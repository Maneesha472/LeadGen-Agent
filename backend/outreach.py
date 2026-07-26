import os
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.orm import Session
from datetime import datetime

from .database import Contact, Company, OutreachLog, User, Execution, Campaign, SessionLocal

def personalize_message(template: str, contact: Contact, company: Company) -> str:
    if not template:
        return ""
    
    # Placeholders map
    replacements = {
        "{contact_name}": contact.name or "Valued Partner",
        "{contact_title}": contact.designation or "Lead",
        "{company_name}": company.name or "your company",
        "{company_website}": company.website or "",
        "{location}": company.address or "your area",
        "{industry}": company.industry or "your industry"
    }
    
    personalized = template
    for key, val in replacements.items():
        personalized = personalized.replace(key, str(val))
        
    return personalized

def send_outreach_email(db: Session, contact_id: int, template_subject: str, template_body: str) -> dict:
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        return {"status": "Failed", "error": "Contact not found"}
        
    company = db.query(Company).filter(Company.id == contact.company_id).first()
    if not company:
        return {"status": "Failed", "error": "Company not found"}

    execution = db.query(Execution).filter(Execution.id == company.execution_id).first()
    user = db.query(User).filter(User.id == execution.user_id).first() if execution else None
    
    if not user:
        return {"status": "Failed", "error": "User profile not found"}

    # Personalize email
    subject = personalize_message(template_subject, contact, company)
    body = personalize_message(template_body, contact, company)

    # Check if SMTP details are configured
    smtp_host = user.smtp_host.strip() if user.smtp_host else ""
    smtp_port = user.smtp_port or 587
    smtp_user = user.smtp_username.strip() if user.smtp_username else ""
    smtp_pass = user.smtp_password.strip() if user.smtp_password else ""
    use_tls = user.smtp_use_tls
    
    if not smtp_user or not smtp_pass:
        return {"status": "Failed", "error": "SMTP email credentials are not configured. Please set them up in your Settings page first."}

    # Attempt real SMTP sending
    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = contact.email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        if use_tls:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
            
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, contact.email, msg.as_string())
        server.quit()

        # Log success
        log = OutreachLog(
            contact_id=contact.id,
            email_subject=subject,
            email_body=body,
            status="Success",
            response_text="Email successfully sent via SMTP server.",
            sent_at=datetime.utcnow()
        )
        contact.status = "Sent"
        db.add(log)
        db.commit()
        return {"status": "Success", "simulated": False, "message": "Email sent successfully."}

    except Exception as e:
        # Log failure
        error_msg = str(e)
        log = OutreachLog(
            contact_id=contact.id,
            email_subject=subject,
            email_body=body,
            status="Failed",
            response_text=f"SMTP Error: {error_msg}",
            sent_at=datetime.utcnow()
        )
        contact.status = "Failed"
        db.add(log)
        db.commit()
        return {"status": "Failed", "error": error_msg}

def log_campaign_progress(campaign_id: int, message: str):
    log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "logs"))
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"campaign_{campaign_id}.log")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"[{timestamp}] {message}\n"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(formatted_msg)
    print(formatted_msg.strip())

def run_campaign_outreach(campaign_id: int):
    db = SessionLocal()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            print(f"[ERROR] Campaign {campaign_id} not found in database.")
            return
            
        log_campaign_progress(campaign_id, f"Initializing outreach campaign #{campaign_id}...")
        log_campaign_progress(campaign_id, f"Subject template: '{campaign.subject}'")
        
        # Determine lead target cohort
        if campaign.execution_id:
            contacts = db.query(Contact).join(Company).filter(
                Company.execution_id == campaign.execution_id
            ).all()
            log_campaign_progress(campaign_id, f"Targeting leads generated by Run #{campaign.execution_id} ({len(contacts)} leads).")
        else:
            # Target all new/uncontacted leads
            contacts = db.query(Contact).join(Company).join(Execution).filter(
                Execution.user_id == campaign.user_id,
                Contact.status == "New"
            ).all()
            log_campaign_progress(campaign_id, f"Targeting all uncontacted leads for this user account ({len(contacts)} leads).")
            
        if not contacts:
            log_campaign_progress(campaign_id, "[WARNING] No contacts found matching criteria. Ending campaign.")
            campaign.status = "Completed"
            campaign.completed_at = datetime.utcnow()
            db.commit()
            return
            
        # Load user configuration delay
        user = db.query(User).filter(User.id == campaign.user_id).first()
        time_delay = user.scraping_delay if user else 2.0
        
        sent_count = 0
        failed_count = 0
        
        for contact in contacts:
            log_campaign_progress(campaign_id, f"Sending email to {contact.name} <{contact.email}>...")
            
            # Spacing delay
            time.sleep(max(0.5, time_delay / 2.0))
            
            result = send_outreach_email(db, contact.id, campaign.subject, campaign.body)
            
            if result.get("status") == "Success":
                sent_count += 1
                sim_txt = " (Simulated Mode)" if result.get("simulated") else ""
                log_campaign_progress(campaign_id, f"[SUCCESS] Sent successfully{sim_txt} to {contact.email}")
            else:
                failed_count += 1
                log_campaign_progress(campaign_id, f"[ERROR] Failed to send to {contact.email}: {result.get('error')}")
                
            # Update campaign metrics
            campaign.sent_count = sent_count
            campaign.failed_count = failed_count
            db.commit()
            
        campaign.status = "Completed"
        campaign.completed_at = datetime.utcnow()
        db.commit()
        log_campaign_progress(campaign_id, f"Campaign complete. Dispatched: {sent_count} successful | {failed_count} failures.")
        
    except Exception as e:
        log_campaign_progress(campaign_id, f"CRITICAL ERROR in Campaign outreach execution: {e}")
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign:
            campaign.status = "Failed"
            campaign.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()

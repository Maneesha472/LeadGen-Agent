import os
import threading
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy.orm import Session
import asyncio
from datetime import datetime

from .database import init_db, get_db, Execution, Company, Contact, OutreachLog, SessionLocal, User, Campaign
from .scraper import LeadGenerator, LOGS_DIR, log_progress
from .outreach import send_outreach_email, run_campaign_outreach
from .auth import get_current_user, get_password_hash, verify_password, create_access_token

# Initialize DB on import
init_db()

app = FastAPI(title="Lead Generation Execution Agent API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Models
class UserRegister(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: str
    password: str

class RunAgentRequest(BaseModel):
    category: str = Field(..., min_length=1)
    location: str = Field(..., min_length=1)
    keywords: Optional[str] = ""
    email_subject: Optional[str] = ""
    email_body: Optional[str] = ""

class SettingsUpdate(BaseModel):
    smtp_host: Optional[str] = "smtp.gmail.com"
    smtp_port: Optional[int] = 587
    smtp_username: Optional[str] = ""
    smtp_password: Optional[str] = ""
    smtp_use_tls: Optional[bool] = True
    simulation_mode: Optional[bool] = False
    scraping_delay: Optional[float] = 2.0
    max_search_results: Optional[int] = 10
    groq_api_key: Optional[str] = ""

class SingleEmailRequest(BaseModel):
    contact_id: int
    subject: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)

class StartCampaignRequest(BaseModel):
    execution_id: Optional[int] = None
    subject: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)

class CompanyCSVEntry(BaseModel):
    name: str
    website: Optional[str] = ""
    category: Optional[str] = "General"
    location: Optional[str] = "United States"
    keywords: Optional[str] = ""

class BulkCSVRequest(BaseModel):
    companies: List[CompanyCSVEntry]
    email_subject: Optional[str] = ""
    email_body: Optional[str] = ""

# Thread-safe background runner wrapper
def execute_agent_task(execution_id: int, request_data: RunAgentRequest):
    db = SessionLocal()
    try:
        # 1. Lead Generation Phase
        generator = LeadGenerator(db, execution_id)
        generator.run()
        
        # Refresh execution reference
        db.refresh(generator.execution)
        exec_obj = generator.execution
        
        # 2. Email Outreach Phase (if template provided)
        if exec_obj.status == "Completed" and request_data.email_subject and request_data.email_body:
            log_progress(execution_id, "[OUTREACH] Starting email outreach campaign...")
            
            # Fetch all contacts generated in this execution
            contacts = db.query(Contact).join(Company).filter(Company.execution_id == execution_id).all()
            
            # Load user settings for delay
            user = db.query(User).filter(User.id == exec_obj.user_id).first()
            time_delay = user.scraping_delay if user else 2.0
            
            sent_count = 0
            for contact in contacts:
                log_progress(execution_id, f"[OUTREACH] Dispatching email to: {contact.name} <{contact.email}>")
                
                # Introduce delay between emails
                asyncio.run(asyncio.sleep(time_delay / 2.0))
                
                result = send_outreach_email(db, contact.id, request_data.email_subject, request_data.email_body)
                
                if result.get("status") == "Success":
                    sent_count += 1
                    sim_txt = " (Simulated)" if result.get("simulated") else ""
                    log_progress(execution_id, f"[OUTREACH SUCCESS] Dispatch successful{sim_txt} to {contact.email}")
                else:
                    log_progress(execution_id, f"[OUTREACH FAILED] Failed to email {contact.email}: {result.get('error')}")
            
            exec_obj.sent_count = sent_count
            db.commit()
            log_progress(execution_id, f"[OUTREACH COMPLETE] Dispatched emails to {sent_count} of {len(contacts)} contacts.")
        else:
            if not request_data.email_subject or not request_data.email_body:
                log_progress(execution_id, "[OUTREACH] Auto email dispatch skipped (no outreach subject/body template provided). Lead is saved in Leads Manager.")

    except Exception as e:
        log_progress(execution_id, f"[ERROR] Thread executor failed: {e}")
        exec_obj = db.query(Execution).filter(Execution.id == execution_id).first()
        if exec_obj:
            exec_obj.status = "Failed"
            exec_obj.completed_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()

# Authentication Endpoints
@app.post("/api/auth/register")
def register_user(user_data: UserRegister, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email.strip().lower()).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="A user with this email address already exists.")
        
    hashed_pwd = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email.strip().lower(),
        hashed_password=hashed_pwd
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "Registration successful. You can now log in."}

@app.post("/api/auth/login")
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username.strip().lower()).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/auth/login-json")
def login_user_json(user_data: UserLogin, db: Session = Depends(get_db)):
    email = user_data.email.strip().lower()
    print(f"[DEBUG LOGIN] Attempting login for email: '{email}'")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        print(f"[DEBUG LOGIN] User with email '{email}' not found in database!")
    else:
        is_verified = verify_password(user_data.password, user.hashed_password)
        print(f"[DEBUG LOGIN] User found. Password matches: {is_verified}")

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/auth/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {"email": current_user.email, "id": current_user.id}

# API Endpoints
@app.post("/api/leads/start")
def start_leads_agent(req: RunAgentRequest, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not req.category.strip() or not req.location.strip():
        raise HTTPException(status_code=400, detail="Business Category and Location are required fields.")

    # Create new execution history record
    execution = Execution(
        user_id=current_user.id,
        category=req.category.strip(),
        location=req.location.strip(),
        keywords=req.keywords.strip() if req.keywords else None,
        status="Running"
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)
    
    # Initialize blank log file
    log_file_path = os.path.join(LOGS_DIR, f"run_{execution.id}.log")
    with open(log_file_path, "w", encoding="utf-8") as f:
        f.write(f"[SYSTEM] Agent execution scheduled at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Run pipeline as background task
    t = threading.Thread(target=execute_agent_task, args=(execution.id, req))
    t.start()
    
    return {"execution_id": execution.id, "message": "Lead generation agent started in the background."}

@app.post("/api/leads/bulk-csv")
def bulk_csv_scrape(req: BulkCSVRequest, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Accepts a list of companies parsed from a CSV file on the frontend.
    Creates one Execution per batch and runs each company through the same
    LeadGenerator pipeline as /api/leads/start.
    """
    if not req.companies:
        raise HTTPException(status_code=400, detail="CSV companies list is empty.")

    execution_ids = []

    for company in req.companies:
        if not company.name.strip():
            continue

        # Use the website directly as 'location' if provided; otherwise use company name
        location_val = company.website.strip() if company.website and company.website.strip() else company.name.strip()

        execution = Execution(
            user_id=current_user.id,
            category=company.category.strip() or "General",
            location=location_val,
            keywords=company.keywords.strip() if company.keywords else None,
            status="Running"
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        log_file_path = os.path.join(LOGS_DIR, f"run_{execution.id}.log")
        with open(log_file_path, "w", encoding="utf-8") as f:
            f.write(f"[SYSTEM] CSV Bulk Execution for '{company.name}' scheduled at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        req_data = RunAgentRequest(
            category=company.category.strip() or "General",
            location=location_val,
            keywords=company.keywords or "",
            email_subject=req.email_subject or "",
            email_body=req.email_body or ""
        )

        t = threading.Thread(target=execute_agent_task, args=(execution.id, req_data))
        t.start()
        execution_ids.append(execution.id)

    if not execution_ids:
        raise HTTPException(status_code=400, detail="No valid company names found in CSV.")

    return {
        "message": f"Bulk CSV scrape started for {len(execution_ids)} companies.",
        "execution_ids": execution_ids,
        "total": len(execution_ids)
    }

@app.get("/api/leads/download-csv")
def download_leads_csv(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Export all leads for the current user as a downloadable CSV file."""
    import csv
    import io
    contacts = db.query(Contact).join(Company).join(Execution).filter(Execution.user_id == current_user.id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Designation", "Email", "Phone", "LinkedIn", "Company", "Website", "Industry", "Address", "Status", "Discovered"])

    for c in contacts:
        comp = db.query(Company).filter(Company.id == c.company_id).first()
        writer.writerow([
            c.name or "",
            c.designation or "",
            c.email or "",
            c.phone or "",
            c.linkedin_url or "",
            comp.name if comp else "",
            comp.website if comp else "",
            comp.industry if comp else "",
            comp.address if comp else "",
            c.status or "",
            c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else ""
        ])

    output.seek(0)
    from fastapi.responses import Response
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_export.csv"}
    )

@app.get("/api/leads/status/{execution_id}")
def get_execution_status(execution_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    execution = db.query(Execution).filter(Execution.id == execution_id, Execution.user_id == current_user.id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found.")
    return {
        "id": execution.id,
        "category": execution.category,
        "location": execution.location,
        "status": execution.status,
        "total_found": execution.total_found,
        "valid_leads": execution.valid_leads,
        "sent_count": execution.sent_count,
        "reply_count": execution.reply_count,
        "created_at": execution.created_at,
        "completed_at": execution.completed_at
    }

@app.get("/api/leads")
def get_leads(status: Optional[str] = None, category: Optional[str] = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(Contact).join(Company).join(Execution).filter(Execution.user_id == current_user.id)
    
    if status:
        query = query.filter(Contact.status == status)
    if category:
        query = query.filter(Company.industry.like(f"%{category}%"))
        
    contacts = query.order_by(Contact.created_at.desc()).all()
    
    results = []
    for c in contacts:
        comp = db.query(Company).filter(Company.id == c.company_id).first()
        log_obj = db.query(OutreachLog).filter(OutreachLog.contact_id == c.id).order_by(OutreachLog.sent_at.desc()).first()
        
        import json
        
        score_bd = {}
        try:
            score_bd = json.loads(getattr(c, 'score_breakdown', '{}') or '{}')
        except Exception:
            pass

        contact_source = {}
        try:
            contact_source = json.loads(getattr(c, 'source_attribution', '{}') or '{}')
        except Exception:
            pass

        company_source = {}
        try:
            company_source = json.loads(getattr(comp, 'source_attribution', '{}') or '{}') if comp else {}
        except Exception:
            pass

        social_links = {}
        try:
            social_links = json.loads(getattr(comp, 'social_links', '{}') or '{}') if comp else {}
        except Exception:
            pass

        results.append({
            "id": c.id,
            "name": c.name,
            "designation": c.designation,
            "email": c.email,
            "phone": c.phone,
            "linkedin_url": c.linkedin_url,
            "status": c.status,
            "verification_status": getattr(c, 'verification_status', 'Unverified') or 'Unverified',
            "score_breakdown": score_bd,
            "source_attribution": contact_source,
            "created_at": c.created_at,
            "company": {
                "name": comp.name,
                "website": comp.website,
                "address": comp.address,
                "phone": comp.phone,
                "industry": comp.industry,
                "linkedin_url": getattr(comp, 'linkedin_url', 'Not Available'),
                "social_links": social_links,
                "source_attribution": company_source
            } if comp else None,
            "outreach": {
                "subject": log_obj.email_subject,
                "body": log_obj.email_body,
                "status": log_obj.status,
                "sent_at": log_obj.sent_at,
                "response": log_obj.response_text
            } if log_obj else None
        })
        
    return results

@app.delete("/api/leads/{id}")
def delete_lead(id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contact = db.query(Contact).join(Company).join(Execution).filter(Contact.id == id, Execution.user_id == current_user.id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Lead not found.")
    db.delete(contact)
    db.commit()
    return {"message": "Lead deleted successfully."}

@app.post("/api/leads/{id}/simulate-reply")
def simulate_reply(id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contact = db.query(Contact).join(Company).join(Execution).filter(Contact.id == id, Execution.user_id == current_user.id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Lead not found.")
        
    if contact.status != "Sent":
        raise HTTPException(status_code=400, detail="Replies can only be simulated for contacts who have been sent outreach.")
        
    contact.status = "Replied"
    
    # Find execution matching company
    company = db.query(Company).filter(Company.id == contact.company_id).first()
    if company:
        execution = db.query(Execution).filter(Execution.id == company.execution_id).first()
        if execution:
            execution.reply_count += 1
            
    # Add simulated response to outreach logs
    log_obj = db.query(OutreachLog).filter(OutreachLog.contact_id == contact.id).order_by(OutreachLog.sent_at.desc()).first()
    if log_obj:
        log_obj.response_text = (
            f"Simulated Inbound Reply at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:\n"
            f"\"Thanks for reaching out, {contact.name}. I received your email and I am interested. "
            f"Let's schedule a brief call next week to discuss this further.\""
        )
        
    db.commit()
    return {"message": "Simulated reply recorded and metrics updated."}

@app.get("/api/executions")
def get_executions(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Execution).filter(Execution.user_id == current_user.id).order_by(Execution.created_at.desc()).all()

@app.get("/api/reports")
def get_reports(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    executions = db.query(Execution).filter(Execution.user_id == current_user.id).all()
    execution_ids = [e.id for e in executions]
    
    if not execution_ids:
        return {
            "summary": {"total_found": 0, "valid_leads": 0, "emails_sent": 0, "replies": 0, "failures": 0},
            "funnel": {"discovered": 0, "validated": 0, "contacted": 0, "replied": 0},
            "categories": {},
            "trends": []
        }
        
    leads = db.query(Contact).join(Company).filter(Company.execution_id.in_(execution_ids)).all()
    
    total_found = sum(e.total_found for e in executions)
    valid_leads = len(leads)
    emails_sent = sum(e.sent_count for e in executions)
    replies = sum(e.reply_count for e in executions)
    failures = len([c for c in leads if c.status == "Failed"])
    
    # Calculate conversion funnel
    funnel = {
        "discovered": total_found,
        "validated": valid_leads,
        "contacted": emails_sent,
        "replied": replies
    }
    
    # Group by category
    categories = {}
    for e in executions:
        cat = e.category.capitalize()
        categories[cat] = categories.get(cat, 0) + e.valid_leads
        
    # Group by date for trends
    trends = {}
    for c in leads:
        day = c.created_at.strftime("%Y-%m-%d")
        trends[day] = trends.get(day, 0) + 1
        
    sorted_trends = [{"date": k, "count": v} for k, v in sorted(trends.items())]
    
    return {
        "summary": {
            "total_found": total_found,
            "valid_leads": valid_leads,
            "emails_sent": emails_sent,
            "replies": replies,
            "failures": failures
        },
        "funnel": funnel,
        "categories": categories,
        "trends": sorted_trends[:15] # Top 15 days
    }

@app.get("/api/settings")
def get_settings_endpoint(current_user: User = Depends(get_current_user)):
    return {
        "smtp_host": current_user.smtp_host,
        "smtp_port": current_user.smtp_port,
        "smtp_username": current_user.smtp_username,
        "smtp_password": current_user.smtp_password,
        "smtp_use_tls": current_user.smtp_use_tls,
        "simulation_mode": False,
        "scraping_delay": current_user.scraping_delay,
        "max_search_results": current_user.max_search_results,
        "groq_api_key": getattr(current_user, 'groq_api_key', '') or "",
    }

@app.post("/api/settings")
def save_settings_endpoint(settings: SettingsUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        val_smtp_host = getattr(settings, 'smtp_host', None)
        if val_smtp_host is not None: current_user.smtp_host = str(val_smtp_host).strip()

        val_smtp_port = getattr(settings, 'smtp_port', None)
        if val_smtp_port is not None:
            try: current_user.smtp_port = int(val_smtp_port)
            except Exception: pass

        val_smtp_user = getattr(settings, 'smtp_username', None)
        if val_smtp_user is not None: current_user.smtp_username = str(val_smtp_user).strip()

        val_smtp_pass = getattr(settings, 'smtp_password', None)
        if val_smtp_pass is not None: current_user.smtp_password = str(val_smtp_pass).strip()

        val_smtp_tls = getattr(settings, 'smtp_use_tls', None)
        if val_smtp_tls is not None: current_user.smtp_use_tls = bool(val_smtp_tls)

        val_delay = getattr(settings, 'scraping_delay', None)
        if val_delay is not None:
            try: current_user.scraping_delay = float(val_delay)
            except Exception: pass

        val_max = getattr(settings, 'max_search_results', None)
        if val_max is not None:
            try: current_user.max_search_results = int(val_max)
            except Exception: pass

        for key in ["groq_api_key"]:
            v = getattr(settings, key, None)
            if v is not None and hasattr(current_user, key):
                setattr(current_user, key, str(v).strip())

        db.commit()
        return {"message": "Configuration saved successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {str(e)}")

@app.get("/api/stream-logs/{execution_id}")
async def stream_logs(execution_id: int, token: Optional[str] = None, db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Authentication token required.")
        
    try:
        from .auth import SECRET_KEY, ALGORITHM
        from jose import jwt
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token.")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token.")
        
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
        
    execution = db.query(Execution).filter(Execution.id == execution_id, Execution.user_id == user.id).first()
    if not execution:
        raise HTTPException(status_code=403, detail="Access denied to execution logs.")

    log_file_path = os.path.join(LOGS_DIR, f"run_{execution_id}.log")
    
    async def log_generator():
        # Wait until file exists
        for _ in range(30):
            if os.path.exists(log_file_path):
                break
            await asyncio.sleep(0.2)
            
        if not os.path.exists(log_file_path):
            yield "data: [ERROR] Connecting to agent logs... Log channel offline.\n\n"
            return
            
        # Stream content
        with open(log_file_path, "r", encoding="utf-8") as f:
            content = f.read()
            if content:
                for line in content.splitlines():
                    yield f"data: {line}\n\n"
            
            # Tail file for live streams
            while True:
                line = f.readline()
                if line:
                    yield f"data: {line.strip()}\n\n"
                else:
                    db_local = SessionLocal()
                    exec_obj = db_local.query(Execution).filter(Execution.id == execution_id).first()
                    db_local.close()
                    
                    if exec_obj and exec_obj.status != "Running":
                        # Read any final trailing lines
                        line = f.readline()
                        while line:
                            yield f"data: {line.strip()}\n\n"
                            line = f.readline()
                        break
                        
                    await asyncio.sleep(0.3)
                    
    return StreamingResponse(log_generator(), media_type="text/event-stream")

@app.post("/api/leads/send-email")
def send_single_email(req: SingleEmailRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    contact = db.query(Contact).join(Company).join(Execution).filter(
        Contact.id == req.contact_id, 
        Execution.user_id == current_user.id
    ).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Lead not found.")
        
    result = send_outreach_email(db, contact.id, req.subject, req.body)
    if result.get("status") == "Success":
        return {"message": result.get("message"), "simulated": result.get("simulated", False)}
    else:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to send email."))

@app.post("/api/campaigns/start")
def start_outreach_campaign(req: StartCampaignRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Verify execution run belongs to this user if target execution specified
    if req.execution_id:
        exec_run = db.query(Execution).filter(Execution.id == req.execution_id, Execution.user_id == current_user.id).first()
        if not exec_run:
            raise HTTPException(status_code=404, detail="Execution run not found.")

    # Create campaign record
    campaign = Campaign(
        user_id=current_user.id,
        execution_id=req.execution_id,
        subject=req.subject.strip(),
        body=req.body.strip(),
        status="Running"
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    
    # Initialize campaign log file
    log_file_path = os.path.join(LOGS_DIR, f"campaign_{campaign.id}.log")
    with open(log_file_path, "w", encoding="utf-8") as f:
        f.write(f"[SYSTEM] Outreach Campaign execution initiated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Spawn thread to run outreach in background
    t = threading.Thread(target=run_campaign_outreach, args=(campaign.id,))
    t.start()

    return {"campaign_id": campaign.id, "message": "Outreach campaign dispatched successfully."}

@app.get("/api/campaigns")
def get_campaigns_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    campaigns = db.query(Campaign).filter(Campaign.user_id == current_user.id).order_by(Campaign.created_at.desc()).all()
    results = []
    for c in campaigns:
        target_name = "All Uncontacted Leads"
        if c.execution_id:
            exec_run = db.query(Execution).filter(Execution.id == c.execution_id).first()
            if exec_run:
                target_name = f"Run #{exec_run.id}: {exec_run.category} in {exec_run.location}"
        
        results.append({
            "id": c.id,
            "subject": c.subject,
            "target": target_name,
            "status": c.status,
            "sent_count": c.sent_count,
            "failed_count": c.failed_count,
            "created_at": c.created_at,
            "completed_at": c.completed_at
        })
    return results

@app.get("/api/stream-logs/campaign/{campaign_id}")
async def stream_campaign_logs(campaign_id: int, token: Optional[str] = None, db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(status_code=401, detail="Authentication token required.")
        
    try:
        from .auth import SECRET_KEY, ALGORITHM
        from jose import jwt
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="Invalid token.")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token.")
        
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found.")
        
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id, Campaign.user_id == user.id).first()
    if not campaign:
        raise HTTPException(status_code=403, detail="Access denied to campaign logs.")

    log_file_path = os.path.join(LOGS_DIR, f"campaign_{campaign_id}.log")
    
    async def campaign_log_generator():
        # Wait until file exists
        for _ in range(30):
            if os.path.exists(log_file_path):
                break
            await asyncio.sleep(0.2)
            
        if not os.path.exists(log_file_path):
            yield "data: [ERROR] Connecting to campaign logs... Log channel offline.\n\n"
            return
            
        # Stream content
        with open(log_file_path, "r", encoding="utf-8") as f:
            content = f.read()
            if content:
                for line in content.splitlines():
                    yield f"data: {line}\n\n"
            
            # Tail file for live streams
            while True:
                line = f.readline()
                if line:
                    yield f"data: {line.strip()}\n\n"
                else:
                    db_local = SessionLocal()
                    camp_obj = db_local.query(Campaign).filter(Campaign.id == campaign_id).first()
                    db_local.close()
                    
                    if camp_obj and camp_obj.status != "Running":
                        # Read any final trailing lines
                        line = f.readline()
                        while line:
                            yield f"data: {line.strip()}\n\n"
                            line = f.readline()
                        break
                        
                    await asyncio.sleep(0.3)
                    
    return StreamingResponse(campaign_log_generator(), media_type="text/event-stream")

# Serve Frontend static assets
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))

@app.get("/.well-known/appspecific/com.chrome.devtools.json")
def chrome_devtools_endpoint():
    return {}

@app.get("/")
def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if not os.path.exists(index_path):
        return {"error": f"Frontend directory not found at {FRONTEND_DIR}. Make sure you run frontend files structure."}
    return FileResponse(index_path)

class NoCacheStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

try:
    if os.path.exists(FRONTEND_DIR):
        app.mount("/", NoCacheStaticFiles(directory=FRONTEND_DIR), name="frontend")
except Exception as e:
    print(f"Error mounting frontend: {e}")

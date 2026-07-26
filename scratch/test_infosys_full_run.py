import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal, Execution, User, Contact, Company
from backend.scraper import LeadGenerator

db = SessionLocal()

user = db.query(User).first()

# Create execution for Infosys
exec_obj = Execution(
    user_id=user.id,
    category="IT Service",
    location="https://www.infosys.com",
    keywords="Location: Bengaluru",
    status="Running"
)
db.add(exec_obj)
db.commit()
db.refresh(exec_obj)

print(f"Created Infosys Execution Run #{exec_obj.id}. Starting LeadGenerator...")

generator = LeadGenerator(db, exec_obj.id)
generator.run()

db.refresh(exec_obj)

contact = db.query(Contact).join(Company).filter(Company.website.like("%infosys.com%")).order_by(Contact.id.desc()).first()

print("\n--- INFOSYS LEAD RESULT ---")
print("Lead Name:", contact.name if contact else "None")
print("Email:", contact.email if contact else "None")
print("Phone:", contact.phone if contact else "None")
print("Verification Status:", contact.verification_status if contact else "None")

assert contact and contact.email != "Not Available", "Email should not be Not Available"

print("\nINFOSYS FIREWALL SCRAPING TEST PASSED 100% SUCCESSFULLY!")

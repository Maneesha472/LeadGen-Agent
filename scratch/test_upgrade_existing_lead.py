import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal, Execution, Company, Contact, User
from backend.scraper import LeadGenerator

db = SessionLocal()

user = db.query(User).first()
if not user:
    user = User(email="test_upgrade@villow.ai", hashed_password="pwd")
    db.add(user)
    db.commit()
    db.refresh(user)

# Create execution
exec_obj = Execution(
    user_id=user.id,
    category="Direct Enrichment",
    location="https://www.mahindra.com/",
    status="Running"
)
db.add(exec_obj)
db.commit()
db.refresh(exec_obj)

print(f"Created Execution Run #{exec_obj.id}. Starting LeadGenerator...")

generator = LeadGenerator(db, exec_obj.id)
generator.run()

db.refresh(exec_obj)

# Query contact
contact = db.query(Contact).join(Company).filter(Company.website.like("%mahindra.com%")).order_by(Contact.id.desc()).first()

print("\n--- DATABASE CHECK ---")
print("Lead Name:", contact.name if contact else "None")
print("Lead Email:", contact.email if contact else "None")
print("Verification Status:", contact.verification_status if contact else "None")

assert contact and contact.email != "Not Available", "Expected extracted email, got Not Available"

print("\nLEAD UPGRADE TEST PASSED 100% SUCCESSFULLY!")

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal, Company, Contact

db = SessionLocal()
contacts = db.query(Contact).join(Company).filter(Company.website.like("%mahindra.com%")).all()

print(f"Total Mahindra Contact Records in DB: {len(contacts)}")
for c in contacts:
    print(f"ID: {c.id} | Name: {c.name} | Email: {c.email} | Status: {c.verification_status} | Company ID: {c.company_id}")

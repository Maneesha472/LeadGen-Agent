import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal, User, Execution, Contact, Company
from backend.scraper import LeadGenerator

db = SessionLocal()
u = db.query(User).first()
if not u:
    print("No user found.")
    sys.exit(1)

exec_obj = Execution(user_id=u.id, category="Direct Enrichment", location="https://worklane-staging.villow.ai/", status="Running")
db.add(exec_obj)
db.commit()
db.refresh(exec_obj)

print(f"Launching test LeadGenerator run #{exec_obj.id} for https://worklane-staging.villow.ai/ ...")
generator = LeadGenerator(db=db, execution_id=exec_obj.id)
generator.run()

# Check created contacts
contacts = db.query(Contact).join(Company).filter(Company.execution_id == exec_obj.id).all()
print(f"\n--- SCRAPING RESULT ---")
print(f"Total Contacts Extracted: {len(contacts)}")
for c in contacts:
    print(f"Name: {c.name}")
    print(f"Email: {c.email}")
    print(f"Company: {c.company.name}")
    print(f"Company LinkedIn: {c.company.linkedin_url}")
    print(f"Person LinkedIn: {c.linkedin_url}")

db.close()

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal, User, Execution, Contact, Company
from backend.scraper import LeadGenerator

db = SessionLocal()
u = db.query(User).filter(User.email == "maneeshashaik0408@gmail.com").first()

exec_obj = Execution(user_id=u.id, category="Direct Enrichment", location="https://openai.com/", status="Running")
db.add(exec_obj)
db.commit()
db.refresh(exec_obj)

print(f"Running scraper for https://openai.com/ under user {u.email}...")
generator = LeadGenerator(db=db, execution_id=exec_obj.id)
generator.run()

# Query lead in DB
c = db.query(Contact).join(Company).filter(Company.execution_id == exec_obj.id).first()
if c:
    print(f"\n--- SUCCESS: OPENAI LEAD SAVED ---")
    print(f"Contact Name: {c.name}")
    print(f"Role: {c.designation}")
    print(f"Company: {c.company.name}")
    print(f"Email: {c.email}")
    print(f"Company LinkedIn: {c.company.linkedin_url}")
    print(f"Executive LinkedIn: {c.linkedin_url}")
else:
    print("\n--- FAILURE: Lead was not saved ---")

db.close()

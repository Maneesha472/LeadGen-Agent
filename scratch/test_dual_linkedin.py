import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal, Company, Contact, User, Execution

db = SessionLocal()
u = db.query(User).first()
if not u:
    print("No user found in DB.")
    sys.exit(1)

exec_obj = db.query(Execution).filter(Execution.user_id == u.id).first()
if not exec_obj:
    exec_obj = Execution(user_id=u.id, category="Tech", location="Online", status="Completed")
    db.add(exec_obj)
    db.commit()
    db.refresh(exec_obj)

# Create test Company with company_linkedin_url
comp = Company(
    execution_id=exec_obj.id,
    name="OpenAI Tech",
    website="https://openai.com",
    address="San Francisco, CA",
    phone="(415) 555-0199",
    industry="AI",
    linkedin_url="https://www.linkedin.com/company/openai"
)
db.add(comp)
db.commit()
db.refresh(comp)

# Create test Contact with personal LinkedIn
c = Contact(
    company_id=comp.id,
    name="Sam Altman",
    designation="CEO",
    email="sam@openai.com",
    phone="(415) 555-0199",
    linkedin_url="https://www.linkedin.com/in/samaltman",
    status="New"
)
db.add(c)
db.commit()
db.refresh(c)

print("Test record saved successfully!")
print("Company LinkedIn:", comp.linkedin_url)
print("Executive Personal LinkedIn:", c.linkedin_url)

db.close()

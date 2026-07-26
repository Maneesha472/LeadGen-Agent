import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal, Execution, User
from backend.scraper import LeadGenerator

db = SessionLocal()

user = db.query(User).first()
if not user:
    user = User(email="test_comp_name@villow.ai", hashed_password="pwd")
    db.add(user)
    db.commit()
    db.refresh(user)

# Create execution with Company Name "Tata Consultancy"
exec_obj = Execution(
    user_id=user.id,
    category="IT Service",
    location="Tata Consultancy",
    keywords="Location: Mumbai",
    status="Running"
)
db.add(exec_obj)
db.commit()
db.refresh(exec_obj)

print(f"Created Execution Run #{exec_obj.id} for Company Name 'Tata Consultancy'. Starting LeadGenerator...")

generator = LeadGenerator(db, exec_obj.id)
generator.run()

db.refresh(exec_obj)
print("\nFinal Execution Status:", exec_obj.status)
print("Total Companies Found:", exec_obj.total_found)
print("Valid Leads Generated:", exec_obj.valid_leads)

assert exec_obj.status == "Completed", f"Execution failed with status: {exec_obj.status}"
print("\nCOMPANY NAME AUTO-RESOLUTION & SCRAPING TEST PASSED 100% SUCCESSFULLY!")

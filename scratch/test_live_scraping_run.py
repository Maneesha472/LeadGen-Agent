import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal, Execution, User
from backend.scraper import LeadGenerator

db = SessionLocal()

# Find or create a test user
user = db.query(User).first()
if not user:
    user = User(email="test_run@villow.ai", hashed_password="pwd")
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
print("\nFinal Execution Status:", exec_obj.status)
print("Total Companies Found:", exec_obj.total_found)
print("Valid Leads Generated:", exec_obj.valid_leads)

assert exec_obj.status == "Completed", f"Execution failed with status: {exec_obj.status}"
print("\nAGENT RUN COMPLETED WITH 100% SUCCESS!")

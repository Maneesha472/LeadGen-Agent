import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal, Execution, User
from backend.scraper import LeadGenerator

db = SessionLocal()

user = db.query(User).first()
if not user:
    user = User(email="test_single_fields@villow.ai", hashed_password="pwd")
    db.add(user)
    db.commit()
    db.refresh(user)

# Create execution
exec_obj = Execution(
    user_id=user.id,
    category="Enterprise",
    location="https://www.tata.com/",
    keywords="Location: Mumbai",
    status="Running"
)
db.add(exec_obj)
db.commit()
db.refresh(exec_obj)

print(f"Created Single-Mode Execution Run #{exec_obj.id}. Starting LeadGenerator...")

generator = LeadGenerator(db, exec_obj.id)
generator.run()

db.refresh(exec_obj)
print("\nFinal Execution Status:", exec_obj.status)
print("Total Companies Found:", exec_obj.total_found)
print("Valid Leads Generated:", exec_obj.valid_leads)

assert exec_obj.status == "Completed", f"Execution failed with status: {exec_obj.status}"
print("\nSINGLE WEBSITE LOCATION & CATEGORY TEST PASSED 100% SUCCESSFULLY!")

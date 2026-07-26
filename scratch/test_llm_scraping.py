import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import SessionLocal, User, Execution
from backend.scraper import LeadGenerator

# Create a local test run
db = SessionLocal()
u = db.query(User).first()
if not u:
    print("No user found in DB. Make sure you register/run the app first.")
    sys.exit(1)

# Check if there is an execution
exec_obj = db.query(Execution).filter(Execution.user_id == u.id).first()
if not exec_obj:
    # create dummy execution
    exec_obj = Execution(user_id=u.id, category="Marketing", location="Chicago", status="Running")
    db.add(exec_obj)
    db.commit()
    db.refresh(exec_obj)

generator = LeadGenerator(db, exec_obj.id)

html = """
<html>
<body>
  <h1>Apex Growth Agency</h1>
  <p>We are a premium digital marketing agency located in Chicago, Illinois. Founded by Dr. Jessica Martinez in 2021.</p>
  <p>Email us at: hello@apexgrowth.com or support@apexgrowth.com</p>
  <p>Phone: (312) 555-0199</p>
</body>
</html>
"""

search_text = """
Apex Growth Agency on LinkedIn: https://www.linkedin.com/company/apex-growth-agency
Find Jessica Martinez LinkedIn profile: https://www.linkedin.com/in/jessica-martinez-growth
"""

# Let's test _llm_extract_lead using a mock API call (or we verify it builds prompt correctly)
print("Verifying prompt preparation...")
soup = generator._llm_extract_lead.__globals__["BeautifulSoup"](html, "html.parser")
for script in soup(["script", "style"]):
    script.decompose()
page_text = soup.get_text()
lines = (line.strip() for line in page_text.splitlines())
chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
page_text = "\n".join(chunk for chunk in chunks if chunk)
page_text = page_text[:4000]

print("Extracted page text (first 200 chars):")
print(page_text[:200])

print("Test complete.")
db.close()

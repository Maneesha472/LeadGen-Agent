import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from backend.app import app, get_db
from backend.database import User, SessionLocal

client = TestClient(app)

# Login / Auth
email = "test_user_tc@villow.ai"
db = SessionLocal()
u = db.query(User).filter(User.email == email).first()
if not u:
    u = User(email=email, hashed_password="hashed_pwd_123")
    db.add(u)
    db.commit()
    db.refresh(u)
db.close()

from backend.auth import create_access_token
token = create_access_token({"sub": email})
headers = {"Authorization": f"Bearer {token}"}

payload = {
    "smtp_host": "",
    "smtp_port": 587,
    "smtp_username": "",
    "smtp_password": "",
    "smtp_use_tls": True,
    "simulation_mode": False,
    "scraping_delay": 2.0,
    "max_search_results": 10,
    "gemini_api_key": "",
    "openai_api_key": "",
    "google_api_key": "test_google_123",
    "google_cse_id": "",
    "brave_api_key": "",
    "tavily_api_key": "tvly-12345",
    "apollo_api_key": "apollo_999",
    "proxycurl_api_key": "",
    "pdl_api_key": "",
    "zerobounce_api_key": "",
    "neverbounce_api_key": ""
}

res = client.post("/api/settings", json=payload, headers=headers)
print("NEW UPDATED CODE POST /api/settings Status:", res.status_code)
print("NEW UPDATED CODE Response:", res.json())

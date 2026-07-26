import requests

BASE_URL = "http://localhost:8000"

# 1. Login or Register
email = "testuser@villow.ai"
password = "TestPassword123!"

reg_res = requests.post(f"{BASE_URL}/api/auth/register", json={"email": email, "password": password})
login_res = requests.post(f"{BASE_URL}/api/auth/login", data={"username": email, "password": password})

token = login_res.json().get("access_token")
print("Obtained JWT Token:", token is not None)

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 2. Test GET /api/settings
get_res = requests.get(f"{BASE_URL}/api/settings", headers=headers)
print("GET /api/settings Status Code:", get_res.status_code)
print("GET /api/settings Payload:", get_res.json())

# 3. Test POST /api/settings with partial payload (from Enterprise Integration form)
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

post_res = requests.post(f"{BASE_URL}/api/settings", json=payload, headers=headers)
print("\nPOST /api/settings Status Code:", post_res.status_code)
print("POST /api/settings Response:", post_res.text)

if post_res.status_code == 200:
    print("\nSUCCESS! Settings saved cleanly on live server without 500 error!")
else:
    print("\nERROR: Failed with status", post_res.status_code)

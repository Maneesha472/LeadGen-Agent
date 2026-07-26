import requests

try:
    print("Testing live endpoint GET /api/settings...")
    r_get = requests.get("http://localhost:8000/api/settings")
    print("GET Status:", r_get.status_code)
    print("GET Response:", r_get.text)
except Exception as e:
    print("Error connecting to live server:", e)

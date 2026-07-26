import sys, os, requests, re
from bs4 import BeautifulSoup
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.scraper import LeadGenerator

lg = LeadGenerator.__new__(LeadGenerator)

url = "https://www.infosys.com/contact.html"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Ch-Ua": '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

endpoints = [
    "https://www.infosys.com",
    "https://www.infosys.com/contact.html",
    "https://www.infosys.com/about.html"
]

for ep in endpoints:
    print(f"\nProbing {ep}...")
    try:
        r = requests.get(ep, headers=headers, timeout=10)
        print("Status:", r.status_code, "| HTML Length:", len(r.text))
        if r.status_code == 200:
            print("Extracted Emails:", lg._extract_emails(r.text))
            print("Extracted Socials:", lg._extract_social_links(r.text))
    except Exception as e:
        print("Error:", e)

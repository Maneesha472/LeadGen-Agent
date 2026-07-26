import sys, os
import requests
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.scraper import LeadGenerator

lg = LeadGenerator.__new__(LeadGenerator)

url = "https://www.mahindra.com/contact-us"
print(f"Fetching {url}...")

try:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9"
    }
    r = requests.get(url, headers=headers, timeout=15)
    print("HTTP Status Code:", r.status_code)
    
    extracted_emails = lg._extract_emails(r.text)
    extracted_socials = lg._extract_social_links(r.text)
    
    print("\nExtracted Emails:", extracted_emails)
    print("Extracted Social Channels:", extracted_socials)

    subpages = lg._find_contact_pages(r.text, "https://www.mahindra.com")
    print("\nDiscovered Subpages:", subpages)

    print("\nTEST PASSED SUCCESSFULLY!")
except Exception as e:
    print("Error during live test:", e)

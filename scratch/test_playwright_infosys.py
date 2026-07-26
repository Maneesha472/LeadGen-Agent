import sys, os
from playwright.sync_api import sync_playwright
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.scraper import LeadGenerator

lg = LeadGenerator.__new__(LeadGenerator)

url = "https://www.infosys.com/contact.html"
print(f"Launching Playwright for {url}...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    try:
        page.goto(url, timeout=20000, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        content = page.content()
        print("Page Title:", page.title())
        print("Rendered HTML Length:", len(content))
        
        emails = lg._extract_emails(content)
        phone = lg._extract_phone(content)
        socials = lg._extract_social_links(content)
        
        print("\nPlaywright Extracted Emails:", emails)
        print("Playwright Extracted Phone:", phone)
        print("Playwright Extracted Socials:", socials)
        
    except Exception as e:
        print("Playwright Error:", e)
    finally:
        browser.close()

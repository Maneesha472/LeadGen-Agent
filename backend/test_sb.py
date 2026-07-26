from seleniumbase import SB
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import urllib.parse

BLOCKED_DOMAINS = {
    "yelp.com", "facebook.com", "yellowpages.com", "instagram.com", "linkedin.com",
    "youtube.com", "twitter.com", "x.com", "wikipedia.org", "tripadvisor.com",
    "groupon.com", "indeed.com", "glassdoor.com", "angis.com", "mapquest.com",
    "google.com", "bing.com", "duckduckgo.com", "reddit.com", "quora.com",
    "bloomberg.com", "crunchbase.com", "zoominfo.com", "dnb.com", "justdial.com",
    "sulekha.com", "glassdoor.co.in", "ambitionbox.com", "goodfirms.co", "clutch.co"
}

def discover_with_sb(query: str, max_results: int = 10):
    websites = []
    seen_domains = set()
    try:
        with SB(uc=True, headless=True) as sb:
            sb.open("https://lite.duckduckgo.com/lite/")
            sb.type('input[name="q"]', query + "\n")
            sb.sleep(2)
            html = sb.get_page_source()
            
            soup = BeautifulSoup(html, "html.parser")
            anchors = soup.find_all("a", class_="result-snippet") or soup.find_all("a", class_="result-url")
            
            # Lite might just have td class='result-snippet'
            if not anchors:
                anchors = soup.find_all("a", href=True)
                
            for a in anchors:
                href = a.get("href", "")
                if href.startswith("http") and "duckduckgo" not in href:
                    parsed = urlparse(href)
                    domain = parsed.netloc.lower()
                    if domain.startswith("www."):
                        domain = domain[4:]
                    
                    if not domain or domain in BLOCKED_DOMAINS or domain in seen_domains or "." not in domain:
                        continue
                    
                    seen_domains.add(domain)
                    clean_name = domain.split(".")[0].replace("-", " ").title()
                    websites.append({
                        "url": f"{parsed.scheme}://{parsed.netloc}",
                        "name": clean_name,
                        "domain": domain
                    })
                    if len(websites) >= max_results:
                        break
    except Exception as e:
        print(f"SB failed: {e}")
    return websites

if __name__ == "__main__":
    res = discover_with_sb("Software Development companies in Hyderabad")
    for r in res:
        print(r)

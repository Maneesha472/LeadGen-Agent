import requests
from bs4 import BeautifulSoup
import urllib.parse
from urllib.parse import urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

BLOCKED_DOMAINS = {
    "yelp.com", "facebook.com", "yellowpages.com", "instagram.com", "linkedin.com",
    "youtube.com", "twitter.com", "x.com", "wikipedia.org", "tripadvisor.com",
    "groupon.com", "indeed.com", "glassdoor.com", "angis.com", "mapquest.com",
    "google.com", "bing.com", "duckduckgo.com", "reddit.com", "quora.com",
    "bloomberg.com", "crunchbase.com", "zoominfo.com", "dnb.com", "justdial.com",
    "sulekha.com", "glassdoor.co.in", "ambitionbox.com", "goodfirms.co", "clutch.co"
}

def _discover_websites(query: str, max_results: int) -> list:
    websites = []
    seen_domains = set()
    try:
        print(f"Querying Bing for: {query}")
        r = requests.get(
            f"https://www.bing.com/search?q={urllib.parse.quote(query)}",
            headers=HEADERS,
            timeout=12
        )
        print(f"Status Code: {r.status_code}")
        if r.status_code != 200:
            print("Failed to get 200 status code")
            return websites
        
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Bing results usually have class "b_algo" or just look at all anchors
        anchors = soup.find_all("a", href=True)
        print(f"Found {len(anchors)} total anchors")
        
        for a in anchors:
            actual_url = a.get("href")
            if not actual_url or "bing.com" in actual_url or "microsoft.com" in actual_url or not actual_url.startswith("http"):
                continue

            parsed = urlparse(actual_url)
            domain = parsed.netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
            
            print(f"Found domain: {domain} (from {actual_url})")
            
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
        print(f"DuckDuckGo discovery failed: {e}")
    return websites

if __name__ == "__main__":
    results = _discover_websites("Software Development companies in Hyderabad", 10)
    print("\nRESULTS:")
    for r in results:
        print(r)

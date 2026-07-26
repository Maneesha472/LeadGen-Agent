from duckduckgo_search import DDGS
from urllib.parse import urlparse

BLOCKED_DOMAINS = {
    "yelp.com", "facebook.com", "yellowpages.com", "instagram.com", "linkedin.com",
    "youtube.com", "twitter.com", "x.com", "wikipedia.org", "tripadvisor.com",
    "groupon.com", "indeed.com", "glassdoor.com", "angis.com", "mapquest.com",
    "google.com", "bing.com", "duckduckgo.com", "reddit.com", "quora.com",
    "bloomberg.com", "crunchbase.com", "zoominfo.com", "dnb.com", "justdial.com",
    "sulekha.com", "glassdoor.co.in", "ambitionbox.com", "goodfirms.co", "clutch.co"
}

def _discover_websites_ddgs(query: str, max_results: int) -> list:
    websites = []
    seen_domains = set()
    try:
        results = DDGS().text(query, max_results=max_results * 2) # Fetch extra to account for blocked domains
        for r in results:
            actual_url = r.get("href")
            if not actual_url: continue
            
            parsed = urlparse(actual_url)
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
        print(f"DuckDuckGo discovery failed: {e}")
    return websites

if __name__ == "__main__":
    results = _discover_websites_ddgs("Software Development companies in Hyderabad", 10)
    print("\nRESULTS:")
    for r in results:
        print(r)

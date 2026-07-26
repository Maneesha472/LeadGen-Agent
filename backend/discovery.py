import time
import requests
from bs4 import BeautifulSoup
from typing import List, Dict

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

class DiscoveryService:
    def __init__(self, user_settings: dict):
        self.settings = user_settings or {}
        self.google_api_key = self.settings.get("google_api_key", "").strip()
        self.google_cse_id = self.settings.get("google_cse_id", "").strip()
        self.brave_api_key = self.settings.get("brave_api_key", "").strip()
        self.tavily_api_key = self.settings.get("tavily_api_key", "").strip()

    def discover_web_snippets(self, name: str, domain: str) -> Dict[str, str]:
        """
        Executes multi-source search provider queries and returns combined snippets and links.
        Returns dict: {"snippets": str, "source": str, "discovered_urls": list}
        """
        snippets = []
        discovered_urls = []
        providers_used = []

        # 1. Google Programmable Search API
        if self.google_api_key and self.google_cse_id:
            google_res = self._search_google(f'"{name}" contact email OR linkedin')
            if google_res.get("snippets"):
                snippets.extend(google_res["snippets"])
                discovered_urls.extend(google_res.get("urls", []))
                providers_used.append("Google Search API")

        # 2. Brave Search API
        if self.brave_api_key:
            brave_res = self._search_brave(f'"{name}" contact email OR linkedin')
            if brave_res.get("snippets"):
                snippets.extend(brave_res["snippets"])
                discovered_urls.extend(brave_res.get("urls", []))
                providers_used.append("Brave Search API")

        # 3. Tavily Search API
        if self.tavily_api_key:
            tavily_res = self._search_tavily(f'"{name}" contact email OR linkedin')
            if tavily_res.get("snippets"):
                snippets.extend(tavily_res["snippets"])
                discovered_urls.extend(tavily_res.get("urls", []))
                providers_used.append("Tavily Search API")

        # 4. DuckDuckGo Fallback (if no paid API configured or no results)
        if not snippets:
            ddg_res = self._search_duckduckgo(name, domain)
            snippets.extend(ddg_res.get("snippets", []))
            providers_used.append("DuckDuckGo Search Engine")

        source_label = ", ".join(providers_used) if providers_used else "DuckDuckGo Search Engine"

        return {
            "snippets": "\n".join(snippets[:10]),
            "source": source_label,
            "discovered_urls": list(set(discovered_urls))
        }

    def _search_google(self, query: str) -> dict:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": self.google_api_key,
            "cx": self.google_cse_id,
            "q": query,
            "num": 5
        }
        snippets, urls = [], []
        try:
            r = requests.get(url, params=params, timeout=8)
            if r.status_code == 200:
                items = r.json().get("items", [])
                for item in items:
                    snippets.append(f"{item.get('title')}: {item.get('snippet')}")
                    urls.append(item.get("link"))
        except Exception:
            pass
        return {"snippets": snippets, "urls": urls}

    def _search_brave(self, query: str) -> dict:
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.brave_api_key
        }
        params = {"q": query, "count": 5}
        snippets, urls = [], []
        try:
            r = requests.get(url, headers=headers, params=params, timeout=8)
            if r.status_code == 200:
                results = r.json().get("web", {}).get("results", [])
                for res in results:
                    snippets.append(f"{res.get('title')}: {res.get('description')}")
                    urls.append(res.get("url"))
        except Exception:
            pass
        return {"snippets": snippets, "urls": urls}

    def _search_tavily(self, query: str) -> dict:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_api_key,
            "query": query,
            "max_results": 5
        }
        snippets, urls = [], []
        try:
            r = requests.post(url, json=payload, timeout=8)
            if r.status_code == 200:
                results = r.json().get("results", [])
                for res in results:
                    snippets.append(f"{res.get('title')}: {res.get('content')}")
                    urls.append(res.get("url"))
        except Exception:
            pass
        return {"snippets": snippets, "urls": urls}

    def _search_duckduckgo(self, name: str, domain: str) -> dict:
        queries = [
            f'"{name}" contact email OR linkedin profile',
            f'site:linkedin.com/company/ {name}',
            f'site:linkedin.com/in/ {name} CEO OR Founder OR Owner'
        ]
        snippets = []
        for q in queries:
            search_url = "https://html.duckduckgo.com/html/"
            try:
                r = requests.post(search_url, data={"q": q}, headers=HEADERS, timeout=6)
                if r.status_code == 200:
                    soup = BeautifulSoup(r.text, "html.parser")
                    results = soup.find_all("a", class_="result__snippet")
                    for elem in results[:3]:
                        snippets.append(elem.get_text())
            except Exception:
                pass
            time.sleep(0.3)
        return {"snippets": snippets, "urls": []}

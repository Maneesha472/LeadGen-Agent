import os
import re
import logging
import json
import time
import random
import urllib.parse
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from datetime import datetime
from exa_py import Exa
from .database import Execution, Company, Contact, User
from .scoring import ScoringService
from .extractor import ExtractorService
from email_validator import validate_email, EmailNotValidError

# ─── Logs Directory ────────────────────────────────────────────────────────────
LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "logs"))
os.makedirs(LOGS_DIR, exist_ok=True)

# ─── HTTP Headers (Full Chrome fingerprint to bypass WAF blocks) ───────────────
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

# ─── Hard blocked domains to skip entirely ───────────────────
HARD_BLOCKED_DOMAINS = {
    "yelp.com",
    "facebook.com",
    "yellowpages.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "twitter.com",
    "x.com",
    "wikipedia.org",
    "tripadvisor.com",
    "groupon.com",
    "indeed.com",
    "glassdoor.com",
    "angis.com",
    "mapquest.com",
    "google.com",
    "bing.com",
    "duckduckgo.com",
    "reddit.com",
    "quora.com",
    "bloomberg.com",
}

# ─── Directory domains to scrape for actual company profiles ───────────────────
DIRECTORY_DOMAINS = {
    "crunchbase.com",
    "zoominfo.com",
    "clutch.co",
    "builtinchicago.org",
    "builtin.com",
    "gregslist.com",
    "designrush.com",
    "epicpresence.com",
    "wellfound.com",
    "goodfirms.co",
    "topstartups.io",
    "comparably.com",
    "fortune.com",
    "dnb.com",
}


def normalize_url(url: str) -> str:
    """Normalize URL by removing double slashes in paths and stripping trailing slashes."""
    if not url:
        return ""
    parsed = urlparse(url)
    scheme = parsed.scheme if parsed.scheme else "https"
    netloc = parsed.netloc
    path = parsed.path
    
    # Remove double slashes in the path
    path = re.sub(r'//+', '/', path)
    if path.endswith('/'):
        path = path[:-1]
        
    # Strip index.html or home
    if path.endswith('/index.html') or path.endswith('/home'):
        path = path.rsplit('/', 1)[0]
        
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{scheme}://{netloc}{path}{query}"

def get_base_url(url: str) -> str:
    """Extract only the scheme and netloc (root domain) from a URL."""
    if not url:
        return ""
    parsed = urlparse(url)
    scheme = parsed.scheme if parsed.scheme else "https"
    return f"{scheme}://{parsed.netloc}"

def is_personal_email(email: str, name: str) -> bool:
    if not name or name == "Not Available":
        return False
    parts = name.lower().split()
    return any(p in email.lower() for p in parts if len(p) > 2)


def score_email(email: str) -> int:
    """Basic heuristic to score email quality. Generic emails score low."""
    if not email:
        return 0
    email = email.lower()

    # Penalize generic addresses heavily
    generics = [
        "info",
        "contact",
        "sales",
        "support",
        "hello",
        "admin",
        "office",
        "marketing",
        "enquiries",
        "webmaster",
        "hr",
        "careers",
        "noreply",
        "no-reply",
    ]
    local_part = email.split("@")[0]

    if any(g == local_part for g in generics):
        return 10
    if any(g in local_part for g in generics):
        return 20

    # Reward personal-looking addresses
    if "." in local_part or "_" in local_part:
        return 90

    return 80


# ─── Leader title patterns (from Leader Agent) ────────────────────────────────
LEADER_TITLE_PATTERNS = [
    re.compile(r"\b(CEO|Chief Executive Officer)\b", re.I),
    re.compile(r"\b(CTO|Chief Technology Officer)\b", re.I),
    re.compile(r"\b(CFO|Chief Financial Officer)\b", re.I),
    re.compile(r"\b(COO|Chief Operating Officer)\b", re.I),
    re.compile(r"\b(CMO|Chief Marketing Officer)\b", re.I),
    re.compile(r"\b(CPO|Chief Product Officer)\b", re.I),
    re.compile(r"\bFounder\b", re.I),
    re.compile(r"\bCo-?Founder\b", re.I),
    re.compile(r"\bPresident\b", re.I),
    re.compile(r"\bManaging Director\b", re.I),
    re.compile(r"\bExecutive Director\b", re.I),
    re.compile(r"\bVice President\b", re.I),
    re.compile(r"\b(VP|V\.P\.)\b", re.I),
    re.compile(r"\bDirector\b", re.I),
    re.compile(r"\bHead of\b", re.I),
    re.compile(r"\bGeneral Manager\b", re.I),
    re.compile(r"\bOwner\b", re.I),
    re.compile(r"\bPartner\b", re.I),
    re.compile(r"\bChairman\b", re.I),
]

# ─── CSS selectors for person cards (from Leader Agent) ───────────────────────
PERSON_CARD_SELECTORS = [
    ".team-member",
    ".member",
    ".person",
    ".leader",
    ".executive",
    ".team-card",
    ".profile-card",
    ".bio-card",
    ".people-card",
    '[class*="team"]',
    '[class*="member"]',
    '[class*="leader"]',
    '[class*="person"]',
    '[class*="executive"]',
    '[class*="profile"]',
    "article",
    ".card",
]

NAME_SELECTORS = [
    "h2",
    "h3",
    "h4",
    ".name",
    ".member-name",
    ".person-name",
    ".leader-name",
    '[class*="name"]',
    "strong",
]
TITLE_SELECTORS = [
    ".title",
    ".role",
    ".position",
    ".designation",
    ".job-title",
    '[class*="title"]',
    '[class*="role"]',
    "p",
    "span",
]

# ─── Team/leadership page keywords (from Leader Agent) ────────────────────────
TEAM_PAGE_KEYWORDS = [
    "team",
    "about/team",
    "about-us/team",
    "leadership",
    "management",
    "our-team",
    "our-leadership",
    "founders",
    "executives",
    "board",
    "people",
    "staff",
    "directors",
    "about/leadership",
    "company/team",
    "about",
    "about-us",
    "about_us",
    "contact",
    "contact-us",
    "contact_us",
    "company",
]

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(
    r"(?:(?:\+|00)?(1|44|61|81|91|971|[\d]{1,3})[\s\-\.]?)?"  # robust country code
    r"\(?([0-9]{2,5})\)?"  # area code
    r"[\s\-\.]?([0-9]{3,4})"  # prefix
    r"[\s\-\.]?([0-9]{3,5})"  # suffix
)


# ─── Standard Logging Setup ───────────────────────────────────────────────────
def setup_logger(execution_id: int) -> logging.Logger:
    logger = logging.getLogger(f"Execution_{execution_id}")
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        fh = logging.FileHandler(
            os.path.join(LOGS_DIR, f"run_{execution_id}.log"), encoding="utf-8"
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)
    return logger


def log_progress(execution_id: int, message: str) -> None:
    setup_logger(execution_id).info(message)


# ─── Headless Browser Fetch (Playwright) ──────────────────────────────────────
# REPLACED: Playwright fetching is now handled by Parallel Web Systems API
def get_exa_client():
    api_key = os.environ.get("EXA_API_KEY", "")
    if not api_key:
        print("[WARNING] EXA_API_KEY is not set. Exa search will fail.")
        return None
    try:
        return Exa(api_key=api_key)
    except Exception:
        return None


# ─── Global Request Session ───────────────────────────────────────────────────
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Optional, Dict, Any, List
import requests_cache

GLOBAL_SESSION = requests_cache.CachedSession("scraper_cache", expire_after=86400)
_retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["HEAD", "GET", "OPTIONS", "POST"])
GLOBAL_SESSION.mount("http://", HTTPAdapter(max_retries=_retries, pool_connections=50, pool_maxsize=50))
GLOBAL_SESSION.mount("https://", HTTPAdapter(max_retries=_retries, pool_connections=50, pool_maxsize=50))


def smart_fetch(url: str, execution_id: int = 0) -> str:
    """Try Parallel Web Systems Extract API first, then requests fallback."""
    api_key = os.environ.get("PARALLEL_API_KEY")
    if not api_key:
        log_progress(
            execution_id,
            f"[WARNING] PARALLEL_API_KEY not set. Falling back to requests for {url}",
        )
        try:
            r = GLOBAL_SESSION.get(url, headers=HEADERS, timeout=10)
            return r.text if r.status_code == 200 else ""
        except requests.RequestException:
            return ""

    log_progress(
        execution_id,
        f"[LIVE SCRAPING] Using Parallel Web Systems Extract API for {url}",
    )
    try:
        r = GLOBAL_SESSION.post(
            "https://api.parallel.ai/v1/extract",
            json={"urls": [url]},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=20,
        )
        if r.status_code == 200:
            data = r.json()
            results = data.get("results", [])
            if results:
                excerpts = results[0].get("excerpts", [])
                return (
                    "\n\n".join(excerpts)
                    if excerpts
                    else results[0].get("full_content", "")
                )
    except Exception as e:
        log_progress(execution_id, f"[WARNING] Parallel Extract API failed: {e}")

    return ""

def raw_html_fetch(url: str, execution_id: int = 0) -> str:
    """Fetch raw HTML for directory link extraction, bypassing Parallel text extraction."""
    log_progress(
        execution_id,
        f"[LIVE SCRAPING] Fetching raw HTML for link extraction: {url}",
    )
    try:
        r = GLOBAL_SESSION.get(url, headers=HEADERS, timeout=15)
        return r.text if r.status_code == 200 else ""
    except requests.RequestException as e:
        log_progress(execution_id, f"[WARNING] Raw HTML fetch failed: {e}")
        return ""


# ─── DOM Extraction Helpers (ported from Leader Agent) ────────────────────────
def extract_emails_from_html(html: str) -> list:
    """Extract all email addresses from page HTML."""
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    found = set()

    # 1. Standard regex on raw text
    body_text = soup.get_text()
    for m in EMAIL_REGEX.finditer(body_text):
        e = m.group(0).lower()
        if not any(
            x in e for x in ["example", "@sentry", "@w3.", ".png", ".jpg", ".gif"]
        ):
            found.add(e)

    # 2. mailto: href links
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "mailto:" in href.lower():
            raw = href.lower().split("mailto:")[1].split("?")[0].strip()
            if EMAIL_REGEX.match(raw):
                found.add(raw)

    # 3. HTML data attributes
    for tag in soup.find_all(True):
        for attr_val in tag.attrs.values():
            if isinstance(attr_val, str) and "@" in attr_val:
                for m in EMAIL_REGEX.finditer(attr_val):
                    e = m.group(0).lower()
                    if "." in e.split("@")[1]:
                        found.add(e)

    # 4. Obfuscated patterns like "name [at] domain.com"
    text_lower = body_text.lower()
    obf_pattern = re.compile(
        r"([a-zA-Z0-9._%+\-]+)\s*[\[\(]?at[\]\)]?\s*([a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6})"
    )
    for m in obf_pattern.finditer(text_lower):
        candidate = f"{m.group(1)}@{m.group(2)}"
        if EMAIL_REGEX.match(candidate):
            found.add(candidate)

    final_valid = set()
    for e in found:
        e = e.strip().lower()
        if any(
            x in e
            for x in [
                "example",
                "@sentry",
                "@w3.",
                ".png",
                ".jpg",
                ".gif",
                ".cfg",
                ".svg",
                ".webp",
                "www.",
                ".js",
                "email@",
            ]
        ):
            continue
        try:
            # Validate and get standard form
            v = validate_email(e, check_deliverability=False)
            final_valid.add(v.normalized)
        except EmailNotValidError:
            pass

    return list(final_valid)


def extract_phone_from_html(html: str) -> str:
    """Extract best phone number from HTML (tel: links first, then regex)."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")

    # 1. tel: links — handle tel:// double-slash AND concatenated junk (e.g. tel://1800-108-5000Email:...)
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.lower().startswith("tel:"):
            # Strip leading slashes (tel:// → tel:)
            raw = href[4:].lstrip("/")
            # Truncate at first non-phone character run (letters that look like email/text appended)
            # Keep only up to the end of the numeric phone part
            # Strategy: extract the first valid phone number from the raw value
            num_match = re.match(r"([\+\d][\d\s\.\-\(\)]{5,20})", raw)
            if num_match:
                p = num_match.group(1).strip().rstrip("-. ")
                digits = re.sub(r"\D", "", p)
                if 7 <= len(digits) <= 15:
                    return p

    # 2. Regex patterns - covers standard, Indian toll-free (@1800/1860), and international formats
    text = soup.get_text()
    YEAR_PREFIXES = ("2024", "2025", "2026", "2027", "2028", "2029", "2030")
    for m in PHONE_REGEX.finditer(text):
        val = (
            m.group(0).strip().lstrip("@")
        )  # strip any @ prefix from toll-free display
        digits = re.sub(r"\D", "", val)
        if 7 <= len(digits) <= 15 and not digits.startswith(YEAR_PREFIXES):
            return val
    return ""


def extract_social_links(html: str) -> dict:
    """Extract social media profile links from page HTML."""
    if not html:
        return {}
    soup = BeautifulSoup(html, "html.parser")
    socials = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "facebook.com" in href and "facebook" not in socials:
            socials["facebook"] = href
        elif ("twitter.com" in href or "x.com" in href) and "twitter" not in socials:
            socials["twitter"] = href
        elif "instagram.com" in href and "instagram" not in socials:
            socials["instagram"] = href
        elif "youtube.com" in href and "youtube" not in socials:
            socials["youtube"] = href
        elif "linkedin.com/company" in href and "company_linkedin" not in socials:
            socials["company_linkedin"] = href
        elif "linkedin.com/in/" in href and "person_linkedin" not in socials:
            socials["person_linkedin"] = href
    return socials


def extract_leaders_from_html(html: str, base_url: str) -> list:
    """
    Rule-based leader extraction (ported from Leader Agent scraper_core.js).
    Tries CSS person card selectors, then Schema.org JSON-LD, then text proximity search.
    """
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen = set()

    # Strategy 1: CSS person card selectors
    for card_sel in PERSON_CARD_SELECTORS:
        cards = soup.select(card_sel)
        if not (2 <= len(cards) <= 50):
            continue
        for card in cards:
            name = ""
            title = ""
            for ns in NAME_SELECTORS:
                el = card.select_one(ns)
                if el:
                    t = el.get_text().strip()
                    if t and 2 < len(t) < 60 and re.search(r"[A-Z]", t):
                        name = t
                        break
            for ts in TITLE_SELECTORS:
                el = card.select_one(ts)
                if el:
                    t = el.get_text().strip()
                    if t and any(pat.search(t) for pat in LEADER_TITLE_PATTERNS):
                        title = t
                        break
            linkedin = ""
            for a in card.find_all("a", href=True):
                href = a["href"]
                if "linkedin.com/in/" in href:
                    linkedin = href
                    break
            if name and title and name.lower() not in seen:
                seen.add(name.lower())
                results.append(
                    {"name": name.strip(), "title": title.strip(), "linkedin": linkedin}
                )
        if len(results) >= 2:
            break

    # Strategy 2: Schema.org JSON-LD Person data
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") == "Person" and item.get("name"):
                    n = item["name"]
                    if n.lower() not in seen:
                        seen.add(n.lower())
                        same_as = item.get("sameAs", [])
                        li = next(
                            (
                                u
                                for u in (
                                    same_as if isinstance(same_as, list) else [same_as]
                                )
                                if "linkedin" in str(u)
                            ),
                            "",
                        )
                        results.append(
                            {
                                "name": n.strip(),
                                "title": item.get("jobTitle", "").strip(),
                                "linkedin": li,
                            }
                        )
        except Exception:
            pass

    # Strategy 3: Text proximity - find title keyword near a name-like text
    if not results:
        body_text = soup.get_text(" ", strip=True)
        for el in soup.find_all(["p", "span", "div", "li"]):
            text = el.get_text().strip()
            if not text or len(text) > 200 or len(el.find_all()) > 5:
                continue
            if any(pat.search(text) for pat in LEADER_TITLE_PATTERNS):
                parent = el.parent
                name_el = None
                for ns in ["h2", "h3", "h4", "strong", ".name"]:
                    name_el = (
                        parent.select_one(ns)
                        if isinstance(ns, str) and not ns.startswith(".")
                        else parent.find(class_=ns[1:])
                    )
                    if name_el:
                        break
                if name_el:
                    n = name_el.get_text().strip()
                    if n and len(n) < 60 and n[0].isupper() and n.lower() not in seen:
                        seen.add(n.lower())
                        results.append({"name": n, "title": text, "linkedin": ""})

    def rank_title(t):
        t = t.lower()
        if "founder" in t or "ceo" in t: return 1
        if "cto" in t or "chief" in t: return 2
        if "president" in t or "coo" in t: return 3
        if "vp " in t or "vice president" in t: return 4
        if "director" in t or "head" in t: return 5
        if "manager" in t and "office" not in t: return 6
        return 99

    results.sort(key=lambda x: rank_title(x.get("title", "")))
    return results[:10]


def find_team_page(html: str, base_url: str) -> str:
    """Find team/leadership/about page link from homepage HTML."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    # Only use the root domain for paths to prevent appending to article paths
    root_base_url = get_base_url(base_url)
    
    for a in soup.find_all("a", href=True):
        href = a["href"].lower()
        if any(
            kw in href for kw in ["blog", "news", "article", "case-study", "author"]
        ):
            continue
        if any(kw in href for kw in TEAM_PAGE_KEYWORDS):
            full = a["href"]
            if full.startswith("http"):
                return normalize_url(full)
            return normalize_url(urllib.parse.urljoin(root_base_url, full))
    return ""


def find_contact_subpages(html: str, base_url: str, location_hint: str = "") -> list:
    """Return a prioritized list of subpages to probe for contact info.

    Priority order:
    1. Links actually found in the page HTML (most accurate — catches deep paths like /in/discover-kia/contact-us.html)
    2. Location-specific guessed paths
    3. Common generic guessed paths
    """
    html_discovered = []  # Links pulled from actual page HTML  (highest priority)
    guessed = []  # Blind path guesses (fallback)
    soup = BeautifulSoup(html, "html.parser") if html else None

    # Only use the root domain for paths to prevent appending to article paths
    root_base_url = get_base_url(base_url)

    # Step 1: Extract links from actual page HTML (or Markdown) first
    CONTACT_KEYWORDS = [
        "contact",
        "about",
        "team",
        "leadership",
        "reach",
        "touch",
        "support",
        "help",
        "query",
        "feedback",
    ]

    # Also support Markdown links [text](href) since Parallel returns markdown
    links = []
    if soup:
        for a in soup.find_all("a", href=True):
            links.append(a["href"])
    if html:
        links.extend(re.findall(r"\[.*?\]\((.*?)\)", html))

    for href in links:
        href_lower = href.lower()
        full = href
        # Skip anchors, javascript, mailto, tel
        if not full or full.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        if any(
            kw in href_lower
            for kw in ["blog", "news", "article", "case-study", "author"]
        ):
            continue
        if any(kw in href_lower for kw in CONTACT_KEYWORDS):
            if full.startswith("http"):
                candidate = full
            else:
                candidate = urllib.parse.urljoin(root_base_url, full)
            candidate = normalize_url(candidate)
            if candidate not in html_discovered:
                html_discovered.append(candidate)

    # Step 2: Location-specific guessed paths
    if location_hint:
        loc_slug = location_hint.lower().replace(" ", "-").replace(",", "")
        guessed += [
            normalize_url(f"{root_base_url}/contact-us/{loc_slug}"),
            normalize_url(f"{root_base_url}/locations/{loc_slug}"),
        ]

    # Step 3: Generic guessed paths
    guessed += [
        normalize_url(f"{root_base_url}/contact-us"),
        normalize_url(f"{root_base_url}/contact"),
        normalize_url(f"{root_base_url}/about-us"),
        normalize_url(f"{root_base_url}/about"),
    ]

    # Merge: HTML-discovered links take priority; guessed paths fill remaining slots
    merged = list(html_discovered)  # real links first
    # Only probe generic if no HTML links found to reduce requests
    if len(merged) < 2:
        for g in guessed:
            if g not in merged:
                merged.append(g)

    return merged[:12]  # Increased from 8 → 12 to catch more real contact pages




def normalize_url(url: str) -> str:
    """Strip protocol, www, and trailing slashes for duplicate checking."""
    if not url or url == "Not Available":
        return "Not Available"
    url = url.lower().strip()
    if url.startswith("http://"):
        url = url[7:]
    elif url.startswith("https://"):
        url = url[8:]
    if url.startswith("www."):
        url = url[4:]
    return url.rstrip("/")


def find_linkedin_waterfall(
    person_name: str, company_name: str, execution_id=None
) -> str:
    """Waterfall search for LinkedIn profile: Exa -> Google -> Bing -> Yahoo -> DuckDuckGo -> URL Guess"""

    def log(msg):
        if execution_id:
            log_progress(execution_id, msg)
        else:
            print(msg)

    log(f"[LINKEDIN FINDER] Stage 1: Exa AI for {person_name} at {company_name}")
    exa = get_exa_client()
    if exa:
        try:
            query = f"""
Find the official LinkedIn profile of {person_name}
who works at {company_name}.

Return only profiles that belong to:
- Founder
- Co-Founder
- CEO
- President
- Owner
- Managing Director
- Partner
- CTO
- CIO
- VP

The profile must match the company.
Site: linkedin.com/in/
"""
            res = exa.search(query, type="keyword", num_results=10)
            log(f"[LINKEDIN FINDER] Exa returned {len(res.results)} results")
            for r in res.results:
                log("--------------------------------------------------")
                log(f"URL   : {r.url}")
                log(f"TITLE : {r.title}")
                if "linkedin.com/in/" in r.url:
                    url_title = (r.url + " " + (r.title or "")).lower()
                    name_parts = person_name.lower().split()
                    has_name = all(part in url_title for part in name_parts)
                    company_words = [
                        w for w in company_name.lower().split() if len(w) > 2
                    ]
                    has_comp = any(w in url_title for w in company_words)
                    has_title = any(
                        t in url_title
                        for t in [
                            "ceo",
                            "founder",
                            "owner",
                            "president",
                            "director",
                            "partner",
                            "manager",
                            "managing partner",
                            "principal",
                            "co-founder",
                            "vp",
                            "vice president",
                            "chairman",
                            "cto",
                            "cio",
                            "chief architect",
                            "founder & ceo",
                        ]
                    )
                    log(f"has_name  = {has_name}")
                    log(f"has_comp  = {has_comp}")
                    log(f"has_title = {has_title}")
                    if has_name and (has_comp or has_title):
                        found_url = clean_linkedin_url(r.url)
                        log(f"[LINKEDIN FINDER] Found via Exa AI: {found_url}")
                        return found_url
        except Exception as e:
            log(f"[LINKEDIN FINDER] Exa failed: {e}")

    query = urllib.parse.quote(
        f'site:linkedin.com/in/ "{person_name}" "{company_name}"'
    )

    # Stages 2-5: Fallback Search Engines
    search_engines = [
        ("Google", f"https://www.google.com/search?q={query}"),
        ("Bing", f"https://www.bing.com/search?q={query}"),
        ("Yahoo", f"https://search.yahoo.com/search?p={query}"),
        ("DuckDuckGo HTML", f"https://html.duckduckgo.com/html/?q={query}"),
    ]

    with requests.Session() as session:
        for stage_idx, (engine_name, engine_url) in enumerate(search_engines, start=2):
            log(f"[LINKEDIN FINDER] Stage {stage_idx}: {engine_name} Search")
            time.sleep(random.uniform(1.5, 3.0))
            try:
                r = session.get(engine_url, headers=get_random_user_agent(), timeout=10)
                found = extract_linkedin_from_html(r.text, person_name, company_name)
                if found:
                    log(f"[LINKEDIN FINDER] Found via {engine_name}: {found}")
                    return found
            except requests.RequestException as e:
                log(f"[LINKEDIN FINDER] {engine_name} failed: {e}")

    log(f"[LINKEDIN FINDER] Stage 6: URL Guessing")
    name_parts = person_name.lower().split()
    if len(name_parts) >= 2:
        first = name_parts[0]
        last = name_parts[-1]
        guesses = [
            f"https://www.linkedin.com/in/{first}-{last}",
            f"https://www.linkedin.com/in/{first}{last}",
            f"https://www.linkedin.com/in/{first}.{last}",
        ]
        with requests.Session() as session:
            for guess in guesses:
                try:
                    time.sleep(random.uniform(1.0, 2.0))
                    hr = session.head(
                        guess,
                        headers=get_random_user_agent(),
                        timeout=5,
                        allow_redirects=True,
                    )
                    if hr.status_code == 200:
                        log(f"[LINKEDIN FINDER] Guessed valid URL: {guess}")
                        return guess
                except requests.RequestException as e:
                    log(f"[LINKEDIN FINDER] URL Guessing exception: {e}")

    log(f"[LINKEDIN FINDER] All stages failed. Profile Not Available.")
    return "Not Available"


def find_company_linkedin_exa(
    company_name: str, location: str, domain: str, industry: str, groq_key: str = None
) -> str:
    """Find and STRICTLY VERIFY LinkedIn company page URL via Exa search."""
    exa = get_exa_client()
    if not exa:
        return "Not Available"

    try:
        search_query = f"site:linkedin.com/company/ {company_name}"
        if location:
            search_query += f" {location}"

        res = exa.search_and_contents(
            search_query, type="keyword", num_results=3, text={"max_characters": 800}
        )

        candidates = []
        for r in res.results:
            if "linkedin.com/company/" in r.url:
                candidates.append(
                    {"url": r.url, "title": r.title or "", "text": r.text or ""}
                )

        if not candidates:
            return "Not Available"

        # If LLM key is available, use it for strict verification
        if groq_key:
            from backend.extractor import ExtractorService

            prompt = f"You are verifying a LinkedIn company profile for a B2B lead generation system.\nTarget Company Identity:\n- Name: {company_name}\n- Domain: {domain}\n- Location: {location}\n- Industry: {industry}\n\nCandidates found:\n"
            for i, c in enumerate(candidates):
                prompt += f"\\n[{i}] URL: {c['url']}\\nTitle: {c['title']}\\nText: {c['text'][:300]}\\n"

            prompt += '\nTask: Which candidate strictly matches the Target Company? Pay attention to location (e.g. Chicago vs Bangalore) and domain mismatches.\nReturn ONLY a valid JSON object with:\n{\n  "match_found": boolean,\n  "matched_url": "string or null"\n}\n'
            llm_result = ExtractorService._call_groq(prompt, groq_key)
            if (
                llm_result
                and llm_result.get("match_found")
                and llm_result.get("matched_url")
            ):
                return llm_result.get("matched_url")

        # Keyword Fallback (if Groq fails or rate limits)
        target_loc = location.split(",")[0].lower().strip() if location else ""
        for c in candidates:
            text_lower = (c["title"] + " " + c["text"]).lower()

            # Reject obvious wrong locations (hardcoded common false positives for Chicago)
            if "chicago" in target_loc and (
                "bengaluru" in text_lower
                or "bangalore" in text_lower
                or "india" in text_lower
            ):
                continue

            # If location is in text, accept it
            if target_loc and target_loc in text_lower:
                return c["url"]

            # If domain is in text, accept it
            if domain and domain.split(".")[0] in text_lower:
                return c["url"]

        # If fallback fails to confidently match, return Not Available
        return "Not Available"
    except Exception as e:
        pass

def is_listicle_or_blog(url: str, title: str) -> bool:
    url_lower = url.lower() if url else ""
    title_lower = title.lower() if title else ""
    
    url_patterns = [
        "/blog", "/article", "/news", "top-", "best-", "-companies", "-startups", "list", 
        "/guide", "/resources", "/how-to", "-company-in"
    ]
    if any(p in url_lower for p in url_patterns):
        return True
        
    title_patterns = ["top ", "best ", "list of ", "companies in", "startups in", "ranking", "how to find"]
    if any(p in title_lower for p in title_patterns):
        return True
        
    return False

def extract_companies_from_directory(html: str, base_url: str, execution_id: int = 0) -> dict:
    """Extract official company URLs and company names from a directory page."""
    from .directory_parser import DirectoryExtractor
    extractor = DirectoryExtractor(HARD_BLOCKED_DOMAINS, DIRECTORY_DOMAINS)
    return extractor.extract_companies(html, base_url)

def async_linkedin_worker(contact_id: int, company_id: int, contact_name: str, company_name: str, location: str, domain: str, category: str, groq_key: str):
    """Background worker to lookup LinkedIn profiles asynchronously to not block lead delivery."""
    import threading
    def worker():
        try:
            time.sleep(random.uniform(2.0, 5.0)) # Add some jitter so multiple threads don't instantly hit APIs
            from .database import SessionLocal, Company, Contact
            with SessionLocal() as db:
                company = db.query(Company).filter(Company.id == company_id).first()
                contact = db.query(Contact).filter(Contact.id == contact_id).first()
                
                if company and (not company.linkedin_url or company.linkedin_url == "Not Available"):
                    c_li = find_company_linkedin_exa(company_name, location, domain, category, groq_key)
                    if c_li and c_li != "Not Available":
                        company.linkedin_url = c_li
                        
                if contact and contact.name not in ("Office Manager", "Not Available", "NOT_FOUND"):
                    if not contact.linkedin_url or contact.linkedin_url == "Not Available":
                        found_li = find_linkedin_waterfall(contact.name, company_name, 0)
                        if found_li and found_li != "Not Available":
                            contact.linkedin_url = found_li
                            
                db.commit()
        except Exception:
            pass
            
    t = threading.Thread(target=worker)
    t.daemon = True
    t.start()


class LeadGenerator:
    def __init__(self, db, execution_id: int):
        self.db = db
        self.execution_id = execution_id
        
        from .database import Execution, User
        self.execution = self.db.query(Execution).filter(Execution.id == self.execution_id).first()
        self.user = self.db.query(User).filter(User.id == self.execution.user_id).first()
        
        import json
        self.settings = {}
        try:
            if self.user and hasattr(self.user, 'settings') and self.user.settings:
                self.settings = json.loads(self.user.settings)
        except Exception:
            pass

    def run(self):
        try:
            self._run_live_scraping()
        except Exception as e:
            log_progress(self.execution_id, f"[ERROR] Scraper crashed: {e}")
            self.db.rollback()
            if self.execution:
                self.execution.status = "Failed"
                self.db.commit()

    def _process_website(self, site: dict, location_hint: str, groq_key: str, category: str, location: str):
        domain = site["domain"]
        url = site["url"]
        name = site["name"]
        
        # --- QUALITY GATE (STEP 6) ---
        url_lower = url.lower()
        name_lower = name.lower()
        
        # 1. Reject Directory/Listicle names
        invalid_name_patterns = ["top ", "best ", "list of ", "companies in", "startups in", "ranking", "how to find"]
        if any(p in name_lower for p in invalid_name_patterns):
            log_progress(self.execution_id, f"[QUALITY GATE REJECTED] Rejected listicle name: {name}")
            return None
            
        # 2. Reject Blog/Article URLs
        invalid_url_patterns = ["/blog", "/article", "/news", "top-", "best-", "-companies", "-startups", "list", "/guide", "/resources", "/how-to", "-company-in"]
        if any(p in url_lower for p in invalid_url_patterns):
            log_progress(self.execution_id, f"[QUALITY GATE REJECTED] Rejected blog/listicle URL: {url}")
            return None
            
        # 3. Reject known directories
        if any(b in domain for b in HARD_BLOCKED_DOMAINS) or any(b in domain for b in DIRECTORY_DOMAINS):
            log_progress(self.execution_id, f"[QUALITY GATE REJECTED] Rejected directory domain: {domain}")
            return None
        # -----------------------------
        
        log_progress(self.execution_id, f"[LIVE SCRAPING] Visiting {url} ...")
        
        # ── Fetch homepage ──
        home_html = smart_fetch(url, self.execution_id)
        if not home_html:
            log_progress(self.execution_id, f"[WARNING] Could not load {url}. Skipping.")
            return None
        homepage_emails = extract_emails_from_html(home_html)
        homepage_phone = extract_phone_from_html(home_html)
        socials = extract_social_links(home_html)
        homepage_leaders = extract_leaders_from_html(home_html, url)
        
        # Clean DOM for text extraction
        def clean_and_extract(html):
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.extract()
            return soup.get_text(separator=" ", strip=True)
            
        page_text = clean_and_extract(home_html)[:6000]
        
        team_url = find_team_page(home_html, url)
        team_html = ""
        if team_url and team_url != url:
            log_progress(self.execution_id, f"[LIVE SCRAPING] Team/leadership page found: {team_url}")
            team_html = smart_fetch(team_url, self.execution_id)
            if team_html:
                team_leaders = extract_leaders_from_html(team_html, url)
                if team_leaders:
                    homepage_leaders = team_leaders
                homepage_emails = list(set(homepage_emails + extract_emails_from_html(team_html)))
                if not homepage_phone:
                    homepage_phone = extract_phone_from_html(team_html)
                socials.update({k: v for k, v in extract_social_links(team_html).items() if k not in socials})
                page_text += " " + clean_and_extract(team_html)[:3000]
                
        contact_pages = find_contact_subpages(home_html, url, location_hint)
        
        # Concurrent probing for subpages
        def probe_subpage(cp_url):
            try:
                cp_html = smart_fetch(cp_url, self.execution_id)
                if cp_html and len(cp_html) >= 500:
                    return cp_url, cp_html
            except Exception:
                pass
            return cp_url, None

        with ThreadPoolExecutor(max_workers=5) as cp_executor:
            futures = {cp_executor.submit(probe_subpage, cp_url): cp_url for cp_url in contact_pages}
            for future in as_completed(futures):
                cp_url, cp_html = future.result()
                if cp_html:
                    log_progress(self.execution_id, f"[LIVE SCRAPING] Probed subpage successfully: {cp_url}")
                    homepage_emails = list(set(homepage_emails + extract_emails_from_html(cp_html)))
                    if not homepage_phone:
                        homepage_phone = extract_phone_from_html(cp_html)
                    socials.update({k: v for k, v in extract_social_links(cp_html).items() if k not in socials})
                    page_text += " " + clean_and_extract(cp_html)[:3000]
                
        # ── AI extraction via Groq (Conditionally Skip) ──
        leader_info = ""
        if homepage_leaders:
            leader_info = " | ".join([f"{l['name']} ({l['title']})" for l in homepage_leaders[:5]])
            
        llm_result = None
        # Try to bypass Groq if we already have a solid leader and email
        best_email_guess = None
        if homepage_emails:
            homepage_emails.sort(key=lambda e: score_email(e), reverse=True)
            best_email_guess = homepage_emails[0]
            
        if groq_key and not (homepage_leaders and best_email_guess and score_email(best_email_guess) >= 40):
            log_progress(self.execution_id, "[LIVE SCRAPING] Groq AI extraction active. Analyzing page data...")
            llm_result = ExtractorService.extract_with_llm(page_text, leader_info, groq_key)
            
        if llm_result:
            contact_name = llm_result.get("contact_name", "Not Available")
            designation = llm_result.get("designation", "Not Available")
            person_linkedin = llm_result.get("person_linkedin_url", "Not Available")
        else:
            contact_name = homepage_leaders[0]["name"] if homepage_leaders else "Office Manager"
            designation = homepage_leaders[0]["title"] if homepage_leaders else "Operations"
            person_linkedin = "Not Available"
            
        company_linkedin = socials.get("company_linkedin", "Not Available")
        phone = homepage_phone.strip() if homepage_phone else "Not Available"
        
        selected_email = None
        email_source = "Not Available"
        if llm_result and llm_result.get("email"):
            selected_email = llm_result.get("email")
            email_source = "Groq LLM Context Analysis"
        elif homepage_emails:
            personal_emails = [e for e in homepage_emails if is_personal_email(e, contact_name)]
            if personal_emails:
                selected_email = personal_emails[0]
                email_source = "Website DOM Extraction (Personal)"
            else:
                selected_email = homepage_emails[0]
                email_source = "Website DOM Extraction (Best Match)"
                
        if not selected_email or score_email(selected_email) < 40:
            generic_emails = [e for e in homepage_emails if e and score_email(e) < 40]
            if generic_emails:
                selected_email = generic_emails[0]
                email_source = "Website DOM Extraction (Generic)"
            else:
                selected_email = selected_email or f"contact@{domain}"
                
        verification_status = "Unverified"
        if selected_email and selected_email != "Not Available":
            # Strict domain checking: discard images, pdfs
            if ".png" in selected_email.lower() or ".pdf" in selected_email.lower():
                selected_email = "Not Available"
            else:
                try:
                    validate_email(selected_email, check_deliverability=True)
                    verification_status = "Valid"
                except EmailNotValidError:
                    try:
                        validate_email(selected_email, check_deliverability=False)
                        verification_status = "Syntax Valid"
                    except EmailNotValidError:
                        verification_status = "Invalid"
                    
        email_domain_match = False
        if selected_email and selected_email != "Not Available":
            ed = selected_email.split('@')[-1].lower()
            wd = domain.lower()
            generic_domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]
            if ed not in generic_domains and (ed == wd or wd.endswith(f".{ed}") or ed.endswith(f".{wd}")):
                email_domain_match = True
                
        page_verification_level = 0
        if contact_name and contact_name != "Office Manager":
            if (team_html and contact_name in team_html) or (contact_name in page_text):
                page_verification_level = 2
            elif contact_name in home_html:
                page_verification_level = 1
                
        linkedin_verified = False
        if person_linkedin and person_linkedin != "Not Available":
            name_parts = [p.lower() for p in contact_name.split() if len(p) > 2]
            if name_parts and any(p in person_linkedin.lower() for p in name_parts):
                linkedin_verified = True
                
        score_data = ScoringService.calculate_lead_score(
            contact_name=contact_name,
            designation=designation,
            email=selected_email,
            phone=phone,
            person_linkedin=person_linkedin,
            company_name=name,
            website=url,
            address=location,
            verification_status=verification_status,
            email_domain_match=email_domain_match,
            page_verification_level=page_verification_level,
            linkedin_verified=linkedin_verified
        )
        
        person_li_source = "Not Available"
        if person_linkedin != "Not Available":
            person_li_source = "Website DOM / Groq AI" if socials.get("person_linkedin") or (llm_result and llm_result.get("person_linkedin_url")) else "DuckDuckGo Search Engine"
            
        source_map = {
            "email": email_source,
            "phone": "tel: link / Page Footer" if homepage_phone else "Not Available",
            "company_linkedin": "Website DOM" if socials.get("company_linkedin") else "Not Available",
            "person_linkedin": person_li_source,
            "discovery": "Exa Neural Search + Playwright Browser",
        }
        
        log_progress(self.execution_id, f"[LIVE SCRAPING] Processing lead for {name} | Email: {selected_email} | Score: {score_data['total_score']}/100")
        
        reject_reason = None
        is_company_lead = False
        if not contact_name or contact_name in ("Office Manager", "Not Available", "null", "NOT_FOUND"):
            is_company_lead = True
            
        if not selected_email or selected_email == "Not Available" or not email_domain_match:
            reject_reason = "Email verification check failed (missing or domain mismatch)"
        elif verification_status != "Valid":
            reject_reason = "Email is unverified (MX Record Failed)"
        elif not url:
            reject_reason = "Website exists check failed"
        elif score_data['total_score'] < 80:
            reject_reason = f"Confidence score ({score_data['total_score']}) < 80"
        elif not is_company_lead:
            if not designation or designation in ("Not Available", "null", "Operations"):
                reject_reason = "Real title check failed for person-level lead"
                
        if reject_reason:
            log_progress(self.execution_id, f"[QUALITY FILTER] Lead for {name} rejected: {reject_reason}")
            return None
            
        # Return valid lead data
        social_links_json = {
            "facebook": socials.get("facebook", ""),
            "twitter": socials.get("twitter", ""),
            "instagram": socials.get("instagram", ""),
            "youtube": socials.get("youtube", ""),
        }
        return {
            "name": name,
            "url": url,
            "address": location,
            "phone": phone,
            "category": category,
            "company_linkedin": company_linkedin,
            "social_links_json": social_links_json,
            "source_map": source_map,
            "contact_name": contact_name,
            "designation": designation,
            "selected_email": selected_email,
            "score_data": score_data
        }

    def _run_live_scraping(self):
        log_progress(self.execution_id, "[LIVE SCRAPING] Starting live scraper with Enterprise Concurrency pipeline...")
        time.sleep(0.5)
        
        category = self.execution.category.strip()
        location = self.execution.location.strip()
        keywords = self.execution.keywords.strip() if self.execution.keywords else ""
        groq_key = os.getenv("GROQ_API_KEY", self.settings.get("groq_api_key", ""))
        max_results = int(self.settings.get("max_search_results", 50))
        target_leads = max_results
        max_scans = 200
        
        location_hint = ""
        if keywords and "Location:" in keywords:
            m = re.search(r"Location:\s*([^|]+)", keywords)
            if m:
                location_hint = m.group(1).strip()
                
        is_direct_enrichment = category == "Direct Enrichment"
        search_variations = []
        if not is_direct_enrichment:
            log_progress(self.execution_id, "[LIVE SCRAPING] Generating semantic search variations via Groq AI...")
            search_variations = ExtractorService.generate_search_variations(category, location, keywords, groq_key)
            if search_variations:
                search_variations = search_variations[:3]
                log_progress(self.execution_id, f"[LIVE SCRAPING] Generated {len(search_variations)} search variations (Capped at 3).")
            else:
                base_query = f"{category} companies in {location}"
                if keywords:
                    base_query += f" {keywords}"
                search_variations = [base_query]
        else:
            search_variations = [f"{keywords}"]
            
        companies_added = 0
        contacts_added = 0
        seen_domains = set()
        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading
        
        db_lock = threading.Lock()
        
        for iteration, search_query in enumerate(search_variations, start=1):
            if contacts_added >= target_leads or companies_added >= max_scans:
                break
                
            log_progress(self.execution_id, f"Iteration {iteration}/{len(search_variations)}\nSearching: {search_query}")
            
            exa = get_exa_client()
            websites = []
            if exa:
                try:
                    res = exa.search_and_contents(search_query, type="keyword", num_results=20, text=True)
                    for r in res.results:
                        if not r.url: continue
                        domain_parsed = urlparse(r.url).netloc.lower().replace("www.", "")
                        
                        if any(b in domain_parsed for b in HARD_BLOCKED_DOMAINS):
                            continue
                            
                        if any(b in domain_parsed for b in DIRECTORY_DOMAINS) or is_listicle_or_blog(r.url, r.title):
                            log_progress(self.execution_id, f"[LIVE SCRAPING] Scraping directory/listicle for companies: {r.url}")
                            dir_html = raw_html_fetch(r.url, self.execution_id)
                            extracted = extract_companies_from_directory(dir_html, r.url, self.execution_id)
                            ext_urls = extracted["urls"]
                            ext_names = extracted["names"]
                            
                            total_extracted = len(ext_urls) + len(ext_names)
                            if total_extracted > 0:
                                log_progress(self.execution_id, f"[LIVE SCRAPING] Extracted {len(ext_urls)} external links and {len(ext_names)} profile names from {r.url}")
                            else:
                                reason = "Unknown reason"
                                if not dir_html:
                                    reason = "Empty HTML (fetch failed or anti-bot protection)"
                                elif "cloudflare" in dir_html.lower() or "captcha" in dir_html.lower() or "challenge-error" in dir_html.lower():
                                    reason = "Anti-bot protection triggered (Cloudflare/Captcha detected)"
                                elif "<html" not in dir_html.lower():
                                    reason = "HTML parsing failed (Invalid HTML returned)"
                                else:
                                    soup_test = BeautifulSoup(dir_html, "html.parser")
                                    a_tags = soup_test.find_all("a", href=True)
                                    if len(a_tags) == 0:
                                        reason = "No anchor tags found (JavaScript-rendered page?)"
                                    else:
                                        reason = f"Filtering removed all {len(a_tags)} links (no external companies or recognizable profile links found)"
                                log_progress(self.execution_id, f"[LIVE SCRAPING] Zero companies extracted from {r.url}. Reason: {reason}")
                            
                            for c_url in ext_urls:
                                c_domain = urlparse(c_url).netloc.lower().replace("www.", "")
                                websites.append({"url": c_url, "name": c_domain, "domain": c_domain})
                                
                            # Resolve company names via Exa
                            if len(ext_names) > 0 and exa:
                                log_progress(self.execution_id, f"[LIVE SCRAPING] Resolving {len(ext_names)} official company websites via Exa...")
                                for c_name in ext_names:
                                    try:
                                        res_search = exa.search_and_contents(f"{c_name} official website", type="keyword", num_results=1, text=False)
                                        if res_search.results:
                                            off_url = res_search.results[0].url
                                            off_domain = urlparse(off_url).netloc.lower().replace("www.", "")
                                            base_r = urlparse(r.url).netloc.lower().replace("www.", "")
                                            if off_domain != base_r and not any(b in off_domain for b in HARD_BLOCKED_DOMAINS) and not any(b in off_domain for b in DIRECTORY_DOMAINS):
                                                websites.append({"url": off_url, "name": c_name, "domain": off_domain})
                                    except Exception:
                                        pass
                            continue
                            
                        websites.append({"url": r.url, "name": r.title or domain_parsed, "domain": domain_parsed})
                except Exception as e:
                    log_progress(self.execution_id, f"[WARNING] Exa search failed: {e}")
                    
            if not websites:
                continue
                
            log_progress(self.execution_id, f"[LIVE SCRAPING] Found {len(websites)} new target websites. Processing batch concurrently...")
            
            # Use ThreadPoolExecutor for concurrent fetching and extraction
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {}
                for site in websites:
                    if contacts_added >= target_leads or companies_added >= max_scans:
                        break
                    domain = site["domain"]
                    with db_lock:
                        if domain in seen_domains:
                            continue
                        seen_domains.add(domain)
                        companies_added += 1
                        
                    future = executor.submit(self._process_website, site, location_hint, groq_key, category, location)
                    futures[future] = site
                    
                for future in as_completed(futures):
                    result = future.result(timeout=120)
                    if result:
                        with db_lock:
                            from .scraper import normalize_url
                            normalized_site_url = normalize_url(result["url"])
                            existing_company = self.db.query(Company).filter(Company.website == normalized_site_url).first()
                            
                            if existing_company:
                                log_progress(self.execution_id, f"[DUPLICATE] Company already processed: {result['url']}")
                                continue
                                
                            company = Company(
                                execution_id=self.execution_id,
                                name=result["name"],
                                website=normalized_site_url,
                                address=result["address"],
                                phone=result["phone"],
                                industry=result["category"],
                                linkedin_url=result["company_linkedin"],
                                social_links=json.dumps(result["social_links_json"]),
                                source_attribution=json.dumps(result["source_map"]),
                            )
                            self.db.add(company)
                            self.db.flush()
                            self.db.refresh(company)
                            
                            from sqlalchemy import or_
                            person_li = result["score_data"].get("person_linkedin")
                            
                            filters = [Contact.email == result["selected_email"]]
                            if person_li and person_li != "Not Available":
                                filters.append(Contact.linkedin_url == person_li)
                                
                            existing_contact = (
                                self.db.query(Contact)
                                .join(Company, Contact.company_id == Company.id)
                                .filter(or_(*filters))
                                .first()
                            )
                            
                            if existing_contact:
                                log_progress(self.execution_id, f"[DUPLICATE] Contact already processed: {result['selected_email']}")
                                continue
                                
                            contact = Contact(
    company_id=company.id,
    name=result["contact_name"],
    designation=result["designation"],
    email=result["selected_email"],
    linkedin_url=result["score_data"].get("person_linkedin"),
    lead_score=result["score_data"].get("total_score", 0),
    verification_status="Verified",
    score_breakdown=json.dumps(
        result["score_data"].get("breakdown", {})
    ),
    source_attribution=json.dumps(
        result.get("source_map", {})
    )
)
                            self.db.add(contact)
                            self.db.flush()
                            contacts_added += 1
                            log_progress(self.execution_id, f"[SAVED] Lead {result['contact_name']} @ {result['name']} saved to database.")
                            
                            # Dispatch background LinkedIn lookup
                            async_linkedin_worker(
                                contact_id=contact.id,
                                company_id=company.id,
                                contact_name=result["contact_name"],
                                company_name=result["name"],
                                location=result["address"],
                                domain=result["url"],
                                category=result["category"],
                                groq_key=groq_key
                            )
            try:
                self.db.commit() # Batch commit after each chunk of websites finishes
            except Exception as e:
                log_progress(self.execution_id, f"[WARNING] Batch commit failed: {e}")
                self.db.rollback()
            
        self.db.commit()
        if self.execution:
            self.execution.status = "Completed"
            self.execution.completed_at = datetime.utcnow()
            self.db.commit()


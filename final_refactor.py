import re

def refactor_scraper():
    with open('backend/scraper.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update normalize_url to aggressively strip URL query parameters and fragments.
    old_normalize = """def normalize_url(url: str) -> str:
    # Basic normalization to prevent obvious duplicates
    url = url.lower().strip()
    if url.startswith("http://"):
        url = url[7:]
    elif url.startswith("https://"):
        url = url[8:]
    if url.startswith("www."):
        url = url[4:]
    if url.endswith("/"):
        url = url[:-1]
    return url"""
    
    new_normalize = """from urllib.parse import urlsplit

def normalize_url(url: str) -> str:
    url = url.lower().strip()
    try:
        if not url.startswith("http"):
            url = "http://" + url
        parts = urlsplit(url)
        netloc = parts.netloc
        if netloc.startswith("www."):
            netloc = netloc[4:]
        path = parts.path
        if path.endswith("/"):
            path = path[:-1]
        return netloc + path
    except:
        pass
    if url.startswith("http://"):
        url = url[7:]
    elif url.startswith("https://"):
        url = url[8:]
    if url.startswith("www."):
        url = url[4:]
    if url.endswith("/"):
        url = url[:-1]
    return url"""
    
    content = content.replace(old_normalize, new_normalize)
    
    # 2. Update score_email to reject placeholder emails
    old_score = """    if not email or "@" not in email:
        return 0
    email = email.lower()"""
    new_score = """    if not email or "@" not in email:
        return 0
    email = email.lower()
    if "yourname" in email or "domain.com" in email or email.startswith("email@"):
        return 0"""
    content = content.replace(old_score, new_score)
    
    # 3. In _run_live_scraping, wrap self.db.commit() and use future.result(timeout=120)
    content = content.replace("result = future.result()", "result = future.result(timeout=120)")
    
    # Batch commit wrap
    content = content.replace(
        "            self.db.commit() # Batch commit after each chunk of websites finishes",
        """            try:
                self.db.commit() # Batch commit after each chunk of websites finishes
            except Exception as e:
                log_progress(self.execution_id, f"[WARNING] Batch commit failed: {e}")
                self.db.rollback()"""
    )
    
    # Remove unused functions using regex to match entire function blocks safely, or just replacing definition
    # For find_website_exa, guess_email_from_name, find_leader_exa
    content = re.sub(r'def find_website_exa.*?return None\n', '', content, flags=re.DOTALL)
    content = re.sub(r'def guess_email_from_name.*?return \[\]\n', '', content, flags=re.DOTALL)
    content = re.sub(r'def find_leader_exa.*?return None\n', '', content, flags=re.DOTALL)
    
    with open('backend/scraper.py', 'w', encoding='utf-8') as f:
        f.write(content)

def refactor_scoring():
    with open('backend/scoring.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace("comp_linkedin: str,", "")
    content = content.replace("comp_linkedin=\"\",", "")
    
    with open('backend/scoring.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    refactor_scraper()
    refactor_scoring()
    print("Final refactoring complete")

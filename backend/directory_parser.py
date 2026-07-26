import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup

class DirectoryExtractor:
    def __init__(self, blocked_domains, directory_domains):
        self.blocked_domains = set(blocked_domains)
        self.directory_domains = set(directory_domains)

    def extract_companies(self, html: str, base_url: str) -> dict:
        if not html:
            return {"urls": set(), "names": set()}

        base_domain = ""
        try:
            base_domain = urlparse(base_url).netloc.lower().replace("www.", "")
        except Exception:
            pass

        soup = BeautifulSoup(html, "html.parser")

        # 1. Strip unwanted structural elements
        for tag in soup(["nav", "footer", "header", "aside", "script", "style", "noscript"]):
            tag.decompose()

        # 2. Identify potential company cards
        # We look for containers that might represent a list item or card
        cards = soup.find_all(["div", "article", "section", "li", "tr"])
        
        found_urls = set()
        found_names = set()

        for card in cards:
            # Find company name in headers or strong elements
            company_name = self._extract_company_name(card)
            
            # Find all links in the card
            links = card.find_all("a", href=True)
            if not links:
                continue

            candidates = []
            for a in links:
                href = a["href"].strip()
                text = a.get_text(strip=True)
                score = self._score_url(href, text, company_name, base_domain)
                candidates.append((score, href, text))
            
            if not candidates:
                continue
                
            # Sort by score descending
            candidates.sort(key=lambda x: x[0], reverse=True)
            best_score, best_href, best_text = candidates[0]
            
            # Only accept if the score is somewhat decent (e.g., > 20)
            if best_score > 20:
                normalized = best_href.rstrip("/")
                try:
                    parsed = urlparse(normalized)
                    domain = parsed.netloc.lower().replace("www.", "")
                    # Ensure it's not the directory itself or a blocked domain
                    if domain and domain != base_domain and not any(b in domain for b in self.blocked_domains) and not any(b in domain for b in self.directory_domains):
                        found_urls.add(normalized)
                        continue
                except Exception:
                    pass

            # If we couldn't find a strong external link, use the name or internal profile path for Exa resolution
            if company_name and len(company_name) > 2:
                found_names.add(company_name)
            else:
                # Fallback to internal profile slug extraction if name extraction failed
                for score, href, text in candidates:
                    path_only = ""
                    if href.startswith("/"):
                        path_only = href.lower()
                    elif href.startswith("http"):
                        try:
                            path_only = urlparse(href).path.lower()
                        except Exception:
                            pass
                    
                    if path_only:
                        for profile_prefix in ["/company/", "/profile/", "/developers/", "/agency/"]:
                            if profile_prefix in path_only:
                                idx = path_only.find(profile_prefix) + len(profile_prefix)
                                slug = path_only[idx:].split("/")[0]
                                if len(slug) > 2:
                                    clean_name = slug.replace("-", " ").title()
                                    found_names.add(clean_name)
                                break

        return {"urls": found_urls, "names": found_names}

    def _extract_company_name(self, card) -> str:
        # Try headers first
        for tag_name in ["h2", "h3", "h4"]:
            header = card.find(tag_name)
            if header:
                text = header.get_text(strip=True)
                if len(text) > 2 and len(text) < 50:
                    return text
        
        # Try bold anchor text
        for a in card.find_all("a"):
            if a.find(["b", "strong"]):
                text = a.get_text(strip=True)
                if len(text) > 2 and len(text) < 50:
                    return text
                    
        return ""

    def _score_url(self, href: str, text: str, company_name: str, base_domain: str) -> int:
        score = 0
        
        # Basic categorization
        is_http = href.startswith("http")
        domain = ""
        path = ""
        
        if is_http:
            try:
                parsed = urlparse(href)
                domain = parsed.netloc.lower().replace("www.", "")
                path = parsed.path.lower()
            except Exception:
                pass
        else:
            path = href.lower()
            
        # +40 if external domain
        if is_http and domain and domain != base_domain:
            score += 40
            
        # +30 if anchor text equals company name
        if text and company_name and text.lower() == company_name.lower():
            score += 30
            
        # +20 if URL appears inside company card
        # Note: Since we are iterating inside a card, all these links get +20
        score += 20
        
        # +10 if HTTPS
        if href.startswith("https"):
            score += 10
            
        # -50 if blocked domain
        if domain and any(b in domain for b in self.blocked_domains):
            score -= 50
            
        # -100 if social media
        socials = ["linkedin.com", "facebook.com", "twitter.com", "x.com", "instagram.com", "youtube.com"]
        if domain and any(s in domain for s in socials):
            score -= 100
            
        # -30 if blog/article
        if any(p in path for p in ["/blog", "/article", "/news"]):
            score -= 30
            
        # -20 if contains /directory/
        if "/directory/" in path:
            score -= 20
            
        # -20 if contains /category/
        if "/category/" in path:
            score -= 20
            
        # -20 if contains /author/
        if "/author/" in path:
            score -= 20
            
        # -20 if contains /tag/
        if "/tag/" in path:
            score -= 20
            
        return score

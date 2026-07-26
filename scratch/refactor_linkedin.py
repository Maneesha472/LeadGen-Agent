import re

def refactor_scraper():
    with open("backend/scraper.py", "r", encoding="utf-8") as f:
        content = f.read()

    # Find find_company_linkedin_exa
    old_func_match = re.search(r"def find_company_linkedin_exa\(company_name: str, location: str\) -> str:.*?return \"Not Available\"", content, flags=re.DOTALL)
    if not old_func_match:
        print("Could not find function")
        return
        
    old_func_str = old_func_match.group(0)

    new_func_str = """def find_company_linkedin_exa(company_name: str, location: str, domain: str, industry: str, groq_key: str = None) -> str:
    \"\"\"Find and STRICTLY VERIFY LinkedIn company page URL via Exa search.\"\"\"
    exa = get_exa_client()
    if not exa: return "Not Available"
    
    try:
        search_query = f"site:linkedin.com/company/ {company_name}"
        if location:
            search_query += f" {location}"
            
        res = exa.search_and_contents(search_query, type="keyword", num_results=3, text={"max_characters": 800})
        
        candidates = []
        for r in res.results:
            if "linkedin.com/company/" in r.url:
                candidates.append({"url": r.url, "title": r.title or "", "text": r.text or ""})
                
        if not candidates:
            return "Not Available"

        # If LLM key is available, use it for strict verification
        if groq_key:
            prompt = f\"\"\"You are verifying a LinkedIn company profile for a B2B lead generation system.
Target Company Identity:
- Name: {company_name}
- Domain: {domain}
- Location: {location}
- Industry: {industry}

Candidates found:
\"\"\"
            for i, c in enumerate(candidates):
                prompt += f"\\n[{i}] URL: {c['url']}\\nTitle: {c['title']}\\nText: {c['text'][:300]}\\n"
                
            prompt += \"\"\"
Task: Which candidate strictly matches the Target Company? Pay attention to location (e.g. Chicago vs Bangalore) and domain mismatches.
Return ONLY a valid JSON object with:
{
  "match_found": boolean,
  "matched_url": "string or null"
}
\"\"\"
            llm_result = ExtractorService._call_groq(prompt, groq_key)
            if llm_result and llm_result.get("match_found") and llm_result.get("matched_url"):
                return llm_result.get("matched_url")
                
        # Keyword Fallback (if Groq fails or rate limits)
        target_loc = location.split(',')[0].lower().strip()
        for c in candidates:
            text_lower = (c['title'] + " " + c['text']).lower()
            
            # Reject obvious wrong locations (hardcoded common false positives for Chicago)
            if "chicago" in target_loc and ("bengaluru" in text_lower or "bangalore" in text_lower or "india" in text_lower):
                continue
                
            # If location is in text, accept it
            if target_loc in text_lower:
                return c['url']
                
            # If domain is in text, accept it
            if domain.split('.')[0] in text_lower:
                return c['url']
                
        # If fallback fails to confidently match, return Not Available
        return "Not Available"
    except Exception as e:
        print(f"[EXA LinkedIn Verification Error]: {e}")
        pass
        
    return "Not Available\"\"\"
    # Strip the trailing quotes that got added by the replacement string
    new_func_str = new_func_str.replace('return "Not Available"\"\"\"', 'return "Not Available"')

    content = content.replace(old_func_str, new_func_str)

    with open("backend/scraper.py", "w", encoding="utf-8") as f:
        f.write(content)
        
    print("Function replaced.")

refactor_scraper()

import json
import requests
import time
import threading
from typing import Optional

class ExtractorService:
    # Throttle Groq API to a maximum of 2 concurrent connections to prevent Rate Limiting
    _groq_semaphore = threading.Semaphore(2)

    @staticmethod
    def extract_with_llm(page_text: str, search_snippets: str, groq_api_key: str) -> Optional[dict]:
        """
        Invokes Groq LLM (llama-3.3-70b-versatile) with a strict B2B extraction schema.
        Ported from the Leader Agent scraper_core.js approach.
        """
        page_text = (page_text or "")[:12000]
        search_snippets = (search_snippets or "")[:4000]

        prompt = f"""You are an enterprise-grade B2B lead generation extraction engine. Return ONLY valid JSON. Never guess, infer, or hallucinate any information.
Analyze the target website text AND search engine snippets provided below.

Extract the REAL, VERIFIED information ONLY from what is present in the text.

IMPORTANT RULES:
- Never guess a person's name.
- Never use company names as contact names.
- Never use page headings, navigation menus, slogans, or section titles as contact names.
- Never invent an email address.
- Never construct an email address using the company domain.
- Never assign another employee's email to the extracted contact.
- Return null if unsure.
- If no real decision maker is found, return:
  "contact_name": "NOT_FOUND"
  "designation": "NOT_FOUND"
- STRICTLY ENFORCE this executive priority: Founder > Co-Founder > CEO > CTO > COO > President > VP Engineering > Head of Engineering > Director > Head of Sales.
- STRICTLY FORBID non-executive roles. Do NOT extract: Office Manager, Receptionist, Admin, Support, General Operations. If only these exist, return "NOT_FOUND".
- Only return information that is explicitly present in the provided text.
- Never infer or hallucinate missing information.

1. Contact Person Name - Extract ONLY one real human decision maker. Do NOT return: Company names, Headings, Slogans, About Us, Services, Products, Cities, Page titles. If no real person is found, output "NOT_FOUND".

2. Job Title / Role - Strictly enforce executive priority. Do NOT extract Office Manager, Receptionist, Admin, Support, etc. If no real decision maker is found, output "NOT_FOUND".

3. Direct Email Address - Look for mailto: links or email patterns. ONLY extract if it clearly belongs to the person (e.g. name match) or is a general company email. If you are not sure, output null.

4. Phone Number - Look for tel: links, phone patterns. If missing, output "Not Available".

5. Official Company LinkedIn URL - Must be linkedin.com/company/... URL. If missing, output "Not Available".

6. Executive / Personal LinkedIn Profile URL - Must be linkedin.com/in/... URL. If missing, output "Not Available".

7. Company Street Address / Physical Location. If missing, output "Not Available".

8. Social Media Links (Facebook, Twitter/X, Instagram, YouTube URLs if present).

EMAIL RULES:
1. ONLY output an email if it is explicitly present in the text.
2. DO NOT guess or hallucinate emails using domain patterns.
3. If an email belongs to a different person, do not assign it to the contact. Output null instead.
4. Never construct an email using the company website domain.
5. Reject fake or placeholder emails (example@example.com, test@test.com, noreply@, no-reply@, donotreply@).

For LinkedIn:
- Only output real URLs visible in the text.
- Never guess LinkedIn URLs.
- Company LinkedIn must be linkedin.com/company/...
- Personal LinkedIn must be linkedin.com/in/...

Website Text:
---
{page_text}
---

Search Engine Snippets:
---
{search_snippets}
---

Return STRICTLY as a valid JSON object:

{{
  "contact_name": "string or null",
  "designation": "string or null",
  "email": "string",
  "phone": "string",
  "company_linkedin_url": "string",
  "person_linkedin_url": "string",
  "address": "string",
  "social_links": {{
     "facebook": "string",
     "twitter": "string",
     "instagram": "string",
     "youtube": "string"
  }}
}}
"""

        if not groq_api_key:
            return None
        return ExtractorService._call_groq(prompt, groq_api_key)

    @staticmethod
    def _call_groq(prompt: str, api_key: str) -> Optional[dict]:
        with ExtractorService._groq_semaphore:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        payload = {
            "model": "llama-3.3-70b-versatile",
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "You are an enterprise-grade B2B lead generation extraction engine. Return ONLY valid JSON. Never guess, infer, or hallucinate any information."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0,
            "max_tokens": 1024
        }
        import random
        for attempt in range(5):
            try:
                r = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=60
                )

                if r.status_code == 200:
                    text_resp = r.json()["choices"][0]["message"]["content"]
                    text_resp = text_resp.strip()

                    if text_resp.startswith("```json"):
                        text_resp = text_resp[7:]
                    if text_resp.startswith("```"):
                        text_resp = text_resp[3:]
                    if text_resp.endswith("```"):
                        text_resp = text_resp[:-3]

                    return json.loads(text_resp.strip())

                elif r.status_code == 429:
                    # Exponential backoff with jitter
                    wait_time = (2 ** attempt) + random.uniform(1, 3)
                    print(f"[GROQ] Rate limit hit. Retry {attempt + 1}/5 (waiting {wait_time:.2f}s)")
                    time.sleep(wait_time)
                    continue

                elif r.status_code == 401:
                    print("[GROQ] Invalid API key.")
                    break

                else:
                    print(f"[GROQ] Error {r.status_code}: {r.text[:200]}")
                    break

            except Exception as e:
                print(f"[GROQ] Attempt {attempt + 1} failed: {e}")
                time.sleep(2)

        return None

    @staticmethod
    def generate_search_variations(category: str, location: str, keywords: str, groq_api_key: str) -> list:
        """
        Dynamically generates semantic search variations for Exa AI using Groq LLM.
        """
        if not groq_api_key:
            return []
            
        prompt = f"""You are an expert at B2B lead generation search strategies for Exa AI.
Generate 10 highly relevant, semantic search query variations to find OFFICIAL COMPANY WEBSITES matching the user's exact criteria.
Your goal is to provide diverse search strings that will uncover different companies in the requested niche.
The queries should be phrased to target official business domains that are likely to have "About Us", "Team", "Leadership", or "Contact" pages.

Source of Truth Criteria:
- Category: {category}
- Location: {location}
- Keywords/Filters: {keywords}

RULES:
1. Do NOT hardcode unrelated variations. Base ALL variations STRICTLY on the user's Category, Location, and Keywords above.
2. Do NOT include words like "list", "directory", "top 10", "best", or "reviews". We want to find actual company websites, not blog posts.
3. Ensure the variations are natural search phrases or descriptors that an official company would use to describe itself on its homepage.

Return STRICTLY as a valid JSON array of strings:
{{
  "variations": [
    "query 1",
    "query 2",
    ...
  ]
}}"""
        result = ExtractorService._call_groq(prompt, groq_api_key)
        if result and "variations" in result and isinstance(result["variations"], list):
            return result["variations"]
        return []

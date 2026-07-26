import requests
from typing import Optional, Dict

class EnrichmentService:
    def __init__(self, user_settings: dict):
        self.settings = user_settings or {}
        self.apollo_key = self.settings.get("apollo_api_key", "").strip()
        self.proxycurl_key = self.settings.get("proxycurl_api_key", "").strip()
        self.pdl_key = self.settings.get("pdl_api_key", "").strip()

    def enrich_contact(self, domain: str, person_name: str = "", current_email: str = "", current_phone: str = "", current_linkedin: str = "") -> Dict[str, dict]:
        """
        Queries enabled enrichment providers if fields are missing.
        Returns dict: {
           "enriched_data": {"email": ..., "phone": ..., "person_linkedin": ..., "company_linkedin": ..., "contact_name": ..., "designation": ...},
           "source_attribution": {"email": ..., "phone": ..., "linkedin": ...}
        }
        """
        enriched = {}
        source_attribution = {}

        # 1. Apollo API Enrichment
        if self.apollo_key and (current_email == "Not Available" or current_phone == "Not Available"):
            apollo_data = self._query_apollo(domain, person_name)
            if apollo_data:
                if apollo_data.get("email") and current_email == "Not Available":
                    enriched["email"] = apollo_data["email"]
                    source_attribution["email"] = "Apollo API"
                if apollo_data.get("phone") and current_phone == "Not Available":
                    enriched["phone"] = apollo_data["phone"]
                    source_attribution["phone"] = "Apollo API"
                if apollo_data.get("contact_name"):
                    enriched["contact_name"] = apollo_data["contact_name"]
                if apollo_data.get("designation"):
                    enriched["designation"] = apollo_data["designation"]

        # 2. Proxycurl API Enrichment (for LinkedIn URL enrichment)
        if self.proxycurl_key and current_linkedin != "Not Available" and "linkedin.com/in/" in current_linkedin:
            proxy_data = self._query_proxycurl(current_linkedin)
            if proxy_data:
                if proxy_data.get("email") and enriched.get("email", current_email) == "Not Available":
                    enriched["email"] = proxy_data["email"]
                    source_attribution["email"] = "Proxycurl API"
                if proxy_data.get("phone") and enriched.get("phone", current_phone) == "Not Available":
                    enriched["phone"] = proxy_data["phone"]
                    source_attribution["phone"] = "Proxycurl API"
                if proxy_data.get("designation"):
                    enriched["designation"] = proxy_data["designation"]

        # 3. People Data Labs API Enrichment
        if self.pdl_key and (enriched.get("email", current_email) == "Not Available"):
            pdl_data = self._query_pdl(domain, person_name)
            if pdl_data:
                if pdl_data.get("email") and enriched.get("email", current_email) == "Not Available":
                    enriched["email"] = pdl_data["email"]
                    source_attribution["email"] = "People Data Labs API"
                if pdl_data.get("phone") and enriched.get("phone", current_phone) == "Not Available":
                    enriched["phone"] = pdl_data["phone"]
                    source_attribution["phone"] = "People Data Labs API"

        return {
            "enriched_data": enriched,
            "source_attribution": source_attribution
        }

    def _query_apollo(self, domain: str, person_name: str) -> Optional[dict]:
        url = "https://api.apollo.io/v1/people/match"
        payload = {
            "api_key": self.apollo_key,
            "domain": domain,
            "name": person_name if person_name != "Office Manager" else ""
        }
        try:
            r = requests.post(url, json=payload, timeout=8)
            if r.status_code == 200:
                person = r.json().get("person") or {}
                return {
                    "email": person.get("email"),
                    "phone": person.get("sanitized_phone"),
                    "contact_name": f"{person.get('first_name', '')} {person.get('last_name', '')}".strip(),
                    "designation": person.get("title")
                }
        except Exception:
            pass
        return None

    def _query_proxycurl(self, linkedin_url: str) -> Optional[dict]:
        url = "https://nubela.co/proxycurl/api/v2/linkedin"
        headers = {"Authorization": f"Bearer {self.proxycurl_key}"}
        params = {"url": linkedin_url, "fallback_to_cache": "on-error"}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=8)
            if r.status_code == 200:
                data = r.json()
                experiences = data.get("experiences", [])
                curr_title = experiences[0].get("title") if experiences else data.get("occupation")
                return {
                    "email": data.get("personal_email") or data.get("work_email"),
                    "phone": data.get("phone_number"),
                    "designation": curr_title
                }
        except Exception:
            pass
        return None

    def _query_pdl(self, domain: str, person_name: str) -> Optional[dict]:
        url = "https://api.peopledatalabs.com/v5/person/enrich"
        headers = {"X-Api-Key": self.pdl_key}
        params = {"company": domain, "name": person_name}
        try:
            r = requests.get(url, headers=headers, params=params, timeout=8)
            if r.status_code == 200:
                data = r.json().get("data", {})
                emails = data.get("emails", [])
                phones = data.get("phone_numbers", [])
                return {
                    "email": emails[0].get("address") if emails else None,
                    "phone": phones[0] if phones else None
                }
        except Exception:
            pass
        return None

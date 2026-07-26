import re
import requests
from typing import Dict

class EmailValidatorService:
    def __init__(self, user_settings: dict):
        self.settings = user_settings or {}
        self.zerobounce_key = self.settings.get("zerobounce_api_key", "").strip()
        self.neverbounce_key = self.settings.get("neverbounce_api_key", "").strip()

    def validate_email(self, email: str) -> Dict[str, str]:
        """
        Validates email syntax, disposable domains, and external API verification services.
        Returns dict: {"status": "Valid" | "Invalid" | "Risky" | "Unverified", "provider": str}
        """
        if not email or email == "Not Available":
            return {"status": "Unverified", "provider": "Syntax Check"}

        # 1. Regex Syntax Check
        regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(regex, email):
            return {"status": "Invalid", "provider": "Syntax Validation"}

        # 2. Check for disposable and free email domain blocklist (Corporate Only)
        domain = email.split("@")[-1].lower()
        disposable_domains = {"mailinator.com", "10minutemail.com", "tempmail.com", "guerrillamail.com", "trashmail.com"}
        free_domains = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "aol.com", "icloud.com", "mail.com", "msn.com", "yandex.com", "zoho.com"}
        
        if domain in disposable_domains:
            return {"status": "Invalid", "provider": "Disposable Domain Filter"}
        if domain in free_domains:
            return {"status": "Invalid", "provider": "Free Email Filter (Corporate Only)"}

        # 3. ZeroBounce API Validation
        if self.zerobounce_key:
            zb_res = self._validate_zerobounce(email)
            if zb_res:
                return zb_res

        # 4. NeverBounce API Validation
        if self.neverbounce_key:
            nb_res = self._validate_neverbounce(email)
            if nb_res:
                return nb_res

        # Default fallback for clean syntax emails without paid verification
        return {"status": "Valid", "provider": "Pattern & Syntax Validation"}

    def _validate_zerobounce(self, email: str) -> dict:
        url = "https://api.zerobounce.net/v2/validate"
        params = {"api_key": self.zerobounce_key, "email": email}
        try:
            r = requests.get(url, params=params, timeout=6)
            if r.status_code == 200:
                status = r.json().get("status", "").lower()
                if status == "valid":
                    return {"status": "Valid", "provider": "ZeroBounce API"}
                elif status in ["invalid", "spamtrap"]:
                    return {"status": "Invalid", "provider": "ZeroBounce API"}
                elif status in ["catch_all", "do_not_mail", "unknown"]:
                    return {"status": "Risky", "provider": "ZeroBounce API"}
        except Exception:
            pass
        return None

    def _validate_neverbounce(self, email: str) -> dict:
        url = "https://api.neverbounce.com/v4/single/check"
        params = {"key": self.neverbounce_key, "email": email}
        try:
            r = requests.get(url, params=params, timeout=6)
            if r.status_code == 200:
                result = r.json().get("result", "").lower()
                if result == "valid":
                    return {"status": "Valid", "provider": "NeverBounce API"}
                elif result == "invalid":
                    return {"status": "Invalid", "provider": "NeverBounce API"}
                elif result in ["disposable", "catchall", "unknown"]:
                    return {"status": "Risky", "provider": "NeverBounce API"}
        except Exception:
            pass
        return None

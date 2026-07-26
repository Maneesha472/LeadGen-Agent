from typing import Dict

class ScoringService:
    @staticmethod
    def calculate_lead_score(contact_name: str, designation: str, email: str, phone: str, 
                              person_linkedin: str, 
                             company_name: str, website: str, address: str, 
                             verification_status: str,
                             email_domain_match: bool = False,
                             page_verification_level: int = 0,
                             linkedin_verified: bool = False,
                             location_match: bool = False) -> Dict[str, any]:
        """
        Calculates a 0-100 Lead Quality Score across multi-point verification:
        - Official company email: +25
        - Email domain matches website: +20
        - Real CEO/Founder found: +20
        - LinkedIn matches company: +15
        - Official website evidence: +10
        - Phone number: +5
        - Location matches: +5
        """
        breakdown = {
    "official_email": 0,
    "domain_match": 0,
    "real_ceo": 0,
    "linkedin_match": 0,
    "website_evidence": 0,
    "phone": 0,
    "location": 0,
    "company_validity": 0
}

        # 1. Official company email (+25)
        if (
            email
            and email != "Not Available"
            and verification_status == "Valid"
            and "example.com" not in email.lower()
            and "test@" not in email.lower()
            and "noreply" not in email.lower()
        ):
            breakdown["official_email"] = 25

        # 2. Email domain matches website (+20)
        if email_domain_match:
            breakdown["domain_match"] = 20

        # 3. Real CEO/Founder found (+20)
        if designation and designation.lower() not in ["operations", "not available", "null"]:
            lower_desig = designation.lower()
            if any(t in lower_desig for t in ["ceo", "founder", "owner", "president", "managing director", "partner", "co-founder", "executive director", "chairman", "principal"]):
                breakdown["real_ceo"] = 20

        # 4. LinkedIn matches company (+15)
        if linkedin_verified:
            breakdown["linkedin_match"] = 15

        # 5. Official website evidence (+10)
        if page_verification_level >= 2:
            breakdown["website_evidence"] = 10

        # 6. Phone number (+5)
        if phone and phone != "Not Available" and len("".join(filter(str.isdigit, str(phone)))) >= 10:
            breakdown["phone"] = 5
            
        # 7. Location matches (+5)
        if location_match:
            breakdown["location"] = 5
            
        # 8. Company Level Bonus (+35) if no person but highly verified company email
        if breakdown.get("real_ceo", 0) == 0 and breakdown.get("official_email", 0) > 0 and breakdown.get("domain_match", 0) > 0:
            breakdown["company_validity"] = 35
        
        total_score = sum(breakdown.values())

        return {
            "total_score": min(100, total_score),
            "breakdown": breakdown
        }

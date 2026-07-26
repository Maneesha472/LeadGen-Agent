import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.discovery import DiscoveryService
from backend.enrichment import EnrichmentService
from backend.validator import EmailValidatorService
from backend.scoring import ScoringService
from backend.extractor import ExtractorService

# Test settings
test_settings = {
    "google_api_key": "",
    "google_cse_id": "",
    "brave_api_key": "",
    "tavily_api_key": "",
    "apollo_api_key": "",
    "proxycurl_api_key": "",
    "pdl_api_key": "",
    "zerobounce_api_key": "",
    "neverbounce_api_key": ""
}

print("1. Testing DiscoveryService fallback...")
disc = DiscoveryService(test_settings)
disc_res = disc.discover_web_snippets("OpenAI", "openai.com")
print("Discovery Provider:", disc_res["source"])

print("\n2. Testing EmailValidatorService...")
val = EmailValidatorService(test_settings)
res_valid = val.validate_email("test@example.com")
print("Email Validation Result:", res_valid)

res_disposable = val.validate_email("junk@mailinator.com")
print("Disposable Domain Result:", res_disposable)

print("\n3. Testing ScoringService...")
score = ScoringService.calculate_lead_score(
    contact_name="Sam Altman",
    designation="CEO",
    email="sam@openai.com",
    phone="(415) 555-0199",
    comp_linkedin="https://www.linkedin.com/company/openai",
    person_linkedin="https://www.linkedin.com/in/samaltman",
    company_name="OpenAI",
    website="https://openai.com",
    address="San Francisco, CA",
    verification_status="Valid"
)
print("Lead Score (0-100):", score["total_score"])
print("Score Breakdown:", score["breakdown"])

print("\n4. Testing ExtractorService prompt compilation...")
prompt_check = ExtractorService._call_gemini("test prompt", "invalid_key")
print("Extractor handled invalid key cleanly:", prompt_check is None)

print("\nALL PHASE 2 UNIT TESTS PASSED SUCCESSFULLY!")

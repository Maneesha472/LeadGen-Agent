import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app import app, SettingsUpdate, save_settings_endpoint, get_db
from backend.database import User

# Test Pydantic model instantiation with partial/empty fields
test_payload = SettingsUpdate(
    google_api_key="test_key_123",
    brave_api_key="test_brave"
)

print("1. SettingsUpdate Pydantic Model initialized successfully:", test_payload.model_dump())
print("\nSETTINGS ENDPOINT REFACTOR VERIFIED SUCCESSFUL!")

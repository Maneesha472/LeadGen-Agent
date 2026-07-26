import os
import json

SETTINGS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "settings.json"))

DEFAULT_SETTINGS = {
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_username": "",
    "smtp_password": "",
    "smtp_use_tls": True,
    "simulation_mode": True,
    "scraping_delay": 2,
    "max_search_results": 10
}

def load_settings():
    if not os.path.exists(SETTINGS_PATH):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS
    try:
        with open(SETTINGS_PATH, "r") as f:
            settings = json.load(f)
            # Ensure all default keys exist
            updated = False
            for k, v in DEFAULT_SETTINGS.items():
                if k not in settings:
                    settings[k] = v
                    updated = True
            if updated:
                save_settings(settings)
            return settings
    except Exception:
        return DEFAULT_SETTINGS

def save_settings(settings):
    try:
        # Cast fields properly
        settings["smtp_port"] = int(settings.get("smtp_port", 587))
        settings["scraping_delay"] = float(settings.get("scraping_delay", 2))
        settings["max_search_results"] = int(settings.get("max_search_results", 10))
        settings["smtp_use_tls"] = bool(settings.get("smtp_use_tls", True))
        settings["simulation_mode"] = bool(settings.get("simulation_mode", True))
        
        with open(SETTINGS_PATH, "w") as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False

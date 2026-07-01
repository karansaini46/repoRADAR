import json
import os
import logging
from pathlib import Path
from pydantic import BaseModel

SETTINGS_FILE = Path("/app/autoscan/settings.json")
# For local testing if /app is not available
if not SETTINGS_FILE.parent.exists():
    SETTINGS_FILE = Path("autoscan/settings.json")

class SystemSettings(BaseModel):
    auto_mode: bool = True
    scraping_interval_hours: int = 24

def get_settings() -> SystemSettings:
    if not SETTINGS_FILE.exists():
        return SystemSettings()
    
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
            return SystemSettings(**data)
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to read settings: {e}")
        return SystemSettings()

def save_settings(settings: SystemSettings):
    try:
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SETTINGS_FILE, "w") as f:
            json.dump(settings.model_dump(), f, indent=2)
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to save settings: {e}")

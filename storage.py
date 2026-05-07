"""
Storage module — saves leads to leads_data.json.
All scraped leads start as New with no pre-filled history.
"""

import json
import os

LEADS_FILE = "leads_data.json"


def load_leads():
    """Load leads from file. Returns empty list if no file exists yet."""
    if os.path.exists(LEADS_FILE):
        try:
            with open(LEADS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def save_leads(leads):
    try:
        with open(LEADS_FILE, "w") as f:
            json.dump(leads, f, indent=2)
    except Exception as e:
        print(f"Warning: could not save leads: {e}")

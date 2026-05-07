"""
Storage module — saves leads to leads_data.json.
On Streamlit Cloud this file persists as long as the app is running.
For permanent persistence across restarts, this can later be swapped
for Google Sheets or Supabase (free tier) in Phase 2.
"""

import json
import os

LEADS_FILE = "leads_data.json"

SAMPLE_LEADS = [
    {
        "id": 1001,
        "name": "Pari Global Agri Exports Pvt Ltd",
        "iec": "0513078432",
        "city": "Ludhiana, Punjab",
        "phone": "+91 98150 34221",
        "email": "exports@pariglobal.in",
        "website": "https://pariglobal.in",
        "countries": ["UAE", "Saudi Arabia", "UK"],
        "products": ["Basmati Rice", "Wheat"],
        "shipments": "62 shipments/yr",
        "score": "Hot",
        "status": "New",
        "notes": "Large volume exporter. Has contacts in Dubai wholesale market.",
        "source": "https://www.indiamart.com/pariglobal",
        "added": "2025-04-10",
    },
    {
        "id": 1002,
        "name": "Shree Ram Food Exports",
        "iec": "0515023998",
        "city": "Karnal, Haryana",
        "phone": "+91 94160 55443",
        "email": "info@sreeramfoods.com",
        "website": "https://sreeramfoods.com",
        "countries": ["USA", "Canada", "Australia"],
        "products": ["Non-Basmati Rice", "Chickpeas"],
        "shipments": "38 shipments/yr",
        "score": "Hot",
        "status": "Contacted",
        "notes": "Reached out on April 12. Waiting for response.",
        "source": "https://zauba.com/exporter-shree-ram",
        "added": "2025-04-09",
    },
    {
        "id": 1003,
        "name": "Bharat Grains International",
        "iec": "0512986541",
        "city": "Indore, Madhya Pradesh",
        "phone": "+91 73898 12345",
        "email": "contact@bharatgrains.in",
        "website": "",
        "countries": ["China", "UAE"],
        "products": ["Soybean", "Maize", "Lentils"],
        "shipments": "24 shipments/yr",
        "score": "Warm",
        "status": "Follow-up",
        "notes": "Interested but wants pricing first. Follow up by 20th.",
        "source": "https://volza.com/bharat-grains",
        "added": "2025-04-08",
    },
    {
        "id": 1004,
        "name": "Golden Harvest Exports",
        "iec": "0316542187",
        "city": "Rajkot, Gujarat",
        "phone": "+91 98250 76543",
        "email": "golden@harvestexports.com",
        "website": "https://goldenharvestexports.com",
        "countries": ["Germany", "UK", "USA"],
        "products": ["Groundnut", "Wheat"],
        "shipments": "19 shipments/yr",
        "score": "Warm",
        "status": "Replied",
        "notes": "Interested in bulk wheat. Scheduled call for 25th April.",
        "source": "https://exportersindia.com/golden-harvest",
        "added": "2025-04-07",
    },
    {
        "id": 1005,
        "name": "Punjab Agri Links",
        "iec": "0315987123",
        "city": "Amritsar, Punjab",
        "phone": "+91 98720 44321",
        "email": "sales@punjabagrilinks.com",
        "website": "https://punjabagrilinks.com",
        "countries": ["USA", "Canada", "UK", "UAE"],
        "products": ["Basmati Rice", "Wheat", "Chickpeas"],
        "shipments": "55 shipments/yr",
        "score": "Hot",
        "status": "Converted",
        "notes": "Signed 3-month trial for 200MT wheat supply.",
        "source": "https://zauba.com/punjab-agri-links",
        "added": "2025-04-05",
    },
]


def load_leads():
    if os.path.exists(LEADS_FILE):
        try:
            with open(LEADS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    save_leads(SAMPLE_LEADS)
    return SAMPLE_LEADS


def save_leads(leads):
    try:
        with open(LEADS_FILE, "w") as f:
            json.dump(leads, f, indent=2)
    except Exception as e:
        print(f"Warning: could not save leads: {e}")

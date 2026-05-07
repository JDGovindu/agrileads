"""
Scraper using Google Custom Search API (free tier: 100 queries/day).
Searches for IEC food grain exporters across India and extracts
contact details from search snippets and result pages.
"""

import re
import time
import random
import hashlib
import requests
from datetime import datetime
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

PRODUCT_KEYWORDS = [
    "rice", "wheat", "pulses", "maize", "basmati", "chickpea",
    "lentil", "soybean", "groundnut", "millet", "grain", "cereal",
    "food grain", "agri", "dal", "paddy", "corn", "oilseed",
]


def _make_id(name):
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


def _extract_products(text):
    text_lower = text.lower()
    found = []
    if "basmati" in text_lower:
        found.append("Basmati Rice")
    elif "rice" in text_lower or "paddy" in text_lower:
        found.append("Non-Basmati Rice")
    if "wheat" in text_lower:        found.append("Wheat")
    if "chickpea" in text_lower or "chana" in text_lower:  found.append("Chickpeas")
    if "lentil" in text_lower or "masoor" in text_lower or "dal" in text_lower:
        found.append("Lentils")
    if "maize" in text_lower or "corn" in text_lower:      found.append("Maize")
    if "soybean" in text_lower or "soya" in text_lower:    found.append("Soybean")
    if "groundnut" in text_lower or "peanut" in text_lower: found.append("Groundnut")
    if "millet" in text_lower or "bajra" in text_lower:    found.append("Millet")
    if "oilseed" in text_lower:      found.append("Oilseeds")
    if not found and any(k in text_lower for k in ["grain", "cereal", "agri", "export"]):
        found.append("Food Grains")
    return list(dict.fromkeys(found)) or ["Food Grains"]


def _extract_countries(text, destinations):
    found = []
    country_aliases = {
        "UAE":         ["uae", "dubai", "abu dhabi", "united arab emirates", "sharjah"],
        "Saudi Arabia":["saudi", "riyadh", "jeddah", "ksa"],
        "Kuwait":      ["kuwait"],
        "USA":         ["usa", "united states", "america", "us market"],
        "Canada":      ["canada", "toronto", "vancouver"],
        "UK":          ["uk", "united kingdom", "britain", "england", "london"],
        "Germany":     ["germany", "german", "berlin"],
        "Netherlands": ["netherlands", "holland", "amsterdam"],
        "Australia":   ["australia", "sydney", "melbourne"],
        "China":       ["china", "beijing", "shanghai", "chinese market"],
    }
    text_lower = text.lower()
    for dest in destinations:
        aliases = country_aliases.get(dest, [dest.lower()])
        if any(alias in text_lower for alias in aliases):
            found.append(dest)
    return found


def _extract_phone(text):
    patterns = [
        r'\+91[\s\-]?[6-9]\d{9}',
        r'\+91[\s\-]?\d{10}',
        r'(?<!\d)[6-9]\d{9}(?!\d)',
        r'\d{4}[\s\-]\d{6}',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            phone = m.group(0).strip()
            if not phone.startswith("+91"):
                phone = "+91 " + phone
            return phone
    return ""


def _extract_email(text):
    m = re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
    if m:
        email = m.group(0)
        if not any(x in email.lower() for x in ["example", "test@", "noreply"]):
            return email
    return ""


def _extract_iec(text):
    patterns = [
        r'IEC[:\s#]*(\d{10})',
        r'IEC[:\s#]*(\d{4}\s\d{6})',
        r'\bIEC\b[^\d]*(\d{10})',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return re.sub(r'\s', '', m.group(1))
    return ""


def _extract_city(text):
    cities = [
        "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata",
        "Ludhiana", "Amritsar", "Jalandhar", "Karnal", "Hisar", "Rohtak",
        "Indore", "Bhopal", "Nagpur", "Pune", "Surat", "Ahmedabad", "Rajkot",
        "Jaipur", "Jodhpur", "Kanpur", "Lucknow", "Varanasi", "Agra",
        "Patna", "Ranchi", "Bhubaneswar", "Visakhapatnam", "Guntur",
        "Vijayawada", "Coimbatore", "Madurai", "Kochi", "Chandigarh",
    ]
    states = {
        "Punjab": "Punjab", "Haryana": "Haryana",
        "Uttar Pradesh": "Uttar Pradesh", "UP": "Uttar Pradesh",
        "Madhya Pradesh": "Madhya Pradesh", "MP": "Madhya Pradesh",
        "Gujarat": "Gujarat", "Rajasthan": "Rajasthan",
        "Maharashtra": "Maharashtra", "Tamil Nadu": "Tamil Nadu",
        "Karnataka": "Karnataka", "Telangana": "Telangana",
        "Andhra Pradesh": "Andhra Pradesh", "West Bengal": "West Bengal",
        "Bihar": "Bihar", "Odisha": "Odisha", "Kerala": "Kerala",
    }
    for city in cities:
        if city.lower() in text.lower():
            for state_key, state_val in states.items():
                if state_key.lower() in text.lower():
                    return f"{city}, {state_val}"
            return city
    for state_key, state_val in states.items():
        if state_key.lower() in text.lower():
            return state_val
    return ""


def _score_lead(lead):
    score = 0
    if lead.get("phone"):                    score += 2
    if lead.get("email"):                    score += 2
    if lead.get("iec"):                      score += 3
    if lead.get("website"):                  score += 1
    if len(lead.get("countries", [])) >= 2:  score += 2
    if len(lead.get("products", [])) >= 2:   score += 1
    name_lower = lead.get("name", "").lower()
    if "pvt" in name_lower or "ltd" in name_lower or "llp" in name_lower:
        score += 1
    if score >= 7:   return "Hot"
    elif score >= 4: return "Warm"
    else:            return "Cold"


def _fetch_page_details(url):
    """Fetch extra contact details from the lead's own website."""
    if not url or len(url) > 200:
        return {}
    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        if r.status_code != 200:
            return {}
        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)[:3000]
        return {
            "phone": _extract_phone(text),
            "email": _extract_email(text),
            "iec":   _extract_iec(text),
            "city":  _extract_city(text),
        }
    except Exception:
        return {}


def google_custom_search(query, api_key, cx, num=10):
    """Call Google Custom Search API."""
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": api_key, "cx": cx, "q": query, "num": min(num, 10)}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if "error" in data:
            raise ValueError(f"Google API error: {data['error'].get('message','Unknown')}")
        return data.get("items", [])
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Request failed: {str(e)}")


def build_search_queries(keywords, destinations):
    """Build targeted search queries for IEC agriculture exporters."""
    queries = []
    dest_str = " OR ".join(destinations[:4]) if destinations else "export"
    for kw in keywords:
        queries += [
            f'"{kw}" IEC number India exporter contact email',
            f'"{kw}" exporter India {dest_str} contact phone',
            f'site:indiamart.com "{kw}" exporter',
            f'site:exportersindia.com "{kw}" exporter India',
            f'site:tradeindia.com "{kw}" exporter',
            f'"{kw}" exporter India IEC "pvt ltd" contact',
        ]
    seen, unique = set(), []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)
    return unique


def parse_result_to_lead(item, destinations):
    """Convert a Google search result into a lead dict."""
    title   = item.get("title", "")
    snippet = item.get("snippet", "")
    link    = item.get("link", "")
    full_text = f"{title} {snippet}"

    # Clean company name from title
    name = title
    for sep in ["|", "-", "–", ":", "·", "—"]:
        name = name.split(sep)[0].strip()
    name = re.sub(r'\s+', ' ', name).strip()[:80]

    if not name or len(name) < 5:
        return None
    if not any(kw in full_text.lower() for kw in PRODUCT_KEYWORDS):
        return None
    exporter_signals = ["export", "pvt", "ltd", "llp", "trading", "agro",
                        "foods", "grains", "international", "enterprises", "impex"]
    if not any(sig in full_text.lower() for sig in exporter_signals):
        return None

    lead = {
        "id":        _make_id(name + link),
        "name":      name,
        "iec":       _extract_iec(full_text),
        "city":      _extract_city(full_text),
        "phone":     _extract_phone(full_text),
        "email":     _extract_email(full_text),
        "website":   link,
        "countries": _extract_countries(full_text, destinations),
        "products":  _extract_products(full_text),
        "shipments": "",
        "score":     "Warm",
        "status":    "New",
        "notes":     f"Source snippet: {snippet[:150]}",
        "source":    link,
        "added":     datetime.now().strftime("%Y-%m-%d"),
    }
    lead["score"] = _score_lead(lead)
    return lead


def scrape_leads(keywords, destinations, max_per_source, progress=None,
                 api_key="", cx=""):
    """Main entry point — uses Google Custom Search API."""
    if not api_key or not cx:
        raise ValueError("Missing API credentials. Add your Google API Key and Search Engine ID in the sidebar.")

    queries = build_search_queries(keywords, destinations)
    max_queries = min(len(queries), max(4, max_per_source // 2))
    queries = queries[:max_queries]

    all_leads = []

    for i, query in enumerate(queries):
        if progress:
            progress.progress((i + 1) / (len(queries) + 1),
                              text=f"Searching Google: {query[:55]}...")
        try:
            items = google_custom_search(query, api_key, cx, num=10)
            for item in items:
                lead = parse_result_to_lead(item, destinations)
                if lead:
                    # Enrich from actual website if it's not a directory
                    url = lead.get("website", "")
                    skip_fetch = any(d in url for d in [
                        "indiamart.com", "tradeindia.com",
                        "exportersindia.com", "justdial.com",
                        "google.com", "youtube.com",
                    ])
                    if url and not skip_fetch:
                        details = _fetch_page_details(url)
                        if details.get("phone") and not lead["phone"]:
                            lead["phone"] = details["phone"]
                        if details.get("email") and not lead["email"]:
                            lead["email"] = details["email"]
                        if details.get("iec") and not lead["iec"]:
                            lead["iec"] = details["iec"]
                        if details.get("city") and not lead["city"]:
                            lead["city"] = details["city"]
                        lead["score"] = _score_lead(lead)
                    all_leads.append(lead)
        except ValueError:
            raise
        except Exception:
            pass
        time.sleep(random.uniform(0.3, 0.8))

    if progress:
        progress.progress(1.0, text="Done!")

    # Deduplicate by name
    seen_names, unique = set(), []
    for l in all_leads:
        key = l["name"].lower().strip()
        if key not in seen_names and len(key) > 4:
            seen_names.add(key)
            unique.append(l)
    return unique

"""
Scraper for IEC agriculture exporters.
Uses requests + BeautifulSoup to scrape:
  1. Google Search results
  2. IndiaMart listings
  3. TradeIndia listings
  4. ExportersIndia listings
No paid API required.
"""

import re
import time
import random
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

PRODUCT_KEYWORDS = [
    "rice", "wheat", "pulses", "maize", "basmati", "chickpea",
    "lentil", "soybean", "groundnut", "millet", "grain", "cereal",
    "food grain", "agri"
]

PRODUCT_MAP = {
    "basmati": "Basmati Rice",
    "rice": "Non-Basmati Rice",
    "wheat": "Wheat",
    "chickpea": "Chickpeas",
    "lentil": "Lentils",
    "maize": "Maize",
    "soybean": "Soybean",
    "groundnut": "Groundnut",
    "millet": "Millet",
    "grain": "Food Grains",
    "pulse": "Pulses",
}


def _get(url, timeout=10):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception:
        return None


def _make_id(name):
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


def _score_lead(lead):
    score = 0
    if lead.get("phone"):     score += 2
    if lead.get("email"):     score += 2
    if lead.get("iec"):       score += 3
    if lead.get("website"):   score += 1
    if len(lead.get("countries", [])) >= 3: score += 2
    if lead.get("shipments"): score += 1
    if score >= 7:   return "Hot"
    elif score >= 4: return "Warm"
    else:            return "Cold"


def _extract_products(text):
    text_lower = text.lower()
    found = []
    if "basmati" in text_lower:
        found.append("Basmati Rice")
    elif "rice" in text_lower:
        found.append("Non-Basmati Rice")
    if "wheat" in text_lower:   found.append("Wheat")
    if "chickpea" in text_lower or "chana" in text_lower: found.append("Chickpeas")
    if "lentil" in text_lower or "masoor" in text_lower:  found.append("Lentils")
    if "maize" in text_lower or "corn" in text_lower:     found.append("Maize")
    if "soybean" in text_lower or "soya" in text_lower:   found.append("Soybean")
    if "groundnut" in text_lower or "peanut" in text_lower: found.append("Groundnut")
    if "millet" in text_lower or "bajra" in text_lower:   found.append("Millet")
    if "pulse" in text_lower or "dal" in text_lower:      found.append("Pulses")
    return found or ["Food Grains"]


def _extract_countries(text, destinations):
    found = []
    for d in destinations:
        if d.lower() in text.lower():
            found.append(d)
    return found


def _extract_phone(text):
    patterns = [
        r'\+91[\s\-]?[6-9]\d{9}',
        r'\+91[\s\-]?\d{10}',
        r'[6-9]\d{9}',
        r'\d{4}[\s\-]\d{6}',
        r'\(\d{3,5}\)[\s\-]?\d{5,8}',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(0).strip()
    return ""


def _extract_email(text):
    m = re.search(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text)
    return m.group(0) if m else ""


def _extract_iec(text):
    # IEC is a 10-digit number, often prefixed with IEC
    m = re.search(r'(?:IEC[:\s#]*)?(\d{10})', text, re.IGNORECASE)
    return m.group(1) if m else ""


# ── Google Scraper ─────────────────────────────────────────────────────────────
def scrape_google(keyword, destinations, max_results):
    leads = []
    dest_str = " ".join(destinations[:3])
    queries = [
        f'"{keyword}" IEC exporter India site:indiamart.com',
        f'"{keyword}" exporter India IEC number {dest_str}',
        f'site:exportersindia.com "{keyword}" exporter',
        f'site:tradeindia.com "{keyword}" exporter India',
    ]

    for query in queries[:2]:
        url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num=15"
        html = _get(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        results = soup.select("div.g")

        for r in results[:max_results]:
            title_el = r.select_one("h3")
            link_el  = r.select_one("a")
            snippet_el = r.select_one("div.VwiC3b, span.aCOpRe")
            if not title_el:
                continue

            title   = title_el.get_text()
            snippet = snippet_el.get_text() if snippet_el else ""
            link    = link_el["href"] if link_el and link_el.get("href","").startswith("http") else ""
            full_text = title + " " + snippet

            if not any(kw in full_text.lower() for kw in PRODUCT_KEYWORDS):
                continue

            lead = {
                "id": _make_id(title),
                "name": title.split("|")[0].split("-")[0].strip()[:80],
                "iec": _extract_iec(full_text),
                "city": "",
                "phone": _extract_phone(full_text),
                "email": _extract_email(full_text),
                "website": link,
                "countries": _extract_countries(full_text, destinations),
                "products": _extract_products(full_text),
                "shipments": "",
                "score": "Warm",
                "status": "New",
                "notes": "",
                "source": link,
                "added": datetime.now().strftime("%Y-%m-%d"),
            }
            lead["score"] = _score_lead(lead)
            if lead["name"] and len(lead["name"]) > 4:
                leads.append(lead)

        time.sleep(random.uniform(1.5, 3.0))

    return leads


# ── IndiaMart Scraper ──────────────────────────────────────────────────────────
def scrape_indiamart(keyword, destinations, max_results):
    leads = []
    slug = keyword.lower().replace(" ", "-")
    urls = [
        f"https://dir.indiamart.com/search.mp?ss={requests.utils.quote(keyword)}&priceRange=0-0&cat=Grains%2C+Cereals+%26+Flour",
        f"https://dir.indiamart.com/impcat/{slug}-exporters.html",
    ]

    for url in urls[:1]:
        html = _get(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")

        # IndiaMart company listing cards
        cards = soup.select("div.organic-card, div.companydetails, div.prdcard")
        if not cards:
            cards = soup.select("div[class*='company'], div[class*='supplier']")

        for card in cards[:max_results]:
            text = card.get_text(" ", strip=True)
            name_el = card.select_one("h2, h3, .company-name, .lcname")
            name = name_el.get_text(strip=True) if name_el else ""
            if not name or len(name) < 5:
                continue

            city_el = card.select_one(".lcadr, .city, [class*='address']")
            city = city_el.get_text(strip=True) if city_el else ""

            link_el = card.select_one("a[href*='indiamart.com']")
            link = link_el["href"] if link_el else ""

            phone = _extract_phone(text)
            email = _extract_email(text)

            lead = {
                "id": _make_id(name),
                "name": name[:80],
                "iec": _extract_iec(text),
                "city": city,
                "phone": phone,
                "email": email,
                "website": link,
                "countries": _extract_countries(text, destinations),
                "products": _extract_products(keyword + " " + text),
                "shipments": "",
                "score": "Warm",
                "status": "New",
                "notes": "",
                "source": link or url,
                "added": datetime.now().strftime("%Y-%m-%d"),
            }
            lead["score"] = _score_lead(lead)
            leads.append(lead)

        time.sleep(random.uniform(1.0, 2.5))

    return leads


# ── ExportersIndia Scraper ─────────────────────────────────────────────────────
def scrape_exportersindia(keyword, destinations, max_results):
    leads = []
    slug  = keyword.lower().replace(" ", "-")
    url   = f"https://www.exportersindia.com/search/{slug}-exporter.htm"
    html  = _get(url)
    if not html:
        return leads

    soup  = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.sup_listing, div.comp-listing, li.list-item")

    for card in cards[:max_results]:
        text = card.get_text(" ", strip=True)
        name_el = card.select_one("h2, h3, strong, .comp-name")
        name = name_el.get_text(strip=True) if name_el else ""
        if not name or len(name) < 5:
            continue

        city_el = card.select_one(".city, .location, [class*='addr']")
        city = city_el.get_text(strip=True) if city_el else ""

        link_el = card.select_one("a")
        link = link_el["href"] if link_el and link_el.get("href","").startswith("http") else ""

        lead = {
            "id": _make_id(name),
            "name": name[:80],
            "iec": _extract_iec(text),
            "city": city,
            "phone": _extract_phone(text),
            "email": _extract_email(text),
            "website": link,
            "countries": _extract_countries(text, destinations),
            "products": _extract_products(keyword + " " + text),
            "shipments": "",
            "score": "Warm",
            "status": "New",
            "notes": "",
            "source": link or url,
            "added": datetime.now().strftime("%Y-%m-%d"),
        }
        lead["score"] = _score_lead(lead)
        leads.append(lead)

    time.sleep(random.uniform(1.0, 2.0))
    return leads


# ── TradeIndia Scraper ─────────────────────────────────────────────────────────
def scrape_tradeindia(keyword, destinations, max_results):
    leads = []
    slug  = keyword.lower().replace(" ", "+")
    url   = f"https://www.tradeindia.com/Exporters/{slug.replace('+','-')}.html"
    html  = _get(url)
    if not html:
        return leads

    soup  = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.company-info, div.product-listing, li.companyList")

    for card in cards[:max_results]:
        text    = card.get_text(" ", strip=True)
        name_el = card.select_one("h2, h3, .comp-name, strong")
        name    = name_el.get_text(strip=True) if name_el else ""
        if not name or len(name) < 5:
            continue

        city_el = card.select_one(".city, .location")
        city    = city_el.get_text(strip=True) if city_el else ""

        link_el = card.select_one("a[href*='tradeindia']")
        link    = link_el["href"] if link_el and link_el.get("href","").startswith("http") else ""

        lead = {
            "id": _make_id(name),
            "name": name[:80],
            "iec": _extract_iec(text),
            "city": city,
            "phone": _extract_phone(text),
            "email": _extract_email(text),
            "website": link,
            "countries": _extract_countries(text, destinations),
            "products": _extract_products(keyword + " " + text),
            "shipments": "",
            "score": "Warm",
            "status": "New",
            "notes": "",
            "source": link or url,
            "added": datetime.now().strftime("%Y-%m-%d"),
        }
        lead["score"] = _score_lead(lead)
        leads.append(lead)

    time.sleep(random.uniform(1.0, 2.0))
    return leads


# ── Master scrape function ─────────────────────────────────────────────────────
def scrape_leads(keywords, destinations, max_per_source, progress=None):
    all_leads = []
    sources = [
        ("IndiaMart",       scrape_indiamart),
        ("ExportersIndia",  scrape_exportersindia),
        ("TradeIndia",      scrape_tradeindia),
        ("Google",          scrape_google),
    ]
    total_steps = len(keywords) * len(sources)
    step = 0

    for kw in keywords:
        for source_name, fn in sources:
            step += 1
            pct  = step / total_steps
            if progress:
                progress.progress(pct, text=f"Scraping {source_name} for '{kw}'...")
            try:
                results = fn(kw, destinations, max_per_source)
                all_leads.extend(results)
            except Exception as e:
                pass  # silently skip failed sources
            time.sleep(random.uniform(0.5, 1.5))

    # Deduplicate within this batch
    seen_names = set()
    unique = []
    for l in all_leads:
        key = l["name"].lower().strip()
        if key not in seen_names and len(key) > 4:
            seen_names.add(key)
            unique.append(l)

    return unique

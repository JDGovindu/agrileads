import streamlit as st
import time
from datetime import datetime
from scraper import scrape_leads
from storage import load_leads, save_leads

st.set_page_config(
    page_title="AgriLeads — IEC Exporter Pipeline",
    page_icon="🌾",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=Syne:wght@800&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

/* ── header ── */
.agri-logo { font-family:'Syne',sans-serif; font-size:30px; font-weight:800;
             letter-spacing:-1px; margin-bottom:2px; }
.agri-logo span { color:#3d9e2e; }
.agri-sub { color:#888; font-size:13px; margin-bottom:24px; }

/* ── stat cards ── */
.stat-row { display:flex; gap:12px; margin-bottom:20px; flex-wrap:wrap; }
.stat-card { background:#f7fdf5; border:1px solid #d4edce; border-radius:10px;
             padding:14px 20px; min-width:130px; flex:1; }
.stat-n { font-size:26px; font-weight:700; color:#2d7a20; line-height:1; }
.stat-l { font-size:11px; color:#888; margin-top:3px; }

/* ── lead card ── */
.lead-card { background:#fff; border:1px solid #e8f0e5; border-radius:10px;
             padding:16px 18px; margin-bottom:8px; }
.lead-name { font-size:15px; font-weight:600; color:#1a1a1a; margin-bottom:4px; }
.lead-iec  { font-size:11px; color:#aaa; font-family:monospace; margin-bottom:8px; }

/* ── tags ── */
.tag { display:inline-block; font-size:11px; font-weight:600;
       padding:2px 8px; border-radius:6px; margin-right:4px; margin-bottom:2px; }
.tag-hot      { background:#fff8e6; color:#b07a00; border:1px solid #fde68a; }
.tag-warm     { background:#f0fbec; color:#276f1c; border:1px solid #bbf0a8; }
.tag-cold     { background:#eff6ff; color:#1d5fa8; border:1px solid #bfdbfe; }
.tag-new      { background:#f5f3ff; color:#5b21b6; border:1px solid #ddd6fe; }
.tag-contacted{ background:#fff8e6; color:#b07a00; border:1px solid #fde68a; }
.tag-followup { background:#f0fbec; color:#276f1c; border:1px solid #bbf0a8; }
.tag-replied  { background:#eff6ff; color:#1d5fa8; border:1px solid #bfdbfe; }
.tag-converted{ background:#ecfdf5; color:#065f46; border:1px solid #a7f3d0; }
.tag-dead     { background:#f9f9f9; color:#888;    border:1px solid #ddd; }
.tag-country  { background:#eff6ff; color:#1e40af; }
.tag-product  { background:#f0fdf4; color:#166534; }

/* ── pipeline ── */
.pip-col { background:#f9fdf8; border:1px solid #dff0d8; border-radius:10px;
           padding:10px; min-height:120px; }
.pip-col-head { font-size:12px; font-weight:700; margin-bottom:8px;
                padding-bottom:6px; border-bottom:2px solid currentColor; }
.pip-mini { background:#fff; border:1px solid #e8f0e5; border-radius:7px;
            padding:10px; margin-bottom:6px; font-size:12px; }
.pip-mini-name { font-weight:600; color:#1a1a1a; margin-bottom:2px; }
.pip-mini-sub  { color:#888; font-size:11px; }

/* ── scrape button ── */
div[data-testid="stButton"] > button[kind="primary"] {
    background:#2d7a20 !important; color:#fff !important;
    border:none !important; font-weight:600 !important;
    font-size:15px !important; padding:10px !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background:#1f5a16 !important;
}

/* ── expander ── */
details summary { font-weight:600 !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "leads" not in st.session_state:
    st.session_state.leads = load_leads()
if "last_scrape" not in st.session_state:
    st.session_state.last_scrape = None

leads = st.session_state.leads

STATUSES = ["New", "Contacted", "Follow-up", "Replied", "Converted", "Dead"]
STATUS_COLORS = {
    "New": "#7c3aed", "Contacted": "#b45309", "Follow-up": "#166534",
    "Replied": "#1d4ed8", "Converted": "#065f46", "Dead": "#6b7280",
}
SCORE_COLORS = {"Hot": "#b45309", "Warm": "#166534", "Cold": "#1d4ed8"}
SCORE_TAGS   = {"Hot": "tag-hot",  "Warm": "tag-warm",  "Cold": "tag-cold"}
STATUS_TAGS  = {
    "New": "tag-new", "Contacted": "tag-contacted", "Follow-up": "tag-followup",
    "Replied": "tag-replied", "Converted": "tag-converted", "Dead": "tag-dead",
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🌾 AgriLeads")
    st.markdown("IEC Agriculture Exporter Pipeline")
    st.divider()

    st.markdown("### 🔍 Scrape New Leads")
    keywords = st.multiselect(
        "Product keywords",
        ["food grain exporter", "rice exporter", "wheat exporter",
         "pulses exporter", "maize exporter", "basmati exporter",
         "chickpea exporter", "lentil exporter", "soybean exporter"],
        default=["food grain exporter", "rice exporter", "wheat exporter"],
    )
    destinations = st.multiselect(
        "Export destinations",
        ["UAE", "Saudi Arabia", "Kuwait", "USA", "Canada",
         "UK", "Germany", "Netherlands", "Australia", "China"],
        default=["UAE", "USA", "UK", "Germany", "Australia"],
    )
    max_results = st.slider("Max results per source", 5, 30, 10)

    scrape_clicked = st.button("▶  Scrape Leads Now", type="primary", use_container_width=True)
    if st.session_state.last_scrape:
        st.caption(f"Last scraped: {st.session_state.last_scrape}")

    st.divider()
    st.markdown("### ⚙️ Filters")
    f_search  = st.text_input("Search company / IEC / city", "")
    f_country = st.selectbox("Export country", ["All"] + ["UAE","Saudi Arabia","Kuwait","USA","Canada","UK","Germany","Netherlands","Australia","China"])
    f_product = st.selectbox("Product", ["All","Basmati Rice","Non-Basmati Rice","Wheat","Chickpeas","Lentils","Maize","Soybean","Groundnut"])
    f_status  = st.selectbox("Status", ["All"] + STATUSES)
    f_score   = st.selectbox("Lead score", ["All","Hot","Warm","Cold"])

    st.divider()
    if st.button("🗑  Clear all leads", use_container_width=True):
        st.session_state.leads = []
        save_leads([])
        st.rerun()

# ── Scraping ──────────────────────────────────────────────────────────────────
if scrape_clicked:
    if not keywords:
        st.sidebar.warning("Pick at least one product keyword.")
    elif not destinations:
        st.sidebar.warning("Pick at least one destination.")
    else:
        with st.spinner("🔍 Scraping IndiaMart, ExportersIndia, TradeIndia & Google..."):
            prog = st.progress(0, text="Starting scrape...")
            new_leads = scrape_leads(keywords, destinations, max_results, prog)

            existing_names = {l["name"].lower() for l in st.session_state.leads}
            existing_iecs  = {l["iec"] for l in st.session_state.leads if l["iec"]}
            added = 0
            for lead in new_leads:
                if (lead["name"].lower() not in existing_names
                        and lead["iec"] not in existing_iecs):
                    st.session_state.leads.append(lead)
                    existing_names.add(lead["name"].lower())
                    if lead["iec"]:
                        existing_iecs.add(lead["iec"])
                    added += 1

            save_leads(st.session_state.leads)
            st.session_state.last_scrape = datetime.now().strftime("%d %b %Y, %I:%M %p")
            leads = st.session_state.leads
            prog.progress(1.0, text="Done!")
            st.success(f"✅ Scraped {len(new_leads)} results — {added} new leads added!")

# ── Filter ────────────────────────────────────────────────────────────────────
def apply_filters(leads):
    out = leads
    if f_search:
        q = f_search.lower()
        out = [l for l in out if q in l["name"].lower()
               or q in l.get("iec", "")
               or q in l.get("city", "").lower()]
    if f_country != "All":
        out = [l for l in out if f_country in l.get("countries", [])]
    if f_product != "All":
        out = [l for l in out if f_product in l.get("products", [])]
    if f_status != "All":
        out = [l for l in out if l.get("status") == f_status]
    if f_score != "All":
        out = [l for l in out if l.get("score") == f_score]
    return out

filtered = apply_filters(leads)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown('<div class="agri-logo">Agri<span>Leads</span></div>', unsafe_allow_html=True)
st.markdown('<div class="agri-sub">IEC Agriculture Exporter Lead Pipeline · India → World</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Leads",    len(leads))
c2.metric("Hot Leads 🔥",   sum(1 for l in leads if l.get("score") == "Hot"))
c3.metric("In Progress",    sum(1 for l in leads if l.get("status") not in ["New","Dead"]))
c4.metric("Converted ✅",   sum(1 for l in leads if l.get("status") == "Converted"))

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📋  Lead List", "🗂  Pipeline View", "➕  Add Lead Manually"])

# ─── TAB 1: Lead List ─────────────────────────────────────────────────────────
with tab1:
    st.caption(f"{len(filtered)} leads shown")

    if not filtered:
        st.info("No leads match your filters. Try scraping or adjust the sidebar filters.")
    else:
        for lead in filtered:
            score_tag  = SCORE_TAGS.get(lead.get("score","Warm"), "tag-warm")
            status_tag = STATUS_TAGS.get(lead.get("status","New"), "tag-new")
            ctags = " ".join(
                f'<span class="tag tag-country">{c}</span>'
                for c in lead.get("countries",[])[:3]
            )
            ptags = " ".join(
                f'<span class="tag tag-product">{p}</span>'
                for p in lead.get("products",[])[:2]
            )

            label = f"**{lead['name']}**  ·  {lead.get('city','').split(',')[0]}"
            with st.expander(label, expanded=False):
                col_a, col_b = st.columns([2, 1])

                with col_a:
                    st.markdown(f"**IEC:** `{lead.get('iec','—')}`")
                    st.markdown(f"📍 **City:** {lead.get('city','—')}")
                    st.markdown(f"📞 **Phone:** {lead.get('phone','—')}")
                    st.markdown(f"✉️ **Email:** {lead.get('email','—')}")
                    if lead.get("website"):
                        st.markdown(f"🌐 **Website:** [{lead['website']}]({lead['website']})")
                    st.markdown(f"📦 **Products:** {', '.join(lead.get('products',[]))}")
                    st.markdown(f"🌍 **Exports to:** {', '.join(lead.get('countries',[]))}")
                    st.markdown(f"🚢 **Shipments:** {lead.get('shipments','—')}")
                    if lead.get("source"):
                        st.markdown(f"🔗 **Source:** [{lead['source']}]({lead['source']})")

                with col_b:
                    sc = lead.get("score","Warm")
                    st.markdown(
                        f'<span class="tag {score_tag}">{sc} Lead</span>&nbsp;'
                        f'<span class="tag {status_tag}">{lead.get("status","New")}</span>',
                        unsafe_allow_html=True,
                    )
                    st.write("")

                    new_status = st.selectbox(
                        "Update status",
                        STATUSES,
                        index=STATUSES.index(lead.get("status","New")),
                        key=f"status_{lead['id']}",
                    )
                    if new_status != lead.get("status"):
                        lead["status"] = new_status
                        save_leads(st.session_state.leads)
                        st.rerun()

                    new_score = st.selectbox(
                        "Lead score",
                        ["Hot","Warm","Cold"],
                        index=["Hot","Warm","Cold"].index(lead.get("score","Warm")),
                        key=f"score_{lead['id']}",
                    )
                    if new_score != lead.get("score"):
                        lead["score"] = new_score
                        save_leads(st.session_state.leads)
                        st.rerun()

                notes_val = st.text_area(
                    "📝 Notes",
                    lead.get("notes",""),
                    key=f"notes_{lead['id']}",
                    height=80,
                )
                if st.button("💾 Save Notes", key=f"save_{lead['id']}"):
                    lead["notes"] = notes_val
                    save_leads(st.session_state.leads)
                    st.success("Saved!")

# ─── TAB 2: Pipeline ──────────────────────────────────────────────────────────
with tab2:
    st.caption("All leads grouped by their current stage")
    cols = st.columns(len(STATUSES))
    for col, status in zip(cols, STATUSES):
        group = [l for l in leads if l.get("status") == status]
        color = STATUS_COLORS[status]
        with col:
            st.markdown(
                f'<div class="pip-col-head" style="color:{color}">'
                f'{status} <span style="opacity:.5">({len(group)})</span></div>',
                unsafe_allow_html=True,
            )
            for l in group:
                sc_color = SCORE_COLORS.get(l.get("score","Warm"),"#166534")
                st.markdown(f"""
                <div class="pip-mini">
                  <div class="pip-mini-name">{l['name'][:28]}</div>
                  <div class="pip-mini-sub">
                    {l.get('city','').split(',')[0]} · {(l.get('products') or [''])[0][:18]}
                  </div>
                  <div style="margin-top:4px;font-size:10px;font-weight:700;color:{sc_color}">
                    {l.get('score','')}
                  </div>
                </div>""", unsafe_allow_html=True)

# ─── TAB 3: Add Manually ──────────────────────────────────────────────────────
with tab3:
    st.markdown("### Add a lead manually")
    with st.form("add_lead_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        name          = c1.text_input("Company Name *")
        iec           = c2.text_input("IEC Number")
        city          = c1.text_input("City / State")
        phone         = c2.text_input("Phone")
        email         = c1.text_input("Email")
        website       = c2.text_input("Website")
        countries_in  = c1.text_input("Export Countries (comma separated)", placeholder="UAE, USA, UK")
        products_in   = c2.text_input("Products (comma separated)", placeholder="Basmati Rice, Wheat")
        shipments     = c1.text_input("Annual Shipments", placeholder="e.g. 45 shipments/yr")
        score         = c2.selectbox("Lead Score", ["Warm","Hot","Cold"])
        source        = st.text_input("Source URL")
        notes         = st.text_area("Notes", height=80)
        submitted     = st.form_submit_button("✅ Add Lead")

    if submitted:
        if not name.strip():
            st.error("Company name is required.")
        else:
            new_lead = {
                "id": int(time.time() * 1000),
                "name": name.strip(),
                "iec": iec.strip(),
                "city": city.strip(),
                "phone": phone.strip(),
                "email": email.strip(),
                "website": website.strip(),
                "countries": [c.strip() for c in countries_in.split(",") if c.strip()],
                "products":  [p.strip() for p in products_in.split(",")  if p.strip()],
                "shipments": shipments.strip(),
                "score": score,
                "status": "New",
                "notes": notes.strip(),
                "source": source.strip(),
                "added": datetime.now().strftime("%Y-%m-%d"),
            }
            st.session_state.leads.append(new_lead)
            save_leads(st.session_state.leads)
            st.success(f"✅ Lead '{name}' added successfully!")
            st.rerun()

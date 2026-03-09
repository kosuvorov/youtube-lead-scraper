import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from youtube_scraper import (
    scrape_youtube_for_leads,
    save_list,
    load_list,
    get_saved_list_names,
    get_exclude_ids_from_list,
    get_exclude_ids_from_csv,
    get_exclude_channels_from_list,
    get_exclude_channels_from_csv,
    save_preset,
    load_preset,
    get_preset_names,
    delete_preset,
)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="YouTube Lead Scraper", page_icon="🎯", layout="wide")

# ── shadcn-inspired CSS ─────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif !important;
}
.stApp {
    background-color: #09090b;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: #0a0a0c;
    border-right: 1px solid #27272a;
}
section[data-testid="stSidebar"] *:not(span[data-testid="stIconMaterial"]):not([class*="material"]):not([class*="icon"]) {
    color: #d4d4d8 !important;
    font-family: 'DM Sans', sans-serif !important;
}
section[data-testid="stSidebar"] span[data-testid="stIconMaterial"] {
    font-family: 'Material Symbols Rounded', 'Material Icons' !important;
    color: #d4d4d8 !important;
}
section[data-testid="stSidebar"] .stTextInput label,
section[data-testid="stSidebar"] .stSlider label,
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMultiSelect label,
section[data-testid="stSidebar"] .stCheckbox label,
section[data-testid="stSidebar"] .stNumberInput label,
section[data-testid="stSidebar"] .stDateInput label,
section[data-testid="stSidebar"] .stFileUploader label {
    color: #a1a1aa !important;
    font-weight: 500 !important;
    font-size: 0.8rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
}

/* ── Inputs ── */
section[data-testid="stSidebar"] input,
section[data-testid="stSidebar"] .stSelectbox > div > div,
section[data-testid="stSidebar"] .stMultiSelect > div > div {
    background-color: #18181b !important;
    border: 1px solid #27272a !important;
    border-radius: 6px !important;
    color: #fafafa !important;
}
section[data-testid="stSidebar"] input:focus {
    border-color: #10b981 !important;
    box-shadow: 0 0 0 1px #10b981 !important;
}

/* ── Expander ── */
section[data-testid="stSidebar"] .streamlit-expanderHeader {
    background-color: #18181b !important;
    border: 1px solid #27272a !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
    color: #fafafa !important;
}

/* ── Primary buttons ── */
.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
    border: none !important;
    border-radius: 6px !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
    letter-spacing: 0.02em;
    color: #ffffff !important;
    transition: all 0.15s ease;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover {
    background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
    transform: translateY(-1px);
}

/* ── Secondary buttons ── */
.stButton > button[kind="secondary"],
.stButton > button[data-testid="stBaseButton-secondary"] {
    background-color: #18181b !important;
    border: 1px solid #27272a !important;
    border-radius: 6px !important;
    color: #d4d4d8 !important;
    font-weight: 500 !important;
}

/* ── Download button ── */
.stDownloadButton > button {
    background-color: #18181b !important;
    border: 1px solid #27272a !important;
    border-radius: 6px !important;
    color: #10b981 !important;
    font-weight: 600 !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stDownloadButton > button:hover {
    background-color: #27272a !important;
    border-color: #10b981 !important;
}

/* ── Metrics ── */
div[data-testid="stMetric"] {
    background-color: #18181b;
    border: 1px solid #27272a;
    border-radius: 8px;
    padding: 16px 20px;
}
div[data-testid="stMetric"] label {
    color: #71717a !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    font-weight: 500 !important;
}
div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
    color: #fafafa !important;
    font-weight: 700 !important;
    font-size: 1.5rem !important;
}

/* ── Dataframe ── */
.stDataFrame {
    border: 1px solid #27272a;
    border-radius: 8px;
    overflow: hidden;
}

/* ── Header card ── */
.header-card {
    background-color: #18181b;
    border: 1px solid #27272a;
    border-radius: 12px;
    padding: 28px 32px;
    margin-bottom: 24px;
}
.header-card h1 {
    color: #fafafa;
    font-family: 'DM Sans', sans-serif;
    font-weight: 700;
    font-size: 1.6rem;
    margin: 0 0 4px 0;
}
.header-card p {
    color: #71717a;
    font-size: 0.9rem;
    margin: 0;
}

/* ── Estimate pill ── */
.estimate-pill {
    display: inline-block;
    background-color: #18181b;
    border: 1px solid #27272a;
    border-radius: 20px;
    padding: 6px 16px;
    color: #a1a1aa;
    font-size: 0.8rem;
    margin: 8px 0 12px 0;
}
.estimate-pill strong { color: #10b981; }

/* ── Section headers ── */
.section-header {
    color: #fafafa;
    font-family: 'DM Sans', sans-serif;
    font-weight: 600;
    font-size: 1rem;
    margin: 24px 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid #27272a;
}

/* ── Hint box ── */
.hint-box {
    background-color: #18181b;
    border: 1px solid #27272a;
    border-left: 3px solid #10b981;
    border-radius: 6px;
    padding: 10px 14px;
    color: #a1a1aa;
    font-size: 0.78rem;
    line-height: 1.5;
    margin-top: 4px;
}
.hint-box code {
    background-color: #27272a;
    padding: 1px 5px;
    border-radius: 3px;
    color: #10b981;
    font-size: 0.76rem;
}

/* ── Pipeline badge ── */
.pipeline-badge {
    display: inline-block;
    background-color: #18181b;
    border: 1px solid #27272a;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 0.7rem;
    color: #71717a;
    margin-right: 4px;
}
.pipeline-badge.active { border-color: #10b981; color: #10b981; }

/* ── Hide streamlit branding ── */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* ── Progress bar ── */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #10b981, #059669) !important;
}
</style>
""", unsafe_allow_html=True)

# ── PWA manifest injection ───────────────────────────────────────────────────
st.markdown("""
<link rel="manifest" href="app/static/manifest.json">
<meta name="theme-color" content="#09090b">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="YT Lead Scraper">
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-card">
    <h1>🎯 YouTube Lead Scraper</h1>
    <p>4-tier enrichment pipeline · Search → Bio → Social → Apify</p>
</div>
""", unsafe_allow_html=True)

# ── Session state ────────────────────────────────────────────────────────────
if 'results' not in st.session_state:
    st.session_state.results = []
if 'scraped_ids' not in st.session_state:
    st.session_state.scraped_ids = set()
if 'scraping_done' not in st.session_state:
    st.session_state.scraping_done = False

ALL_COLUMNS = [
    "Search Keyword", "Video URL", "Video Title", "Channel Name", "Channel URL",
    "Creator Name", "View Count", "Upload Date", "Duration (min)", "Subscriber Count",
    "Last Published", "Tags", "All Emails", "Desc Emails", "Bio Emails", "Social Emails",
    "Social Links", "Matching Hashtags", "Channel Bio", "Full Description",
    "Apify Emails",
]

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:

    # ── Search Presets ────────────────────────────────────────────────────
    with st.expander("💾  Presets", expanded=False):
        preset_names = get_preset_names()
        if preset_names:
            selected_preset = st.selectbox("Load preset", options=["—"] + preset_names)
            if selected_preset != "—":
                if st.button("📂 Load", key="load_preset_btn"):
                    st.session_state['loaded_preset'] = load_preset(selected_preset)
                    st.rerun()
                if st.button("🗑️ Delete", key="del_preset_btn"):
                    delete_preset(selected_preset)
                    st.rerun()
        else:
            st.caption("No saved presets yet.")
        st.markdown("---")
        preset_save_name = st.text_input("Save current as", placeholder="my_search_preset",
                                          key="preset_save_name")
        save_preset_btn = st.button("💾 Save Preset", key="save_preset_btn")

    # ── Apply loaded preset ──────────────────────────────────────────────
    lp = st.session_state.get('loaded_preset', {})

    # ── Search ────────────────────────────────────────────────────────────
    with st.expander("🔍  Search", expanded=True):
        query = st.text_input("Keywords", value=lp.get("query", ""),
                              placeholder="e.g. sales automation")
        st.markdown("""
        <div class="hint-box">
            <strong>Search operators:</strong><br>
            <code>"exact phrase"</code> — exact match<br>
            <code>sales|marketing</code> — OR<br>
            <code>sales -podcast</code> — exclude word<br>
            <code>intitle:automation</code> — title only
        </div>
        """, unsafe_allow_html=True)
        limit = st.slider("Max Results", min_value=5, max_value=2000,
                          value=lp.get("limit", 30), step=5)
        sort_options = ["relevance", "upload_date", "view_count", "rating"]
        sort_by = st.selectbox(
            "Sort By",
            options=sort_options,
            index=sort_options.index(lp.get("sort_by", "relevance")),
            format_func=lambda x: x.replace("_", " ").title(),
        )

    # ── Enrichment Pipeline ───────────────────────────────────────────────
    with st.expander("🔬  Enrichment Pipeline", expanded=True):
        st.caption("Control which tiers of the enrichment pipeline to run.")
        enable_bio = st.checkbox("Tier 2: Channel bio scraping", value=lp.get("enable_bio", True))
        enable_social = st.checkbox("Tier 3: Social URL scraping", value=lp.get("enable_social", True))
        search_emails = st.checkbox("Search emails in descriptions", value=lp.get("search_emails", True))
        search_hashtags_enabled = st.checkbox("Search specific hashtags",
                                              value=lp.get("search_hashtags_enabled", False))
        hashtags_input = ""
        if search_hashtags_enabled:
            hashtags_input = st.text_input("Hashtags (comma-separated)",
                                           value=lp.get("hashtags_input", ""),
                                           placeholder="#sales, #ai")

    # ── Filters ───────────────────────────────────────────────────────────
    with st.expander("⚙️  Filters", expanded=False):
        st.caption("Applied after scraping to refine results.")
        f1, f2 = st.columns(2)
        with f1:
            min_views = st.number_input("Min Views", min_value=0,
                                        value=lp.get("min_views", 0), step=1000)
        with f2:
            max_views = st.number_input("Max Views (0=∞)", min_value=0,
                                        value=lp.get("max_views", 0), step=10000)

        d1, d2 = st.columns(2)
        with d1:
            date_from = st.date_input("After", value=datetime.now().date() - timedelta(days=365))
        with d2:
            date_to = st.date_input("Before", value=datetime.now().date())

        dur1, dur2 = st.columns(2)
        with dur1:
            min_duration = st.number_input("Min Duration (m)", min_value=0.0,
                                           value=lp.get("min_duration", 0.0), step=1.0)
        with dur2:
            max_duration = st.number_input("Max Duration (m, 0=∞)", min_value=0.0,
                                           value=lp.get("max_duration", 0.0), step=5.0)

        min_subs = st.number_input("Min Subscribers", min_value=0,
                                   value=lp.get("min_subs", 0), step=1000)

        last_published_options = [
            "Any", "1 month", "2 months", "3 months", "4 months",
            "5 months", "6 months", "7 months", "8 months", "9 months",
            "10 months", "11 months", "12 months", "2 years",
        ]
        last_published_filter = st.selectbox(
            "Last Published Within",
            options=last_published_options,
            index=0,
            help="Only show channels that published a video within this period.",
        )

        tag_filter = st.text_input("Filter by Tags", value=lp.get("tag_filter", ""),
                                   placeholder="e.g. sales, automation",
                                   help="Comma-separated. Only show results containing these tags.")

    # ── Exclude Leads ─────────────────────────────────────────────────────
    with st.expander("🚫  Exclude Leads", expanded=False):
        st.caption("Skip leads you've already collected.")
        exclude_channels_toggle = st.checkbox(
            "Exclude by channel (not just video)",
            value=True,
            help="Skip entire channels found in excluded lists/CSVs.",
        )
        uploaded_csv = st.file_uploader("Import CSV to exclude", type=["csv"],
                                        key="exclude_csv")
        saved_lists = get_saved_list_names()
        exclude_lists = []
        if saved_lists:
            exclude_lists = st.multiselect("Exclude saved lists", options=saved_lists)
        else:
            st.caption("No saved lists yet.")

    # ── CSV Columns ───────────────────────────────────────────────────────
    with st.expander("📋  CSV Columns", expanded=False):
        st.caption("Choose columns for export.")
        default_cols = [c for c in ALL_COLUMNS
                        if c not in ("Full Description", "Channel Bio", "Desc Emails",
                                     "Bio Emails", "Social Emails")]
        selected_columns = st.multiselect("Columns to export", options=ALL_COLUMNS,
                                          default=default_cols)

    # ── Apify ─────────────────────────────────────────────────────────────
    with st.expander("🔗  Apify (Tier 4)", expanded=False):
        apify_api_token = st.text_input("API Token", type="password")
        apify_actor_id = st.text_input("Actor ID",
                                       value="datascoutapi/youtube-channel-email-scraper")

    st.markdown("---")

    # ── Time estimate ─────────────────────────────────────────────────────
    per_video = 3
    if enable_bio:
        per_video += 2
    if enable_social:
        per_video += 1
    est_seconds = limit * per_video
    est_minutes = round(est_seconds / 60, 1)
    st.markdown(
        f'<div class="estimate-pill">⏱ ~<strong>{est_minutes} min</strong> for {limit} videos</div>',
        unsafe_allow_html=True,
    )

    start_btn = st.button("🚀  Start Scraping", type="primary", use_container_width=True)

    # ── Save preset logic ─────────────────────────────────────────────────
    if save_preset_btn and preset_save_name and preset_save_name.strip():
        preset_data = {
            "query": query, "limit": limit, "sort_by": sort_by,
            "enable_bio": enable_bio, "enable_social": enable_social,
            "search_emails": search_emails,
            "search_hashtags_enabled": search_hashtags_enabled,
            "hashtags_input": hashtags_input,
            "min_views": min_views, "max_views": max_views,
            "min_duration": min_duration, "max_duration": max_duration,
            "min_subs": min_subs, "tag_filter": tag_filter,
        }
        save_preset(preset_save_name.strip(), preset_data)
        st.success(f"✅ Preset saved: {preset_save_name.strip()}")


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def build_exclude_ids():
    """Return (video_ids_set, channel_urls_set) for exclusion."""
    ids = set()
    channels = set()
    if uploaded_csv is not None:
        ids.update(get_exclude_ids_from_csv(uploaded_csv))
        if exclude_channels_toggle:
            uploaded_csv.seek(0)
            channels.update(get_exclude_channels_from_csv(uploaded_csv))
    for name in exclude_lists:
        ids.update(get_exclude_ids_from_list(name))
        if exclude_channels_toggle:
            channels.update(get_exclude_channels_from_list(name))
    return ids, channels


def apply_filters(df):
    if df.empty:
        return df
    out = df.copy()
    if min_views > 0:
        out = out[out["View Count"] >= min_views]
    if max_views > 0:
        out = out[out["View Count"] <= max_views]
    if "Upload Date" in out.columns:
        out["_dt"] = pd.to_datetime(out["Upload Date"], errors="coerce")
        out = out[(out["_dt"] >= pd.Timestamp(date_from)) & (out["_dt"] <= pd.Timestamp(date_to))]
        out = out.drop(columns=["_dt"], errors="ignore")
    if min_duration > 0:
        out = out[out["Duration (min)"] >= min_duration]
    if max_duration > 0:
        out = out[out["Duration (min)"] <= max_duration]
    if min_subs > 0:
        out = out[out["Subscriber Count"] >= min_subs]
    # Last Published filter
    if last_published_filter != "Any" and "Last Published" in out.columns:
        out["_lp"] = pd.to_datetime(out["Last Published"], errors="coerce")
        if last_published_filter == "2 years":
            cutoff = datetime.now() - timedelta(days=730)
        else:
            months = int(last_published_filter.split()[0])
            cutoff = datetime.now() - timedelta(days=months * 30)
        out = out[out["_lp"] >= pd.Timestamp(cutoff)]
        out = out.drop(columns=["_lp"], errors="ignore")
    if tag_filter and tag_filter.strip():
        filter_tags = [t.strip().lower() for t in tag_filter.split(",") if t.strip()]
        if filter_tags:
            out = out[out["Tags"].apply(
                lambda x: any(ft in str(x).lower() for ft in filter_tags) if pd.notna(x) else False
            )]
    return out


def run_scrape(num_results, exclude_ids, exclude_channels):
    progress_bar = st.progress(0)
    status_text = st.empty()
    live_table = st.empty()
    batch_results = []

    hashtag_list = None
    if search_hashtags_enabled and hashtags_input.strip():
        hashtag_list = [h.strip() if h.strip().startswith("#") else f"#{h.strip()}"
                        for h in hashtags_input.split(",") if h.strip()]

    def update_ui(data):
        if "error" in data:
            st.error(f"Error: {data['error']}")
            return
        if "status" in data:
            status_text.info(data["status"])
            return
        current = data.get("current", 1)
        total = data.get("total", 1)
        record = data.get("record")
        email_source = data.get("email_source", "")
        source_label = f" {email_source}" if email_source else ""
        progress_bar.progress(float(min(current / total, 1.0)))
        status_text.text(f"Scraping… {current}/{total}{source_label}")
        if record:
            batch_results.append(record)
            tmp_df = pd.DataFrame(batch_results)
            show_cols = [c for c in selected_columns if c in tmp_df.columns]
            live_table.dataframe(tmp_df[show_cols], use_container_width=True)

    results, new_ids = scrape_youtube_for_leads(
        query=query,
        max_results=num_results,
        sort_by=sort_by,
        search_emails=search_emails,
        search_hashtags=hashtag_list,
        exclude_video_ids=exclude_ids,
        exclude_channel_urls=exclude_channels,
        enrichment_api_key=apify_api_token if apify_api_token else None,
        apify_actor_id=apify_actor_id if apify_actor_id else None,
        enable_bio_scraping=enable_bio,
        enable_social_scraping=enable_social,
        progress_callback=update_ui,
    )

    progress_bar.empty()
    status_text.success(f"✅ Scraped {len(results)} videos!")
    return results, new_ids


# ══════════════════════════════════════════════════════════════════════════════
# MAIN: Start Scraping
# ══════════════════════════════════════════════════════════════════════════════
if start_btn:
    if not query:
        st.warning("Please enter keywords first.")
    else:
        st.session_state.results = []
        st.session_state.scraped_ids = set()
        st.session_state.scraping_done = False

        exclude_ids, exclude_channels = build_exclude_ids()
        results, new_ids = run_scrape(limit, exclude_ids, exclude_channels)
        st.session_state.results = results
        st.session_state.scraped_ids = new_ids
        st.session_state.scraping_done = True


# ══════════════════════════════════════════════════════════════════════════════
# RESULTS
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.scraping_done and st.session_state.results:
    df = pd.DataFrame(st.session_state.results)
    df_filtered = apply_filters(df)

    # ── Metrics ───────────────────────────────────────────────────────────
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total Results", len(df_filtered))
    emails_found = df_filtered["All Emails"].apply(lambda x: 1 if x else 0).sum()
    m2.metric("Emails Found", emails_found)
    m3.metric("Unique Channels", df_filtered["Channel Name"].nunique())
    names_found = df_filtered["Creator Name"].apply(lambda x: 1 if x else 0).sum()
    m4.metric("Creator Names", names_found)
    avg_views = int(df_filtered["View Count"].mean()) if not df_filtered.empty else 0
    m5.metric("Avg Views", f"{avg_views:,}")

    # ── Table ─────────────────────────────────────────────────────────────
    st.markdown('<div class="section-header">📊 Results</div>', unsafe_allow_html=True)
    display_cols = [c for c in selected_columns if c in df_filtered.columns]
    st.dataframe(df_filtered[display_cols], use_container_width=True, height=420)

    # ── Export & Save ─────────────────────────────────────────────────────
    exp_col1, exp_col2, exp_col3 = st.columns([2, 2, 3])

    with exp_col1:
        csv = df_filtered[display_cols].to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️  Download CSV",
            data=csv,
            file_name=f"youtube_leads_{query.replace(' ', '_')}.csv",
            mime="text/csv",
        )

    with exp_col2:
        list_name = st.text_input("List name", placeholder="my_leads_march",
                                  label_visibility="collapsed")

    with exp_col3:
        if st.button("💾  Save as List", type="primary"):
            if list_name and list_name.strip():
                save_list(list_name.strip(), st.session_state.results)
                st.success(f"Saved list: {list_name.strip()}")
            else:
                st.warning("Enter a name for the list.")

    # ── Continue Scraping ─────────────────────────────────────────────────
    st.markdown('<div class="section-header">🔄 Continue Scraping</div>', unsafe_allow_html=True)
    st.caption("Fetch more leads with the same search. Already-scraped videos are skipped.")

    cont1, cont2 = st.columns([2, 1])
    with cont1:
        more_count = st.number_input("More leads", min_value=5, max_value=2000,
                                      value=30, step=5, key="more_count",
                                      label_visibility="collapsed")
    with cont2:
        continue_btn = st.button("Continue →", type="primary", key="cont_btn")

    if continue_btn:
        base_ids, base_channels = build_exclude_ids()
        exclude_ids = base_ids | st.session_state.scraped_ids
        new_results, new_ids = run_scrape(more_count, exclude_ids, base_channels)
        st.session_state.results.extend(new_results)
        st.session_state.scraped_ids.update(new_ids)
        st.rerun()

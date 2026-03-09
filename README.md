# YouTube Lead Scraper 🎯

4-tier waterfall enrichment pipeline for YouTube lead generation. Search YouTube, extract channel data, emails, and creator names, then export leads to CSV.

## Features

- **🔍 Smart Search** — Keywords with logical operators (`"exact phrase"`, `-exclude`, `intitle:`)
- **📊 Rich Data** — View count, upload date, duration, subscriber count, tags
- **📧 4-Tier Email Enrichment**
  1. Video description regex
  2. Channel bio extraction via yt-dlp
  3. Social URL scraping (Linktree, personal sites)
  4. Apify fallback for unresolved channels
- **👤 Creator Name Extraction** — Parses bios for real names
- **⚙️ Post-Scrape Filters** — View count, date range, duration, subscribers, tags
- **📋 Named Lists** — Save/load lead lists locally
- **💾 Search Presets** — Save/load search configurations
- **🚫 Deduplication** — Import CSV or select lists to exclude
- **🔄 Continue Scraping** — Fetch more leads without repeats

## Setup

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install streamlit scrapetube yt-dlp pandas requests apify-client

# Run
streamlit run app.py
```

## Usage

1. Open http://localhost:8501
2. Enter search keywords in the sidebar
3. Configure enrichment pipeline (enable/disable tiers)
4. Click **Start Scraping**
5. Filter, export CSV, or save as a named list

## PWA

Install as a desktop app from Chrome/Edge: **⋮ → Install YouTube Lead Scraper**

## Local Storage

- **Lists**: `~/yt/lists/` (JSON)
- **Presets**: `~/yt/presets/` (JSON)

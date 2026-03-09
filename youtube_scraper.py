import scrapetube
import pandas as pd
import re
import argparse
import sys
import json
import os
import requests
from apify_client import ApifyClient
import yt_dlp

# ── Storage directories ─────────────────────────────────────────────────────
LISTS_DIR = os.path.expanduser("~/yt/lists")
PRESETS_DIR = os.path.expanduser("~/yt/presets")
os.makedirs(LISTS_DIR, exist_ok=True)
os.makedirs(PRESETS_DIR, exist_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def extract_emails(text):
    """Find email addresses in text using regex."""
    if not text:
        return []
    pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    emails = re.findall(pattern, text)
    # Filter out common false positives
    false_positives = {'example.com', 'email.com', 'domain.com', 'test.com',
                       'yourname', 'youremail', 'your@'}
    cleaned = []
    for e in emails:
        e_lower = e.lower()
        if not any(fp in e_lower for fp in false_positives):
            cleaned.append(e.lower())
    return list(set(cleaned))


def extract_hashtags(text):
    """Find all hashtags in text."""
    if not text:
        return []
    return list(set(re.findall(r'#\w+', text.lower())))


def extract_creator_name(bio_text, channel_name=""):
    """Try to extract the creator's real name from bio text or channel name."""
    if bio_text:
        # Direct name patterns
        patterns = [
            r"(?:my name is|i'?m|i am|hey,? i'?m|hi,? i'?m|hello,? i'?m)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"(?:my name is|i'?m|i am)\s+(\w+(?:\s+\w+)?)",
            r"(?:about me|about:?)\s*(?:[-–—]?\s*)([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"hosted by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"created by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"run by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, bio_text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Filter out generic words
                generic = {'a', 'an', 'the', 'not', 'just', 'here', 'your',
                           'this', 'that', 'from', 'with', 'back', 'so'}
                words = name.split()
                if words and words[0].lower() not in generic and len(words[0]) > 1:
                    return name.title()

    # Fallback: if channel name looks like a real name
    if channel_name and channel_name != "Unknown":
        words = channel_name.split()
        if 2 <= len(words) <= 3:
            if all(w[0].isupper() and w.isalpha() for w in words):
                return channel_name
    return ""


def extract_social_links(text):
    """Extract social media and external links from text."""
    if not text:
        return []
    patterns = [
        r'https?://(?:www\.)?linktr\.ee/\S+',
        r'https?://(?:www\.)?instagram\.com/\S+',
        r'https?://(?:www\.)?twitter\.com/\S+',
        r'https?://(?:www\.)?x\.com/\S+',
        r'https?://(?:www\.)?linkedin\.com/\S+',
        r'https?://(?:www\.)?tiktok\.com/\S+',
        r'https?://(?:www\.)?facebook\.com/\S+',
        r'https?://[a-zA-Z0-9-]+\.\w{2,}(?:/\S*)?',  # generic URLs
    ]
    links = []
    for p in patterns:
        links.extend(re.findall(p, text))
    # Deduplicate and clean
    cleaned = []
    seen = set()
    skip_domains = {'youtube.com', 'youtu.be', 'google.com', 'googleapis.com',
                    'gstatic.com', 'ggpht.com', 'ytimg.com'}
    for link in links:
        link = link.rstrip('.,;:!?)"\'>]')
        domain = re.search(r'://(?:www\.)?([^/]+)', link)
        if domain:
            d = domain.group(1).lower()
            if d not in skip_domains and link not in seen:
                seen.add(link)
                cleaned.append(link)
    return cleaned[:10]  # Cap at 10 links


# ══════════════════════════════════════════════════════════════════════════════
# TIER 1: VIDEO METADATA (already exists)
# ══════════════════════════════════════════════════════════════════════════════

def get_full_metadata(video_url):
    """Uses yt-dlp to grab full video metadata without downloading."""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extract_flat': False,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            duration_secs = info.get('duration', 0) or 0
            upload_date_raw = info.get('upload_date', '')
            upload_date = ""
            if upload_date_raw and len(upload_date_raw) == 8:
                upload_date = f"{upload_date_raw[:4]}-{upload_date_raw[4:6]}-{upload_date_raw[6:8]}"
            return {
                'description': info.get('description', '') or '',
                'view_count': info.get('view_count', 0) or 0,
                'upload_date': upload_date,
                'duration_min': round(duration_secs / 60, 1),
                'subscriber_count': info.get('channel_follower_count', 0) or 0,
                'tags': info.get('tags', []) or [],
            }
    except Exception:
        return {
            'description': '', 'view_count': 0, 'upload_date': '',
            'duration_min': 0, 'subscriber_count': 0, 'tags': [],
        }


# ══════════════════════════════════════════════════════════════════════════════
# TIER 2: CHANNEL BIO EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def get_channel_bio(channel_url):
    """Fetch channel About page bio, social links, and last published date using yt-dlp."""
    empty = {'bio': '', 'bio_emails': [], 'social_links': [], 'creator_name': '', 'last_published': ''}
    if not channel_url or channel_url == "Unknown":
        return empty

    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extract_flat': True,
        'playlist_items': '0',
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            bio = info.get('description', '') or ''
            channel_name = info.get('channel', '') or info.get('uploader', '') or ''

            # Extract emails from bio
            bio_emails = extract_emails(bio)

            # Extract social links from bio
            social_links = extract_social_links(bio)

            # Also check for links in channel metadata
            webpage_url = info.get('webpage_url', '')
            if webpage_url:
                social_links.extend(extract_social_links(webpage_url))

            # Extract creator name
            creator_name = extract_creator_name(bio, channel_name)

            # Extract last published video date from channel entries
            last_published = ''
            entries = info.get('entries', [])
            if entries:
                # entries is a generator or list of flat video dicts
                for entry in entries:
                    if isinstance(entry, dict):
                        raw_date = entry.get('upload_date', '') or ''
                        if raw_date and len(raw_date) == 8:
                            last_published = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                            break  # First entry = most recent

            # Fallback: try modified_date or upload_date on channel itself
            if not last_published:
                raw = info.get('modified_date', '') or info.get('upload_date', '') or ''
                if raw and len(raw) == 8:
                    last_published = f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"

            return {
                'bio': bio,
                'bio_emails': list(set(bio_emails)),
                'social_links': list(set(social_links))[:10],
                'creator_name': creator_name,
                'last_published': last_published,
            }
    except Exception:
        return empty


# ══════════════════════════════════════════════════════════════════════════════
# TIER 3: SOCIAL URL SCRAPING
# ══════════════════════════════════════════════════════════════════════════════

def scrape_social_links_for_emails(social_links):
    """Visit social link pages and try to extract emails from HTML."""
    found_emails = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0.0.0 Safari/537.36',
    }
    # Prioritize Linktree and personal domains
    priority_domains = ['linktr.ee', 'linktree', 'beacons.ai', 'bio.link',
                        'carrd.co', 'stan.store']
    sorted_links = sorted(
        social_links,
        key=lambda l: any(d in l.lower() for d in priority_domains),
        reverse=True,
    )

    for link in sorted_links[:5]:  # Only visit first 5 links
        try:
            resp = requests.get(link, headers=headers, timeout=5, allow_redirects=True)
            if resp.status_code == 200:
                # Check for mailto: links
                mailto_emails = re.findall(r'mailto:([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)',
                                           resp.text)
                found_emails.extend(mailto_emails)
                # General email regex on page text
                page_emails = extract_emails(resp.text)
                found_emails.extend(page_emails)
        except Exception:
            continue

    return list(set(found_emails))


# ══════════════════════════════════════════════════════════════════════════════
# TIER 4: APIFY ENRICHMENT (existing)
# ══════════════════════════════════════════════════════════════════════════════

def enrich_with_apify(api_key, actor_id, channel_urls, progress_callback=None):
    """Batches channel URLs and runs an Apify Actor to find hidden emails."""
    if not api_key or not actor_id or not channel_urls:
        return {}
    if progress_callback:
        progress_callback({"status": "⏳ Tier 4: Running Apify Actor…"})
    client = ApifyClient(api_key)
    start_urls = [{"url": url} for url in channel_urls]
    run_input = {"startUrls": start_urls}
    try:
        run = client.actor(actor_id).call(run_input=run_input)
        if progress_callback:
            progress_callback({"status": "Apify run finished. Fetching results…"})
        results = {}
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            actor_url = item.get("url") or item.get("channelUrl") or ""
            actor_emails = item.get("emails") or item.get("email") or []
            if isinstance(actor_emails, str):
                actor_emails = [actor_emails]
            if actor_url and actor_emails:
                results[actor_url] = actor_emails
        return results
    except Exception as e:
        if progress_callback:
            progress_callback({"error": f"Apify Error: {str(e)}"})
        return {}


# ══════════════════════════════════════════════════════════════════════════════
# LISTS HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def save_list(name, records):
    path = os.path.join(LISTS_DIR, f"{name}.json")
    with open(path, "w") as f:
        json.dump(records, f, indent=2)
    return path

def load_list(name):
    path = os.path.join(LISTS_DIR, f"{name}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []

def get_saved_list_names():
    if not os.path.exists(LISTS_DIR):
        return []
    return sorted([f.replace(".json", "") for f in os.listdir(LISTS_DIR) if f.endswith(".json")])

def get_exclude_ids_from_list(name):
    records = load_list(name)
    ids = set()
    for r in records:
        url = r.get("Video URL", "")
        if "watch?v=" in url:
            ids.add(url.split("watch?v=")[-1].split("&")[0])
    return ids

def get_exclude_channels_from_list(name):
    """Extract channel URLs from a saved list for channel-level exclusion."""
    records = load_list(name)
    channels = set()
    for r in records:
        ch = r.get("Channel URL", "")
        if ch and ch != "Unknown":
            channels.add(ch.rstrip("/"))
    return channels

def get_exclude_ids_from_csv(csv_content):
    try:
        df = pd.read_csv(csv_content)
        ids = set()
        if "Video URL" in df.columns:
            for url in df["Video URL"].dropna():
                if "watch?v=" in str(url):
                    ids.add(str(url).split("watch?v=")[-1].split("&")[0])
        return ids
    except Exception:
        return set()

def get_exclude_channels_from_csv(csv_content):
    """Extract channel URLs from uploaded CSV for channel-level exclusion."""
    try:
        csv_content.seek(0)
        df = pd.read_csv(csv_content)
        channels = set()
        if "Channel URL" in df.columns:
            for url in df["Channel URL"].dropna():
                if str(url) != "Unknown":
                    channels.add(str(url).rstrip("/"))
        return channels
    except Exception:
        return set()


# ══════════════════════════════════════════════════════════════════════════════
# PRESET HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def save_preset(name, preset_data):
    path = os.path.join(PRESETS_DIR, f"{name}.json")
    with open(path, "w") as f:
        json.dump(preset_data, f, indent=2)
    return path

def load_preset(name):
    path = os.path.join(PRESETS_DIR, f"{name}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def get_preset_names():
    if not os.path.exists(PRESETS_DIR):
        return []
    return sorted([f.replace(".json", "") for f in os.listdir(PRESETS_DIR) if f.endswith(".json")])

def delete_preset(name):
    path = os.path.join(PRESETS_DIR, f"{name}.json")
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
# MAIN SCRAPE FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def scrape_youtube_for_leads(
    query,
    max_results=50,
    sort_by="relevance",
    search_emails=True,
    search_hashtags=None,
    exclude_video_ids=None,
    exclude_channel_urls=None,
    enrichment_api_key=None,
    apify_actor_id=None,
    enable_bio_scraping=True,
    enable_social_scraping=True,
    progress_callback=None,
):
    if exclude_video_ids is None:
        exclude_video_ids = set()
    if exclude_channel_urls is None:
        exclude_channel_urls = set()
    # Normalize channel URLs for comparison
    exclude_channel_urls = {u.rstrip('/') for u in exclude_channel_urls}
    fetch_limit = max_results + len(exclude_video_ids) + len(exclude_channel_urls) * 5

    try:
        generator = scrapetube.get_search(query, limit=fetch_limit, sort_by=sort_by)
    except Exception as e:
        if progress_callback:
            progress_callback({"error": str(e)})
        return [], set()

    results = []
    new_video_ids = set()
    collected = 0
    channel_cache = {}  # Cache bio lookups per channel

    for video in generator:
        if collected >= max_results:
            break
        video_id = video.get('videoId')
        if not video_id or video_id in exclude_video_ids:
            continue

        video_url = f"https://www.youtube.com/watch?v={video_id}"

        title = ""
        try:
            title = video.get('title', {}).get('runs', [{}])[0].get('text', '')
        except Exception:
            pass

        channel_name = "Unknown"
        channel_url = "Unknown"
        try:
            byline = video.get('longBylineText', {}).get('runs', [{}])[0]
            channel_name = byline.get('text', 'Unknown')
            browse_endpoint = byline.get('navigationEndpoint', {}).get('browseEndpoint', {})
            canonical_base_url = browse_endpoint.get('canonicalBaseUrl')
            browse_id = browse_endpoint.get('browseId')
            if canonical_base_url:
                channel_url = f"https://www.youtube.com{canonical_base_url}"
            elif browse_id:
                channel_url = f"https://www.youtube.com/channel/{browse_id}"
        except Exception:
            pass

        # ── Skip excluded channels ───────────────────────────────────────
        if channel_url != "Unknown" and channel_url.rstrip('/') in exclude_channel_urls:
            continue

        # ── TIER 1: Video metadata & description emails ──────────────────
        meta = get_full_metadata(video_url)
        full_description = meta['description']
        if not full_description:
            try:
                snippets = video.get('detailedMetadataSnippets', [])
                if snippets:
                    runs = snippets[0].get('snippetText', {}).get('runs', [])
                    full_description = "".join([run.get('text', '') for run in runs])
            except Exception:
                pass

        desc_emails = []
        if search_emails:
            desc_emails = extract_emails(full_description)

        matching_hashtags = []
        if search_hashtags:
            desc_hashtags = extract_hashtags(full_description)
            matching_hashtags = [h for h in search_hashtags if h.lower() in desc_hashtags]

        # ── TIER 2: Channel bio extraction (cached per channel) ──────────
        bio_emails = []
        social_links_from_bio = []
        creator_name = ""
        channel_bio = ""
        last_published = ""

        if enable_bio_scraping and channel_url != "Unknown":
            if channel_url not in channel_cache:
                bio_data = get_channel_bio(channel_url)
                channel_cache[channel_url] = bio_data
            cached = channel_cache[channel_url]
            channel_bio = cached['bio']
            bio_emails = cached['bio_emails']
            social_links_from_bio = cached['social_links']
            creator_name = cached['creator_name']
            last_published = cached.get('last_published', '')

        # ── TIER 3: Social URL scraping ──────────────────────────────────
        social_emails = []
        all_social_links = list(set(
            social_links_from_bio + extract_social_links(full_description)
        ))

        if enable_social_scraping and all_social_links:
            # Only scrape if we don't have emails yet
            all_found = set(desc_emails + bio_emails)
            if not all_found:
                social_emails = scrape_social_links_for_emails(all_social_links)

        # ── Merge all emails ─────────────────────────────────────────────
        all_emails = list(set(desc_emails + bio_emails + social_emails))

        record = {
            "Search Keyword": query,
            "Video URL": video_url,
            "Video Title": title,
            "Channel Name": channel_name,
            "Channel URL": channel_url,
            "Creator Name": creator_name,
            "View Count": meta['view_count'],
            "Upload Date": meta['upload_date'],
            "Duration (min)": meta['duration_min'],
            "Subscriber Count": meta['subscriber_count'],
            "Last Published": last_published,
            "Tags": ", ".join(meta['tags']) if meta['tags'] else "",
            "Desc Emails": ", ".join(desc_emails) if desc_emails else "",
            "Bio Emails": ", ".join(bio_emails) if bio_emails else "",
            "Social Emails": ", ".join(social_emails) if social_emails else "",
            "All Emails": ", ".join(all_emails) if all_emails else "",
            "Social Links": ", ".join(all_social_links[:5]) if all_social_links else "",
            "Matching Hashtags": ", ".join(matching_hashtags) if matching_hashtags else "",
            "Channel Bio": channel_bio[:500] if channel_bio else "",
            "Full Description": full_description,
            "Apify Emails": "",
        }

        results.append(record)
        new_video_ids.add(video_id)
        collected += 1

        if progress_callback:
            email_source = ""
            if desc_emails:
                email_source = "📝 desc"
            elif bio_emails:
                email_source = "📋 bio"
            elif social_emails:
                email_source = "🔗 social"
            progress_callback({
                "current": collected,
                "total": max_results,
                "record": record,
                "email_source": email_source,
            })

    # ── TIER 4: Apify enrichment for unresolved channels ─────────────────
    if enrichment_api_key and apify_actor_id and results:
        unresolved = [r["Channel URL"] for r in results
                      if r["Channel URL"] != "Unknown" and not r["All Emails"]]
        unresolved = list(set(unresolved))
        if unresolved:
            if progress_callback:
                progress_callback({"status": f"⏳ Tier 4: {len(unresolved)} channels without emails → Apify…"})
            apify_results = enrich_with_apify(
                api_key=enrichment_api_key,
                actor_id=apify_actor_id,
                channel_urls=unresolved,
                progress_callback=progress_callback,
            )
            for r in results:
                curl = r["Channel URL"]
                if curl in apify_results:
                    apify_emails = apify_results[curl]
                    r["Apify Emails"] = ", ".join(apify_emails)
                    # Also merge into All Emails
                    existing = set(e.strip() for e in r["All Emails"].split(",") if e.strip())
                    existing.update(e.lower() for e in apify_emails)
                    r["All Emails"] = ", ".join(existing)

    return results, new_video_ids


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Lead Scraper")
    parser.add_argument("query", type=str)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--sort", type=str, default="relevance",
                        choices=["relevance", "upload_date", "view_count", "rating"])
    parser.add_argument("--output", type=str, default="youtube_leads.csv")
    parser.add_argument("--api-key", type=str, default=None)
    args = parser.parse_args()
    results, _ = scrape_youtube_for_leads(
        query=args.query, max_results=args.limit, sort_by=args.sort,
        enrichment_api_key=args.api_key,
    )
    if results:
        df = pd.DataFrame(results)
        df.to_csv(args.output, index=False)
        print(f"\nSaved {len(results)} results to {args.output}")

#!/usr/bin/env python3
"""
KinderCare / HiMama media downloader + metadata fixer
======================================================

WHAT THIS DOES
1. Logs into the activities feed using YOUR browser session cookie (you must
   supply it — the script does not know your password and never asks for it).
2. Walks pages 1..N of https://classroom.kindercare.com/accounts/<ACCOUNT_ID>/activities
3. Finds every S3 media download link on each page, plus the date shown next
   to that piece of media.
4. Downloads each file.
5. Uses exiftool to write the correct "date taken" metadata into the file
   itself (works for both images and .MOV/.mp4 video), and also sets the
   file's OS-level modified/created time to match, so photo-import apps that
   only look at filesystem dates still get it right.

BEFORE YOU RUN THIS
--------------------
Full step-by-step setup instructions (installing Python, exiftool, and the
required packages from scratch, for both Mac and Windows) are in
kindercare_setup_guide.md, which should be sitting alongside this script.
Read that first if you haven't set anything up yet.

Quick reference, if you already have Python + exiftool installed:

1. Create and activate a virtual environment, then install packages:
     macOS/Linux:
       python3 -m venv env
       source env/bin/activate
       pip install requests beautifulsoup4 python-dateutil
     Windows (PowerShell):
       python -m venv env
       .\\env\\Scripts\\Activate.ps1
       pip install requests beautifulsoup4 python-dateutil

2. Get your session cookie:
   - Log into classroom.kindercare.com in your browser.
   - Open DevTools (F12) -> Network tab -> reload the activities page.
   - Click the first request to .../activities -> Headers -> find "Cookie:"
   - Copy the FULL cookie header value and paste it into COOKIE_HEADER below.
   (This cookie is sensitive — treat it like a password. Don't share this
   script with it filled in, and clear it when you're done.)

3. This script parses the activities table directly: each row's date comes
   from the row's 2nd column (e.g. "9/4/26"), and the file link is the <a>
   tag with a `download="..."` attribute (which is only present on the real
   file link, not thumbnails). Still, do a quick sanity check before the
   full run:
     - Run with --pages 1 first (a single page).
     - Check the printed dates against what you see in your browser.

USAGE
-----
  python3 kindercare_download.py --account YOUR_ACCOUNT_ID --pages YOUR_PAGE_COUNT --out ./kindercare_media

"""

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from urllib.parse import urlparse, unquote

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dateparser

# ---------------------------------------------------------------------------
# CONFIG — fill this in
# ---------------------------------------------------------------------------

COOKIE_HEADER = "PASTE_YOUR_COOKIE_HEADER_HERE"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

REQUEST_DELAY_SECONDS = 1.0  # be polite to the server between page loads

# ---------------------------------------------------------------------------


def build_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Cookie": COOKIE_HEADER,
    })
    return s


def fetch_page(session, account_id, page_num):
    url = f"https://classroom.kindercare.com/accounts/{account_id}/activities?page={page_num}"
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def find_activity_rows(soup):
    """
    The activities feed renders as a <table class="table table-hover ...">
    with one <tr> per activity. Each row's actual downloadable file is the
    <a> tag that has a `download="..."` attribute (thumbnails and the
    "view activity" links do NOT have this attribute, which is what lets us
    tell them apart). The row's date lives in its 2nd <td>, as "M/D/YY"
    (e.g. "9/4/26").
    """
    table = soup.find("table", class_="table-hover")
    if table is None:
        return []
    tbody = table.find("tbody")
    if tbody is None:
        return []
    return tbody.find_all("tr", recursive=False)


def extract_link_and_date(row):
    """Given one activity <tr>, return (url, datetime) or (None, None)."""
    dl_tag = row.find("a", attrs={"download": True})
    if dl_tag is None or not dl_tag.get("href"):
        return None, None
    url = dl_tag["href"]

    tds = row.find_all("td", recursive=False)
    media_date = None
    if len(tds) >= 2:
        date_text = tds[1].get_text(strip=True)
        try:
            media_date = dateparser.parse(date_text)
        except (ValueError, TypeError):
            media_date = None

    return url, media_date


def filename_from_url(url):
    """
    Build a filename that can't collide across activities. The raw S3 path
    looks like: .../activity_file/<image|video>/<activity_id>/<name>
    Different activities can reuse the same <name> (e.g. two videos both
    named "8248.mov" from a phone's default naming), so we prefix with the
    activity_id to guarantee uniqueness.
    """
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    raw_name = unquote(parts[-1]) if parts else "file"
    activity_id = parts[-2] if len(parts) >= 2 else None

    # Strip the "big_"/"thumb_" prefix HiMama adds to image filenames.
    raw_name = re.sub(r"^(thumb_|big_)", "", raw_name)

    if activity_id:
        return f"{activity_id}_{raw_name}"
    return raw_name


def download_file(session, url, dest_path):
    resp = session.get(url, stream=True, timeout=60)
    resp.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1 << 16):
            f.write(chunk)


def set_metadata_date(file_path, dt):
    """Use exiftool to write the capture date into the file, then set
    filesystem mtime/atime to match as a fallback."""
    exif_date_str = dt.strftime("%Y:%m:%d %H:%M:%S")

    # exiftool tag names differ slightly between image and video containers,
    # so we just set the common ones; exiftool ignores tags that don't apply.
    cmd = [
        "exiftool",
        "-overwrite_original",
        f"-AllDates={exif_date_str}",
        f"-QuickTime:CreateDate={exif_date_str}",
        f"-QuickTime:ModifyDate={exif_date_str}",
        f"-QuickTime:TrackCreateDate={exif_date_str}",
        f"-QuickTime:TrackModifyDate={exif_date_str}",
        f"-QuickTime:MediaCreateDate={exif_date_str}",
        f"-QuickTime:MediaModifyDate={exif_date_str}",
        file_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [exiftool warning] {file_path}: {result.stderr.strip()}")

    # Also set OS-level mtime/atime as a fallback for tools that don't read
    # embedded metadata.
    ts = dt.timestamp()
    os.utime(file_path, (ts, ts))


def main():
    parser = argparse.ArgumentParser(description="Download KinderCare media with correct dates")
    parser.add_argument("--account", required=True, help="Your account ID, found in the URL: classroom.kindercare.com/accounts/<ACCOUNT_ID>/activities")
    parser.add_argument("--pages", type=int, required=True, help="Total number of pages in your activities feed (shown in the site's pagination controls)")
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--out", default="./kindercare_media", help="Output directory")
    args = parser.parse_args()

    if COOKIE_HEADER == "PASTE_YOUR_COOKIE_HEADER_HERE":
        sys.exit(
            "You haven't added your login cookie yet.\n"
            "Open kindercare_download.py in a text editor, find the COOKIE_HEADER line "
            "near the top, and paste your cookie there.\n"
            "See kindercare_setup_guide.md, section \"Get your login cookie\", for how to grab it."
        )

    # Make sure exiftool is actually installed before we download anything —
    # better to fail immediately with a clear message than after downloading
    # every page of media with no dates set.
    try:
        subprocess.run(["exiftool", "-ver"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        sys.exit(
            "exiftool doesn't seem to be installed (or isn't on your PATH).\n"
            "See kindercare_setup_guide.md, section \"Install exiftool\", for setup steps."
        )

    os.makedirs(args.out, exist_ok=True)
    session = build_session()

    total_downloaded = 0
    total_failed = 0

    for page_num in range(args.start_page, args.start_page + args.pages):
        print(f"\n=== Page {page_num} ===")
        try:
            html = fetch_page(session, args.account, page_num)
        except requests.RequestException as e:
            print(f"  Failed to fetch page {page_num}: {e}")
            total_failed += 1
            continue

        soup = BeautifulSoup(html, "html.parser")
        rows = find_activity_rows(soup)

        if not rows:
            print("  No activity rows found on this page (check cookie validity / you may have hit the last page).")

        for row in rows:
            url, media_date = extract_link_and_date(row)
            if url is None:
                continue  # row had no downloadable file (text-only journal entry, etc.)

            fname = filename_from_url(url)
            dest_path = os.path.join(args.out, fname)

            if os.path.exists(dest_path):
                print(f"  Skipping (already downloaded): {fname}")
                continue

            if media_date is None:
                print(f"  [WARNING] Could not parse date for {fname}; using today's date instead.")
                media_date = datetime.now()

            try:
                download_file(session, url, dest_path)
                set_metadata_date(dest_path, media_date)
                print(f"  Downloaded + dated {media_date.date()}: {fname}")
                total_downloaded += 1
            except Exception as e:
                print(f"  [ERROR] {fname}: {e}")
                total_failed += 1

        time.sleep(REQUEST_DELAY_SECONDS)

    print(f"\nDone. Downloaded: {total_downloaded}, Failed: {total_failed}")


if __name__ == "__main__":
    main()

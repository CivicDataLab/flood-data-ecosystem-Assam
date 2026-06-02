"""
ASDMA SEC Meeting Minutes - PDF Downloader
==========================================
1. Scrapes the ASDMA listing page for every PDF link.
2. Builds a full list (pdf_list.csv) before downloading anything.
3. Downloads each PDF, skipping files already present in the download folder.

Usage:
    python 01_download_pdfs.py [--list-only]

    --list-only   Discover and print all PDF URLs without downloading.

Output:
    ../pdfs/           — downloaded PDF files
    ../data/pdf_list.csv   — master list of every discovered PDF
    ../data/pdf_index.csv  — download log (status per file)
"""

import os
import re
import sys
import time
import csv
import requests
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL     = "https://asdma.assam.gov.in"
LISTING_URL  = f"{BASE_URL}/documents-detail/minutes-of-sec-meetings-of-asdma"
PDF_DIR      = Path(__file__).parent.parent.parent / "data" / "sec_meeting" / "raw_pdfs"
DATA_DIR     = Path(__file__).parent.parent.parent / "data" / "sec_meeting" / "processed"

PDF_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer":         BASE_URL,
}

POLITE_DELAY = 0.5   # seconds between requests
MIN_PDF_BYTES = 1000 # anything smaller is assumed to be an error page
DUPLICATE_SIZE_TOLERANCE = 0.10  # skip if an existing similar-named file is within 10% size

# ── Step 1: Discover all PDFs ─────────────────────────────────────────────────

def scrape_listing_page(session):
    """
    Try to pull every PDF href from the ASDMA listing page.
    Returns a list of dicts: {url, title, source}.
    """
    found = []
    try:
        print(f"[discover] Fetching listing page: {LISTING_URL}")
        resp = session.get(LISTING_URL, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ".pdf" in href.lower():
                full_url = urljoin(BASE_URL, href)
                title    = a.get_text(strip=True) or unquote(os.path.basename(urlparse(full_url).path))
                found.append({"url": full_url, "title": title, "source": "scraped"})
                print(f"  [found] {full_url}")

        if found:
            print(f"[discover] {len(found)} PDF links found on listing page.")
        else:
            print("[discover] No PDF links found (page may be JS-rendered).")
    except Exception as exc:
        print(f"[discover] Listing page fetch failed: {exc}")

    return found


def build_pattern_urls():
    """
    Generate candidate URLs using the two URL patterns observed on the ASDMA site:
      Pattern A (older):  /sites/default/files/<N><suf>%20SEC%20Meeting.pdf
      Pattern B (newer):  /sites/default/files/swf_utility_folder/.../document/<slug>.pdf

    Pattern B slugs can't be guessed reliably, so we cover A and leave B to
    the scraper.  Extend PATTERN_B_SLUGS below if you discover more slugs.
    """
    suffix = {1: "st", 2: "nd", 3: "rd"}
    urls = []

    # Pattern A — meetings 1 through 60 (generous upper bound)
    for n in range(1, 61):
        suf   = suffix.get(n, "th")
        title = f"{n}{suf} SEC Meeting"
        url   = f"{BASE_URL}/sites/default/files/{n}{suf}%20SEC%20Meeting.pdf"
        urls.append({"url": url, "title": title, "source": "pattern-A"})

    # Pattern B — add known slugs here as you discover them
    PATTERN_B_SLUGS = [
        ("49th_sec_meeting_07_09_2023_0", "49th SEC Meeting (07 Sep 2023)"),
        # ("48th_sec_meeting_...", "48th SEC Meeting"),
    ]
    base_b = (
        f"{BASE_URL}/sites/default/files/swf_utility_folder/departments/"
        "asdma_revenue_uneecopscloud_com_oid_70/menu/document"
    )
    for slug, title in PATTERN_B_SLUGS:
        urls.append({
            "url":    f"{base_b}/{slug}.pdf",
            "title":  title,
            "source": "pattern-B",
        })

    return urls


def discover_all_pdfs(session):
    """
    Combine scraping + pattern generation, deduplicate by URL, and return
    a sorted list of {url, title, source} dicts.
    """
    scraped  = scrape_listing_page(session)
    patterns = build_pattern_urls()

    # Scraped results win; patterns fill the gaps
    seen = {item["url"] for item in scraped}
    for item in patterns:
        if item["url"] not in seen:
            scraped.append(item)
            seen.add(item["url"])

    # Sort by URL for a stable, predictable order
    scraped.sort(key=lambda x: x["url"])

    print(f"\n[discover] Total unique PDF candidates: {len(scraped)}")
    return scraped


# ── Step 2: Save the list ─────────────────────────────────────────────────────

def save_pdf_list(pdf_list, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["url", "title", "source"])
        writer.writeheader()
        writer.writerows(pdf_list)
    print(f"[list] PDF list saved → {path}  ({len(pdf_list)} entries)")


# ── Step 3: Download ──────────────────────────────────────────────────────────

def url_to_filename(url):
    """Derive a clean local filename from a URL."""
    name = unquote(os.path.basename(urlparse(url).path))
    name = re.sub(r"[^\w.\-]", "_", name)   # replace unsafe chars
    name = re.sub(r"_+", "_", name)          # collapse multiple underscores
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name


def already_downloaded(filename):
    """Return True if the file exists in PDF_DIR and is large enough to be real."""
    path = PDF_DIR / filename
    return path.exists() and path.stat().st_size >= MIN_PDF_BYTES


def normalize_basename(filename):
    """Strip trailing _N digit suffix so '10th_SEC_Meeting_0' == '10th_SEC_Meeting'."""
    stem = Path(filename).stem
    return re.sub(r'_\d+$', '', stem).lower()


def find_existing_similar(filename):
    """
    Return the path of any file in PDF_DIR whose normalised basename matches
    filename's normalised basename but whose name differs from filename, or None.
    """
    target = normalize_basename(filename)
    for existing in PDF_DIR.glob("*.pdf"):
        if existing.name != filename and normalize_basename(existing.name) == target:
            return existing
    return None


def get_remote_size(session, url):
    """Return Content-Length from a HEAD request, or None if unavailable."""
    try:
        resp = session.head(url, timeout=10, allow_redirects=True)
        length = resp.headers.get("Content-Length")
        return int(length) if length else None
    except Exception:
        return None


def download_one(session, url, dest_path):
    """
    Download a single PDF to dest_path.
    Returns (success: bool, message: str).
    """
    try:
        resp = session.get(url, timeout=30, stream=True)
        if resp.status_code != 200:
            return False, f"HTTP {resp.status_code}"

        content_type = resp.headers.get("Content-Type", "")
        if "html" in content_type and "pdf" not in content_type:
            # Server returned an HTML error page
            return False, "got HTML instead of PDF"

        with open(dest_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        size = dest_path.stat().st_size
        if size < MIN_PDF_BYTES:
            dest_path.unlink()
            return False, f"file too small ({size} bytes) — likely error page"

        return True, f"{size:,} bytes"

    except Exception as exc:
        if dest_path.exists():
            dest_path.unlink()
        return False, str(exc)


def download_all(session, pdf_list):
    """
    Download every PDF in pdf_list, skipping files already in PDF_DIR.
    Returns a list of log dicts.
    """
    log = []
    total  = len(pdf_list)
    skip   = sum(1 for item in pdf_list if already_downloaded(url_to_filename(item["url"])))

    print(f"\n[download] {total} candidates  |  {skip} already downloaded  |  {total - skip} to fetch\n")

    for i, item in enumerate(pdf_list, 1):
        url      = item["url"]
        title    = item["title"]
        filename = url_to_filename(url)
        dest     = PDF_DIR / filename

        prefix = f"  [{i:>3}/{total}]"

        if already_downloaded(filename):
            size = dest.stat().st_size
            print(f"{prefix} [SKIP] {filename}  ({size:,} bytes already on disk)")
            log.append({"filename": filename, "url": url, "title": title,
                        "status": "skipped", "detail": f"{size:,} bytes"})
            continue

        # Duplicate check: same normalised name, different filename
        similar = find_existing_similar(filename)
        if similar:
            existing_size = similar.stat().st_size
            remote_size   = get_remote_size(session, url)
            if remote_size is not None:
                diff = abs(remote_size - existing_size) / max(remote_size, existing_size)
                if diff <= DUPLICATE_SIZE_TOLERANCE:
                    print(f"{prefix} [DUP]  {filename}: duplicate of {similar.name} "
                          f"(sizes within {diff*100:.1f}% — skipping)")
                    log.append({"filename": filename, "url": url, "title": title,
                                "status": "duplicate",
                                "detail": f"duplicate of {similar.name}; "
                                          f"remote {remote_size:,} vs local {existing_size:,} bytes"})
                    continue
                else:
                    print(f"{prefix} [NEW]  {filename}: similar name to {similar.name} "
                          f"but sizes differ by {diff*100:.1f}% — downloading")

        ok, msg = download_one(session, url, dest)
        status  = "ok" if ok else "failed"
        symbol  = "✓" if ok else "✗"
        print(f"{prefix} [{symbol}]  {filename}: {msg}")
        log.append({"filename": filename, "url": url, "title": title,
                    "status": status, "detail": msg})

        if ok:
            time.sleep(POLITE_DELAY)   # only delay after successful fetches

    return log


def save_download_log(log, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["filename", "url", "title", "status", "detail"]
        )
        writer.writeheader()
        writer.writerows(log)
    print(f"\n[log] Download log saved → {path}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    list_only = "--list-only" in sys.argv

    session = requests.Session()
    session.headers.update(HEADERS)

    # 1. Discover
    pdf_list = discover_all_pdfs(session)

    # 2. Save master list
    save_pdf_list(pdf_list, DATA_DIR / "pdf_list.csv")

    if list_only:
        print("\n[done] --list-only mode. No files downloaded.")
        return

    # 3. Download (with skip logic)
    log = download_all(session, pdf_list)

    # 4. Save download log
    save_download_log(log, DATA_DIR / "pdf_index.csv")

    ok_count   = sum(1 for r in log if r["status"] == "ok")
    skip_count = sum(1 for r in log if r["status"] == "skipped")
    fail_count = sum(1 for r in log if r["status"] == "failed")

    print(f"""
[summary]
  Downloaded : {ok_count}
  Skipped    : {skip_count}  (already on disk)
  Failed     : {fail_count}
  PDFs saved : {PDF_DIR}
""")


if __name__ == "__main__":
    main()
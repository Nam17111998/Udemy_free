"""Generate static JSON with free Udemy coupon courses.

This script reuses the existing scrapers in ``udemy_enroller.scrapers``
to fetch coupon URLs and writes them to ``udemy_free/api/courses.json``.

Features:
- Collect coupon URLs from multiple sources.
- Keep history across runs, removing duplicate URLs.
- Newest links appear at the top of the list.
- When total courses >= 1000, drop 100 oldest entries (from the end).
- Enrich courses with title and image_url scraped from the Udemy page.

Intended usage:
  - Run locally:  ``python udemy_free/build_courses_json.py``
  - Run in CI / GitHub Actions on a schedule to keep the JSON fresh.
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup


# Ensure we import udemy_enroller from the repo, not from site-packages
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from udemy_enroller.scrapers.manager import ScraperManager


def _extract_coupon_code(url: str) -> Optional[str]:
    """Return the coupon code from a Udemy URL if present."""
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    coupon_values = query_params.get("couponCode") or query_params.get("couponcode")
    if coupon_values:
        return coupon_values[0]
    return None


async def _collect_courses(max_pages: Optional[int]) -> List[Dict]:
    """Use ScraperManager to collect unique coupon URLs."""
    manager = ScraperManager(
        idownloadcoupon_enabled=True,
        freebiesglobal_enabled=True,
        tutorialbar_enabled=True,
        discudemy_enabled=True,
        coursevania_enabled=True,
        max_pages=max_pages,
    )
    urls = await manager.run()
    unique_urls = sorted({u for u in urls if u})

    courses: List[Dict] = []
    for url in unique_urls:
        course: Dict[str, Optional[str]] = {"url": url}
        coupon_code = _extract_coupon_code(url)
        if coupon_code:
            course["coupon_code"] = coupon_code
        courses.append(course)
    return courses


def _load_existing_courses(path: Path) -> List[Dict]:
    """Load existing courses from JSON file, if it exists, preserving metadata."""
    if not path.is_file():
        return []

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    courses = data.get("courses") or []
    if not isinstance(courses, list):
        return []

    cleaned: List[Dict] = []
    seen_urls = set()
    for item in courses:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        cleaned.append(item)
    return cleaned


def _merge_courses(existing: List[Dict], scraped: List[Dict]) -> List[Dict]:
    """
    Merge existing and scraped course lists:
    - No duplicate URLs.
    - Preserve metadata (title, image_url, ...) from existing entries if present.
    - Update coupon_code from scraped entries when available.
    - Order: scraped URLs first (newest), then URLs only found in existing.
    - If total >= 1000, drop 100 oldest entries (from the end).
    """
    url_to_course: Dict[str, Dict] = {}

    # Start from existing data so we keep metadata
    for item in existing:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not url:
            continue
        url_to_course[url] = dict(item)

    ordered_urls: List[str] = []
    seen_urls = set()

    # Scraped URLs come first; update coupon_code if needed
    for item in scraped:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        ordered_urls.append(url)

        if url in url_to_course:
            # Update coupon_code, keep other fields (title, image_url, ...)
            if "coupon_code" in item and item["coupon_code"]:
                url_to_course[url]["coupon_code"] = item["coupon_code"]
        else:
            url_to_course[url] = dict(item)

    # Now append any URLs only present in existing
    for item in existing:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        ordered_urls.append(url)
        if url not in url_to_course:
            url_to_course[url] = dict(item)

    combined = [url_to_course[url] for url in ordered_urls]

    max_total = 1000
    drop_batch = 100
    if len(combined) >= max_total and len(combined) > drop_batch:
        # Drop 100 oldest courses (from the end)
        combined = combined[:-drop_batch]

    return combined


def _enrich_courses_with_meta(courses: List[Dict]) -> None:
    """
    Enrich courses with metadata from Udemy landing pages:
    - title: from meta og:title
    - image_url: from meta og:image

    Only fetch for courses missing these fields to avoid unnecessary requests.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    for course in courses:
        if not isinstance(course, dict):
            continue
        url = course.get("url")
        if not url:
            continue

        # Skip if we already have both fields
        if course.get("image_url") and course.get("title"):
            continue

        # Strip query string when fetching to avoid extra redirects
        try:
            parsed = urlparse(url)
            fetch_url = parsed._replace(query="").geturl()
        except Exception:
            fetch_url = url

        try:
            resp = requests.get(fetch_url, headers=headers, timeout=15)
            resp.raise_for_status()
        except Exception:
            continue

        try:
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception:
            continue

        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            course["image_url"] = og_image.get("content")

        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            course["title"] = og_title.get("content")


def main() -> None:
    """Entry point used by GitHub Actions and local runs."""
    max_pages_env = os.getenv("UDEMY_FREE_MAX_PAGES")
    max_pages: Optional[int] = None
    if max_pages_env:
        try:
            max_pages = int(max_pages_env)
        except ValueError:
            max_pages = None

    output_dir = Path(__file__).resolve().parent / "api"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "courses.json"

    # Collect freshly scraped courses
    scraped_courses = asyncio.run(_collect_courses(max_pages=max_pages))

    # Load previous data to keep history and metadata
    existing_courses = _load_existing_courses(output_file)

    # Merge: newest (scraped) first, older below, no duplicate URLs
    merged_courses = _merge_courses(existing_courses, scraped_courses)

    # Enrich all courses that still lack metadata
    if merged_courses:
        to_enrich = [
            c
            for c in merged_courses
            if isinstance(c, dict)
            and (not c.get("image_url") or not c.get("title"))
        ]
        if to_enrich:
            _enrich_courses_with_meta(to_enrich)

    payload: Dict = {
        "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "count": len(merged_courses),
        "courses": merged_courses,
    }

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()


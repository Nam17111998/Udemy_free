"""Generate static JSON with free Udemy coupon courses.

This script reuses the existing scrapers in ``udemy_enroller.scrapers``
to fetch coupon URLs and writes them to ``udemy_free/api/courses.json``.

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

# Bảo đảm ưu tiên dùng package udemy_enroller trong repo hiện tại
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


def main() -> None:
    """Entry point used by GitHub Actions and local runs."""
    max_pages_env = os.getenv("UDEMY_FREE_MAX_PAGES")
    max_pages: Optional[int] = None
    if max_pages_env:
        try:
            max_pages = int(max_pages_env)
        except ValueError:
            max_pages = None

    courses = asyncio.run(_collect_courses(max_pages=max_pages))

    output_dir = Path(__file__).resolve().parent / "api"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "courses.json"

    payload: Dict = {
        "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "count": len(courses),
        "courses": courses,
    }

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()

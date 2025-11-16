"""Generate static JSON with free Udemy coupon courses.

This script reuses the existing scrapers in ``udemy_enroller.scrapers``
to fetch coupon URLs and writes them to ``udemy_free/api/courses.json``.

Tính năng:
- Lấy các link coupon Udemy từ nhiều nguồn.
- Giữ lại lịch sử các lần crawl, lọc bỏ URL trùng.
- Danh sách mới nhất luôn nằm ở đầu (mới → cũ).
- Khi tổng số khóa học >= 1000 thì tự động xóa 100 khóa cũ nhất ở cuối danh sách.
- Bổ sung thêm thông tin ảnh và tiêu đề khóa học (nếu lấy được từ trang Udemy).

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


def _load_existing_courses(path: Path) -> List[Dict]:
    """Load existing courses from JSON file, if it exists."""
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


def _merge_courses(existing: List[Dict], new: List[Dict]) -> List[Dict]:
    """
    Merge danh sách cũ và mới với các quy tắc:
    - Không thêm trùng URL.
    - Các link mới nhất (vừa scrape) được xếp lên đầu.
    - Khi tổng số phần tử >= 1000 thì xoá 100 link cũ nhất (ở cuối danh sách).
    """
    existing_urls = set()
    combined: List[Dict] = []

    # Thêm các link mới không trùng URL lên đầu (ưu tiên mới trước)
    for item in new:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not url or url in existing_urls:
            continue
        existing_urls.add(url)
        combined.append(item)

    # Sau đó thêm các link cũ còn lại (không trùng)
    for item in existing:
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not url or url in existing_urls:
            continue
        existing_urls.add(url)
        combined.append(item)

    max_total = 1000
    drop_batch = 100
    if len(combined) >= max_total and len(combined) > drop_batch:
        # Xoá 100 link cũ nhất (cuối danh sách)
        combined = combined[:-drop_batch]

    return combined


def _enrich_new_courses_with_meta(courses: List[Dict]) -> None:
    """
    Bổ sung thêm thông tin từ trang Udemy:
    - title: lấy từ meta og:title
    - image_url: lấy từ meta og:image

    Chỉ áp dụng cho danh sách khóa học mới (đã lọc không trùng URL).
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    for course in courses:
        url = course.get("url")
        if not url:
            continue

        # Loại bỏ query khi fetch để tránh redirect lặp lại
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

        # Ảnh khóa học
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            course["image_url"] = og_image.get("content")

        # Tiêu đề khóa học
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

    # Lấy danh sách vừa scrape
    scraped_courses = asyncio.run(_collect_courses(max_pages=max_pages))

    # Load dữ liệu cũ để giữ lịch sử và tránh trùng URL
    existing_courses = _load_existing_courses(output_file)
    existing_urls = {
        c.get("url")
        for c in existing_courses
        if isinstance(c, dict) and c.get("url")
    }

    # Chỉ giữ những khóa mới chưa từng xuất hiện (theo URL)
    new_courses = [
        c
        for c in scraped_courses
        if isinstance(c, dict) and c.get("url") and c.get("url") not in existing_urls
    ]

    # Bổ sung title và image_url cho các khóa mới (nếu lấy được)
    if new_courses:
        _enrich_new_courses_with_meta(new_courses)

    # Trộn lại: mới ở trên, cũ ở dưới, lọc trùng, giới hạn tổng ~1000 và xoá 100 cũ nhất
    merged_courses = _merge_courses(existing_courses, new_courses)

    payload: Dict = {
        "updated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "count": len(merged_courses),
        "courses": merged_courses,
    }

    with output_file.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()


import json
import re
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.justwatch.com"
URL = "https://www.justwatch.com/in?sort_by=popular"
OUTPUT_FILE = "ott_popular.json"

TARGET_PROVIDERS = {
    "Amazon Prime",
    "SonyLIV",
    "Zee5",
    "JioHotstar",
}


def normalize_provider(text: str) -> str:
    value = re.sub(r"\s+", " ", text.strip().lower())

    if "amazon" in value and "prime" in value:
        return "Amazon Prime"
    if "sony" in value and ("liv" in value or "l i v" in value):
        return "SonyLIV"
    if "zee5" in value or "zee 5" in value:
        return "Zee5"
    if "hotstar" in value or ("jio" in value and "hotstar" in value):
        return "JioHotstar"
    return ""


def absolute_url(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if not href.startswith("/"):
        href = "/" + href
    return BASE_URL + href


def get_image_url(container) -> str:
    img = container.select_one("img.picture-comp__img, img")
    if img:
        for key in ("src", "data-src", "data-srcset", "srcset"):
            value = (img.get(key) or "").strip()
            if value:
                return value.split(",")[0].strip().split(" ")[0].strip()

    source = container.select_one("source[data-srcset], source[srcset]")
    if source:
        value = (source.get("data-srcset") or source.get("srcset") or "").strip()
        if value:
            return value.split(",")[0].strip().split(" ")[0].strip()

    return ""


def extract_provider_from_title_page(soup: BeautifulSoup) -> str:
    """
    Provider icon learning note:
    Open any title page in DevTools and inspect the provider logo images in the
    watch/offers area. The provider name is usually stored in `alt`, `title`,
    or `aria-label`. We scan those attributes and normalize.
    """
    for el in soup.select("img, [aria-label], [title]"):
        for text in (el.get("alt", ""), el.get("title", ""), el.get("aria-label", "")):
            provider = normalize_provider(text)
            if provider in TARGET_PROVIDERS:
                return provider
    return ""


def scrape_popular(limit: int = 10) -> List[Dict[str, str]]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "mr-IN,mr,en-US,en;q=0.9",
    }

    listing = requests.get(URL, headers=headers, timeout=20)
    listing.raise_for_status()
    soup = BeautifulSoup(listing.text, "html.parser")

    # IMPORTANT:
    # This page is already sorted by popularity for India.
    # We MUST keep that ordering and only filter out titles that aren't on the target OTTs.
    results: List[Dict[str, str]] = []
    seen = set()

    for card in soup.select(".title-list-grid__item")[:120]:
        link = card.select_one("a.title-list-grid__item--link, a[href]")
        if not link:
            continue

        href = (link.get("href") or "").strip()
        if not href:
            continue

        title = (card.get("data-title") or "").strip()
        if not title:
            img = card.select_one("img")
            title = ((img.get("alt") or "") if img else "").strip()

        image = get_image_url(card)
        if not title or not image:
            continue

        # Provider is not reliably visible in the grid HTML, so we check the title page.
        # We do NOT reshuffle results; we keep the first N matches in popularity order.
        detail = requests.get(absolute_url(href), headers=headers, timeout=20)
        if detail.status_code != 200:
            continue
        provider = extract_provider_from_title_page(BeautifulSoup(detail.text, "html.parser"))
        if provider not in TARGET_PROVIDERS:
            continue

        key = (title.lower(), provider.lower())
        if key in seen:
            continue
        seen.add(key)
        results.append({"title": title, "image": image, "provider": provider})

        if len(results) >= limit:
            break

    return results


def main():
    items = scrape_popular(limit=10)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(items)} items to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()


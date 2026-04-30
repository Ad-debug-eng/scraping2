import json
import re
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup


URL = "https://www.justwatch.com/in/new"
OUTPUT_FILE = "ott_updates.json"

# Only keep releases from these providers.
TARGET_PROVIDERS = {
    "amazon prime video": "Amazon Prime",
    "sony liv": "SonyLIV",
    "zee5": "Zee5",
}


def normalize_provider(text: str) -> str:
    """Normalize icon alt/title text to one of our target provider names."""
    value = re.sub(r"\s+", " ", text.strip().lower())

    # Match common variants that appear in provider icon alt/title attributes.
    if "amazon" in value and "prime" in value:
        return "Amazon Prime"
    if "sony" in value and ("liv" in value or "l i v" in value):
        return "SonyLIV"
    if "zee5" in value or "zee 5" in value:
        return "Zee5"

    return ""


def extract_provider(item) -> str:
    """
    Extract provider from icon metadata.

    Learning note:
    In browser devtools, inspect one card under either `.title-list-grid__item`
    (grid layout) or one `.timeline__provider-block` (timeline layout).
    Provider logos are usually `<img>` tags near the title card. The provider
    name is commonly stored in attributes like:
    - alt="Amazon Prime Video"
    - title="Watch on Zee5"
    - aria-label="SonyLIV"
    So we inspect these attributes first, then normalize text to known providers.
    """
    # Collect candidate provider/logo elements in the current container.
    icon_elements = item.select("img, [aria-label], [title]")

    for icon in icon_elements:
        candidates = [
            icon.get("alt", ""),
            icon.get("title", ""),
            icon.get("aria-label", ""),
        ]

        for text in candidates:
            provider = normalize_provider(text)
            if provider:
                return provider

    return ""


def get_image_url(container) -> str:
    """Extract poster URL from img/srcset/data-srcset fields."""
    img_tag = container.select_one("img.picture-comp__img, img.title-poster__image, img")
    if img_tag:
        for key in ("src", "data-src", "data-srcset", "srcset"):
            value = (img_tag.get(key) or "").strip()
            if value:
                return value.split(",")[0].strip().split(" ")[0].strip()

    source_tag = container.select_one("source[data-srcset], source[srcset]")
    if source_tag:
        value = (source_tag.get("data-srcset") or source_tag.get("srcset") or "").strip()
        if value:
            return value.split(",")[0].strip().split(" ")[0].strip()

    return ""


def extract_title(item) -> str:
    """Extract title from anchor title, poster img alt, or visible text."""
    img_tag = item.select_one("img")
    if img_tag:
        alt_text = (img_tag.get("alt") or "").strip()
        if alt_text:
            # Often looks like "Title - Season 1"; keep only the main title.
            return alt_text.split(" - ")[0].strip()

    link = item.select_one("a")
    if link:
        href = (link.get("href") or "").strip()
        if href:
            slug = href.rstrip("/").split("/")[-1].replace("-", " ").strip()
            if slug and slug not in {"new", "in"} and not slug.startswith("season "):
                return slug.title()

    text = item.get_text(" ", strip=True)
    return text[:120].strip()


def parse_timeline_layout(soup) -> List[Dict[str, str]]:
    """Parse timeline provider blocks used on current JustWatch 'new' page."""
    results: List[Dict[str, str]] = []

    provider_blocks = soup.select(".timeline__provider-block")
    for block in provider_blocks:
        provider = extract_provider(block)
        if provider not in TARGET_PROVIDERS.values():
            continue

        for item in block.select(".horizontal-title-list__item"):
            title = extract_title(item)
            image_url = get_image_url(item)
            if title and image_url:
                results.append({"title": title, "image": image_url, "provider": provider})

    return results


def parse_grid_layout(soup) -> List[Dict[str, str]]:
    """Fallback parser for older/new timeline grid cards."""
    results: List[Dict[str, str]] = []
    items = soup.select(".title-list-grid__item")

    for item in items:
        title = extract_title(item)
        image_url = get_image_url(item)
        provider = extract_provider(item)
        if provider in TARGET_PROVIDERS.values() and title and image_url:
            results.append({"title": title, "image": image_url, "provider": provider})

    return results


def dedupe_items(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    deduped: List[Dict[str, str]] = []
    for item in items:
        key = (item["title"].lower(), item["provider"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def scrape_latest_releases() -> List[Dict[str, str]]:
    headers = {
        # Realistic browser UA helps avoid bot blocking.
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    response = requests.get(URL, headers=headers, timeout=20)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Try current timeline layout first, then fallback to older grid layout.
    timeline_items = parse_timeline_layout(soup)
    if timeline_items:
        return dedupe_items(timeline_items)

    grid_items = parse_grid_layout(soup)
    return dedupe_items(grid_items)


def main():
    updates = scrape_latest_releases()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(updates, file, indent=2, ensure_ascii=False)
    print(f"Saved {len(updates)} items to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

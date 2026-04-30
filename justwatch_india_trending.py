import json
import re
from typing import List, Dict, Optional, Tuple

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.justwatch.com"
URL = "https://www.justwatch.com/in?sort_by=trending"
OUTPUT_FILE = "ott_trending.json"

# Target OTTs for India trending.
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

    # Common variants for JioHotstar / Hotstar / Disney+ Hotstar.
    if "hotstar" in value or ("jio" in value and "hotstar" in value):
        return "JioHotstar"

    return ""


def extract_provider_from_page(soup: BeautifulSoup) -> str:
    """
    Learning note (provider icons):
    Provider logos are usually `<img>` tags inside the "where to watch"/offers area.
    In DevTools, open a title page (e.g., `/in/movie/...`) and inspect the provider
    logo image. The provider name is commonly stored in:
    - `alt="Amazon Prime Video"`
    - `title="Zee5"`
    - `aria-label="SonyLIV"`
    So we scan `<img>` and any element with `aria-label`/`title` attributes and
    normalize the text.
    """
    candidates = []
    for el in soup.select("img, [aria-label], [title]"):
        candidates.extend(
            [
                el.get("alt", ""),
                el.get("title", ""),
                el.get("aria-label", ""),
            ]
        )

    for text in candidates:
        provider = normalize_provider(text)
        if provider in TARGET_PROVIDERS:
            return provider

    return ""


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


def is_cricket_related(title: str, soup: Optional[BeautifulSoup] = None) -> bool:
    t = (title or "").strip().lower()
    if "cricket" in t or "ipl" in t:
        return True
    if soup:
        page_text = soup.get_text(" ", strip=True).lower()
        if "cricket" in page_text and ("match" in page_text or "live" in page_text):
            return True
    return False


def absolute_url(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if not href.startswith("/"):
        href = "/" + href
    return BASE_URL + href


def scrape_trending(limit: int = 8) -> List[Dict[str, str]]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        # Include Marathi as a preference, while still accepting English.
        "Accept-Language": "mr-IN,mr,en-US,en;q=0.9",
    }

    listing = requests.get(URL, headers=headers, timeout=20)
    listing.raise_for_status()
    listing_soup = BeautifulSoup(listing.text, "html.parser")

    cards = listing_soup.select(".title-list-grid__item")[:40]
    results: List[Dict[str, str]] = []
    cricket_candidate: Optional[Dict[str, str]] = None

    for card in cards:
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

        image_url = get_image_url(card)
        if not title or not image_url:
            continue

        title_url = absolute_url(href)

        # Provider icons are more reliably present on the title page than in the trending grid.
        detail = requests.get(title_url, headers=headers, timeout=20)
        if detail.status_code != 200:
            continue
        detail_soup = BeautifulSoup(detail.text, "html.parser")

        provider = extract_provider_from_page(detail_soup)
        if provider and provider in TARGET_PROVIDERS:
            item = {"title": title, "image": image_url, "provider": provider}

            # If cricket is trending, we’ll try to include it (even if it bumps the last item).
            if is_cricket_related(title, detail_soup):
                cricket_candidate = item
            else:
                results.append(item)

        if len(results) >= limit:
            break

    if cricket_candidate and all(
        (x["title"].lower(), x["provider"].lower())
        != (cricket_candidate["title"].lower(), cricket_candidate["provider"].lower())
        for x in results
    ):
        if len(results) < limit:
            results.append(cricket_candidate)
        else:
            results[-1] = cricket_candidate

    # De-dupe in case the same title appears twice.
    seen = set()
    deduped: List[Dict[str, str]] = []
    for item in results:
        key = (item["title"].lower(), item["provider"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped[:limit]


def main():
    items = scrape_trending(limit=10)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(items)} items to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()


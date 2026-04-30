import json
import re
from typing import List, Dict, Tuple

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.justwatch.com"
OUTPUT_FILE = "live_tv.json"

# These are JustWatch provider pages for India.
PROVIDER_PAGES: List[Tuple[str, str]] = [
    ("Zee5", "https://www.justwatch.com/in/provider/zee5"),
    ("SonyLIV", "https://www.justwatch.com/in/provider/sony-liv"),
    ("JioHotstar", "https://www.justwatch.com/in/provider/hotstar"),
    ("Amazon Prime", "https://www.justwatch.com/in/provider/amazon-prime-video"),
]


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


def clean_title(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def scrape_provider_titles(provider_name: str, url: str, headers: dict, max_items: int) -> List[Dict[str, str]]:
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, "html.parser")

    items: List[Dict[str, str]] = []
    for card in soup.select(".title-list-grid__item"):
        title = clean_title(card.get("data-title") or "")
        if not title:
            img = card.select_one("img")
            title = clean_title((img.get("alt") or "") if img else "")

        image = get_image_url(card)
        if title and image:
            items.append({"title": title, "image": image, "provider": provider_name})

        if len(items) >= max_items:
            break

    return items


def main():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "mr-IN,mr,en-US,en;q=0.9",
    }

    results: List[Dict[str, str]] = []
    per_provider = 10

    for provider_name, url in PROVIDER_PAGES:
        results.extend(scrape_provider_titles(provider_name, url, headers, max_items=per_provider))

    # Keep only 10 total, de-duped by title+provider.
    seen = set()
    deduped: List[Dict[str, str]] = []
    for item in results:
        key = (item["title"].lower(), item["provider"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    final = deduped[:10]
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    print(f"Saved {len(final)} items to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()


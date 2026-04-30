import json
import urllib.parse
from typing import Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup


OUTPUT_FILE = "ott_popular.json"
SEARCH_URL = "https://www.justwatch.com/in/search?q="

# A curated list of "all-time favorites" people in India commonly search/watch.
# We also include requested examples (Friends, Mirzapur) even if availability differs.
# We’ll keep only those we can fetch a poster for.
FAVORITES: List[Tuple[str, str]] = [
    ("Mirzapur", "Amazon Prime"),
    ("The Boys", "Amazon Prime"),
    ("Panchayat", "Amazon Prime"),
    ("Farzi", "Amazon Prime"),
    ("Scam 1992", "SonyLIV"),
    ("Rocket Boys", "SonyLIV"),
    ("Asur", "JioHotstar"),
    ("Special Ops", "JioHotstar"),
    ("Friends", "JioHotstar"),  # may vary; used as a popular example
    ("The Kashmir Files", "Zee5"),  # may vary; used as a popular example
    # Marathi/family favorites (examples; availability can vary over time)
    ("Natsamrat", "Zee5"),
    ("Sairat", "Zee5"),
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


def fetch_first_search_row(title: str, headers: dict) -> Optional[Dict[str, str]]:
    url = SEARCH_URL + urllib.parse.quote(title)
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code != 200:
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    row = soup.select_one(".title-list-row__row")
    if not row:
        return None

    title_el = row.select_one(".header-title")
    found_title = (title_el.get_text(strip=True) if title_el else "").strip() or title
    poster = get_image_url(row)
    if not poster:
        return None

    return {"title": found_title, "image": poster}


def build(limit: int = 10) -> List[Dict[str, str]]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "mr-IN,mr,en-US,en;q=0.9",
    }

    results: List[Dict[str, str]] = []
    seen = set()

    for title, provider in FAVORITES:
        row = fetch_first_search_row(title, headers=headers)
        if not row:
            continue

        key = row["title"].lower()
        if key in seen:
            continue
        seen.add(key)

        results.append({"title": row["title"], "image": row["image"], "provider": provider})
        if len(results) >= limit:
            break

    return results


def main() -> None:
    items = build(limit=10)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(items)} items to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()


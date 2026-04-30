import json
from typing import List, Dict, Tuple

import requests
from bs4 import BeautifulSoup


OUTPUT_FILE = "ott_popular.json"

IMDB_PROVIDER_NAME = "IMDb"


def fetch_imdb_chart(url: str, headers: dict, limit: int = 100) -> List[Tuple[str, str]]:
    """
    Fetch (title, poster_url) from an IMDb chart page.
    """
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    items: List[Tuple[str, str]] = []

    # IMDb chart rows: posters are in <img>, and titles are in links to /title/tt...
    for row in soup.select("li.ipc-metadata-list-summary-item, tr"):
        a = row.select_one('a[href^="/title/"]')
        img = row.select_one("img")
        if not a:
            continue
        title = (a.get_text(strip=True) or "").strip()
        if not title or title.isdigit():
            continue
        poster = (img.get("src") or "").strip() if img else ""
        if title and poster:
            items.append((title, poster))
        if len(items) >= limit:
            break

    # Fallback (older layout): any /title/ link + nearest image
    if not items:
        for a in soup.select('a[href^="/title/"]'):
            title = (a.get_text(strip=True) or "").strip()
            if not title or title.isdigit():
                continue
            img = a.find_previous("img") or a.find_next("img")
            poster = (img.get("src") or "").strip() if img else ""
            if poster:
                items.append((title, poster))
            if len(items) >= limit:
                break

    return items


def build_all_time_favorites(limit: int = 10) -> List[Dict[str, str]]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    movies = fetch_imdb_chart("https://www.imdb.com/chart/top/", headers=headers, limit=80)
    tv = fetch_imdb_chart("https://www.imdb.com/chart/toptv/", headers=headers, limit=80)

    # Interleave movie + TV so the row feels varied.
    results: List[Dict[str, str]] = []
    seen = set()
    i = 0
    while len(results) < limit and (i < len(movies) or i < len(tv)):
        for pool in (movies, tv):
            if i >= len(pool):
                continue
            title, poster = pool[i]
            key = title.lower()
            if key in seen:
                continue
            seen.add(key)
            results.append({"title": title, "image": poster, "provider": IMDB_PROVIDER_NAME})
            if len(results) >= limit:
                break
        i += 1

    return results


def main():
    items = build_all_time_favorites(limit=10)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    print(f"Saved {len(items)} items to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()


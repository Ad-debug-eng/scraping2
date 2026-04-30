# India OTT Posters (JustWatch)

This project shows **two continuously-scrolling poster rows** on a simple website:

- **Trending in India** (10 posters) → generated into `ott_trending.json`
- **Most popular (all‑time favorites)** (10 posters) → generated into `ott_popular.json`

The UI is a static site (`index.html`, `styles.css`, `app.js`) that loads the JSON files.

## Run locally

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Generate data:

```bash
python justwatch_india_trending.py
python all_time_favorites_ott.py
```

Serve the site:

```bash
python -m http.server 8000
```

Open:

- `http://127.0.0.1:8000/index.html`

## Free hosting + auto-updates (GitHub Pages)

You can host the site **for free** on **GitHub Pages** and auto-update the JSON daily/weekly using **GitHub Actions scheduled workflows**.

High level:

1. Create a GitHub repo and push this folder.
2. Enable GitHub Pages (Settings → Pages → Deploy from branch).
3. Enable Actions (repo → Actions tab).
4. The scheduled workflow will run the Python scripts, update the JSON, and commit changes automatically.

## Notes / reliability

- JustWatch pages and HTML can change; scraping can break and may be rate-limited.
- Keep requests gentle (don’t run too frequently).
- If a provider/title becomes unavailable, it may disappear from JSON outputs.


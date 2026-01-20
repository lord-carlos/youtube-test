Purpose
-------
This repository is a small Python CLI that reads your YouTube "Liked" playlist and attempts to find matching tracks on Bandcamp.

Quick facts
- **Entry point:** `main.py`
- **Run:** use the project's `uv` wrapper (see README.md). Example: `uv sync` then `uv run python .\main.py --cookie cookies.txt "Artist Channel"`
- **Language:** Python >=3.12
- **Dependencies:** listed in `pyproject.toml` (notably `yt-dlp`, `httpx[http2]`, `beautifulsoup4`).

High-level architecture
- Single-process CLI pipeline in `main.py`.
- Major functions:
  - `fetch_likes(limit, browser=None, cookiefile=None)` — uses `yt_dlp` to extract the YouTube "Liked videos" playlist (playlist id `LL`) with `extract_flat=True` so no downloads occur.
  - `filter_by_channels(likes, channels)` — simple casefold exact-match filter on uploader names.
  - `bandcamp_search(query)` — performs an HTTP GET via `httpx` and parses Bandcamp search results with `BeautifulSoup`.
  - `score_match(youtube_title, bc_match)` — fuzzy matching using `difflib.SequenceMatcher`.

Developer workflows
- Install deps: `uv sync`
- Run CLI examples (cookie file):
```
uv run python .\main.py --cookie cookies.txt "Artist Channel"
```

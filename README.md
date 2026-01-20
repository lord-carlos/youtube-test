yt-like-bc
===========

A small CLI tool that lists your most recent YouTube "Liked" videos and attempts to find them on Bandcamp.

Features
- Read liked videos from your YouTube "Liked videos" playlist (via `yt-dlp`).
- Filter likes by channel name(s).
- Search Bandcamp for matching tracks and score fuzzy title/artist matches.
- Supports using browser cookies (via `--browser`) or a cookie file (via `--cookie`).

Quick start

1. Install dependencies (uses the project's `uv` wrapper):

```powershell
uv sync
```

2. Run (examples):

- Use a cookie file exported to `cookies.txt`:

```powershell
uv run python .\main.py --cookie cookies.txt "Artist Channel"
```

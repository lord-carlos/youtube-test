#!/usr/bin/env python3
import argparse
import sys
import textwrap
import urllib.parse
from difflib import SequenceMatcher
import os
import webbrowser
import html as _html

import httpx
import yt_dlp
from bs4 import BeautifulSoup


def parse_args():
    parser = argparse.ArgumentParser(
        description="List recently liked YouTube videos from specific channels and optionally search them on Bandcamp.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Examples:
              foo.py "Linus Tech Tips"
              foo.py --limit 50 --browser firefox "JAKE JEFFERY"
              foo.py --cookie cookies.txt --limit 50 "Artist Channel"
              foo.py --match-threshold 0.8 --browser chrome "Artist Channel"
            """
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Number of recent likes to inspect (default: 20).",
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--browser",
        type=str,
        default="chrome",
        help="Browser name for yt-dlp cookiesfrombrowser (e.g., chrome|firefox|edge|safari|brave...).",
    )
    group.add_argument(
        "--cookie",
        type=str,
        default=None,
        help="Path to a yt-dlp cookie file (mutually exclusive with --browser).",
    )

    parser.add_argument(
        "--match-threshold",
        type=float,
        default=0.75,
        help="Fuzzy match threshold for Bandcamp top result (0-1, default: 0.75).",
    )
    parser.add_argument(
        "channels",
        nargs="+",
        help="Channel names to filter (case-insensitive exact match).",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Write a static results.html file and open it in the default browser.",
    )
    return parser.parse_args()


def fetch_likes(limit, browser=None, cookiefile=None):
    # Fetch liked videos via YouTube "Liked videos" playlist (LL).
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": True,
        "playlistend": limit,
    }
    if cookiefile:
        ydl_opts["cookiefile"] = cookiefile
    elif browser:
        ydl_opts["cookiesfrombrowser"] = (browser, None, None, None)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info("https://www.youtube.com/playlist?list=LL", download=False)
    entries = info.get("entries") or []
    likes = []
    for e in entries:
        title = e.get("title") or ""
        uploader = e.get("uploader") or ""
        url = e.get("url") or e.get("webpage_url")
        likes.append({"title": title, "uploader": uploader, "url": url})
    return likes


def filter_by_channels(likes, channels):
    chan_set = {c.casefold(): c for c in channels}
    filtered = []
    for item in likes:
        uploader = item["uploader"]
        if uploader and uploader.casefold() in chan_set:
            filtered.append(item)
    return filtered


def prompt_yes_no(msg):
    while True:
        resp = input(f"{msg} [y/n]: ").strip().lower()
        if resp in ("y", "yes"):
            return True
        if resp in ("n", "no"):
            return False
        print("Please enter y or n.")


def dash_stripped(text):
    return text.replace("-", " ").strip()


def bandcamp_search(query):
    url = f"https://bandcamp.com/search?q={urllib.parse.quote_plus(query)}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://bandcamp.com/",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    }
    try:
        with httpx.Client(http2=True, timeout=10.0) as client:
            r = client.get(url, headers=headers)
            r.raise_for_status()
            text = r.text
    except Exception as exc:
        return {"ok": False, "error": str(exc), "url": url}

    soup = BeautifulSoup(text, "html.parser")
    first = soup.select_one("li.searchresult")
    if not first:
        return {"ok": True, "match": None, "url": url}

    link = first.select_one("a")
    title_el = first.select_one(".heading")
    artist_el = first.select_one(".subhead")
    match = {
        "title": title_el.get_text(strip=True) if title_el else "",
        "artist": artist_el.get_text(strip=True) if artist_el else "",
        "url": urllib.parse.urljoin("https://bandcamp.com", link["href"]) if link and link.has_attr("href") else url,
    }
    return {"ok": True, "match": match, "url": url}


def score_match(youtube_title, bc_match):
    if not bc_match:
        return 0.0
    a = youtube_title.casefold()
    b = f"{bc_match.get('artist','')} {bc_match.get('title','')}".strip().casefold()
    return SequenceMatcher(None, a, b).ratio()


def main():
    args = parse_args()

    cookiefile = None
    if getattr(args, "cookie", None):
        cookiefile_candidate = os.path.expanduser(args.cookie)
        if not os.path.isfile(cookiefile_candidate):
            print(f"Cookie file not found: {args.cookie}", file=sys.stderr)
            sys.exit(1)
        cookiefile = cookiefile_candidate

    try:
        likes = fetch_likes(args.limit, args.browser, cookiefile)
    except Exception as exc:
        print(f"Failed to fetch likes via yt-dlp: {exc}", file=sys.stderr)
        sys.exit(1)

    filtered = filter_by_channels(likes, args.channels)

    if not filtered:
        print("No liked videos from the specified channels found.")
        return

    print("Matched liked videos (titles only):")
    for i, item in enumerate(filtered, 1):
        print(f"{i}. {item['title']}")

    if not prompt_yes_no("Proceed to search these on Bandcamp?"):
        return

    print("\nBandcamp search results:")
    results = []
    for item in filtered:
        raw_title = item["title"]
        query = dash_stripped(raw_title)
        result = bandcamp_search(query)

        if not result.get("ok"):
            print(f"- {raw_title}: error searching Bandcamp ({result.get('error')}); search URL: {result.get('url')}")
            results.append({
                "uploader": item.get("uploader"),
                "bc_title": None,
                "score": 0.0,
                "bc_url": result.get("url"),
                "yt_url": item.get("url"),
            })
            continue

        match = result.get("match")
        if not match:
            print(f"- {raw_title}: no results; search URL: {result.get('url')}")
            results.append({
                "uploader": item.get("uploader"),
                "bc_title": None,
                "score": 0.0,
                "bc_url": result.get("url"),
                "yt_url": item.get("url"),
            })
            continue

        score = score_match(raw_title, match)
        if score >= args.match_threshold:
            print(f"- {raw_title}: MATCH {score:.2f} -> {match['title']} — {match['artist']} ({match['url']})")
            results.append({
                "uploader": item.get("uploader"),
                "bc_title": match.get("title"),
                "score": score,
                "bc_url": match.get("url"),
                "yt_url": item.get("url"),
            })
        else:
            print(f"- {raw_title}: below threshold (score {score:.2f}); search URL: {result.get('url')}")
            results.append({
                "uploader": item.get("uploader"),
                "bc_title": match.get("title"),
                "score": score,
                "bc_url": match.get("url"),
                "yt_url": item.get("url"),
            })

    if getattr(args, "html", False):
        try:
            render_html(results)
            abspath = os.path.abspath("results.html")
            webbrowser.open_new_tab(f"file://{abspath}")
        except Exception as exc:
            print(f"Failed to write or open results.html: {exc}", file=sys.stderr)


def render_html(results):
    # Simple self-contained HTML with embedded CSS. Row color derived from score (0.0 -> red, 1.0 -> green).
    def hue_for_score(score: float) -> int:
        try:
            s = float(score)
        except Exception:
            s = 0.0
        s = max(0.0, min(1.0, s))
        return int(120 * s)

    html_parts = []
    html_parts.append("<!doctype html>")
    html_parts.append("<html lang=\"en\">")
    html_parts.append("<head>")
    html_parts.append("<meta charset=\"utf-8\">")
    html_parts.append("<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">")
    html_parts.append("<title>Bandcamp matches</title>")
    html_parts.append("<style>")
    html_parts.append("body{font-family:Inter, system-ui, Arial, sans-serif; margin:24px; background:#f7fafc; color:#0f172a}")
    html_parts.append("h1{font-size:20px;margin-bottom:8px}")
    html_parts.append("table{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 6px 18px rgba(15,23,42,0.08)}")
    html_parts.append("thead th{background:#0f172a;color:#fff;padding:12px 16px;text-align:left;font-weight:600}")
    html_parts.append("tbody td{padding:0;border-top:1px solid #eef2f7}")
    html_parts.append("tr.clickable{cursor:pointer}")
    html_parts.append("tr.clickable:hover .row-link{background:linear-gradient(90deg, rgba(15,23,42,0.03), transparent)}")
    html_parts.append(".row-link{display:block;color:inherit;text-decoration:none;padding:12px 16px}")
    html_parts.append(".cell-inner{display:flex;align-items:center;gap:8px}")
    html_parts.append(".yt-link{display:inline-flex;width:20px;height:20px;align-items:center;justify-content:center}")
    html_parts.append(".score-pill{display:inline-block;padding:6px 10px;border-radius:999px;color:#fff;font-weight:600;font-size:13px}")
    html_parts.append(".search-btn{display:inline-block;padding:6px 10px;border-radius:8px;background:#e6f0ff;color:#1e3a8a;font-weight:700;font-size:13px;text-decoration:none}")
    html_parts.append(".muted{color:#475569;font-size:13px}")
    html_parts.append("</style>")
    html_parts.append("</head>")
    html_parts.append("<body>")
    html_parts.append("<h1>Bandcamp search results</h1>")
    html_parts.append(f"<p class=\"muted\">Generated with {os.path.basename(__file__)} — {len(results)} rows</p>")
    html_parts.append("<table>")
    html_parts.append("<thead><tr><th>Uploader</th><th>Bandcamp Title</th><th style=\"width:140px;text-align:center\">Search</th><th style=\"width:120px;text-align:right\">Score</th></tr></thead>")
    html_parts.append("<tbody>")
    for r in results:
        raw_uploader = r.get("uploader") or "Unknown"
        raw_bc_title = r.get("bc_title") or ""
        uploader = _html.escape(raw_uploader)
        bc_title = _html.escape(raw_bc_title or "—")
        score = r.get("score") or 0.0
        bc_url = (r.get("bc_url") or "#").replace("'", "%27")
        raw_yt = r.get("yt_url") or ""
        yt_url = raw_yt.replace("'", "%27") if raw_yt else ""
        hue = hue_for_score(score)
        color = f"hsl({hue} 75% 45%)"
        score_text = f"{score:.2f}" if isinstance(score, float) else _html.escape(str(score))
        html_parts.append(f"<tr class=\"clickable\">")
        # uploader cell: uploader text (links to Bandcamp result) + small YouTube icon linking to original liked video
        uploader_cell = []
        uploader_cell.append(f"<a class=\"row-link\" href=\"{bc_url}\" target=\"_blank\" rel=\"noopener noreferrer\">{uploader}</a>")
        if yt_url:
            yt_svg = ("<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"16\" height=\"16\">"
                      "<path fill=\"#FF0000\" d=\"M23.5 6.2a2.9 2.9 0 0 0-2.05-2.06C19.73 3.5 12 3.5 12 3.5s-7.73 0-9.45.64A2.9 2.9 0 0 0 .5 6.2 30.8 30.8 0 0 0 0 12a30.8 30.8 0 0 0 .5 5.8 2.9 2.9 0 0 0 2.05 2.06c1.72.64 9.45.64 9.45.64s7.73 0 9.45-.64A2.9 2.9 0 0 0 23.5 17.8 30.8 30.8 0 0 0 24 12a30.8 30.8 0 0 0-.5-5.8z\"/>"
                      "<path fill=\"#fff\" d=\"M10 15l5-3-5-3v6z\"/></svg>")
            uploader_cell.append(f"<a class=\"yt-link\" href=\"{yt_url}\" target=\"_blank\" rel=\"noopener noreferrer\">{yt_svg}</a>")
        html_parts.append(f"<td><div class=\"cell-inner\">{''.join(uploader_cell)}</div></td>")
        html_parts.append(
            f"<td><a class=\"row-link\" href=\"{bc_url}\" target=\"_blank\" rel=\"noopener noreferrer\">{bc_title}</a></td>"
        )
        # Google search link for this track (uploader + bc title)
        try:
            query = urllib.parse.quote_plus(f"{raw_uploader} {raw_bc_title}".strip())
            google_url = f"https://www.google.com/search?q={query}"
        except Exception:
            google_url = "https://www.google.com"
        html_parts.append(
            f"<td style=\"text-align:center\"><a class=\"row-link search-btn\" href=\"{google_url}\" target=\"_blank\" rel=\"noopener noreferrer\">Search</a></td>"
        )
        html_parts.append(
            f"<td style=\"text-align:right\"><a class=\"row-link\" href=\"{bc_url}\" target=\"_blank\" rel=\"noopener noreferrer\"><span class=\"score-pill\" style=\"background:{color}\">{score_text}</span></a></td>"
        )
        html_parts.append("</tr>")
    html_parts.append("</tbody></table>")
    html_parts.append("</body></html>")

    with open("results.html", "w", encoding="utf-8") as fh:
        fh.write("\n".join(html_parts))

if __name__ == "__main__":
    main()
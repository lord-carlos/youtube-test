#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import textwrap
import webbrowser
from typing import Iterable

from models import MatchRow
from report import HtmlReport
from search import BandcampSearch, score_match
from youtube_client import (
    YouTubeClient,
    dash_stripped,
    filter_by_channels,
    validate_cookie_path,
)


def parse_args() -> argparse.Namespace:
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


def print_likes(likes: Iterable[str]) -> None:
    print("Matched liked videos (titles only):")
    for idx, title in enumerate(likes, 1):
        print(f"{idx}. {title}")


def main() -> None:
    args = parse_args()

    try:
        cookiefile = validate_cookie_path(args.cookie)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        sys.exit(1)

    yt_client = YouTubeClient(browser=args.browser, cookiefile=cookiefile)
    search_provider = BandcampSearch()
    report = HtmlReport()

    try:
        likes = yt_client.fetch_likes(args.limit)
    except Exception as exc:
        print(f"Failed to fetch likes via yt-dlp: {exc}", file=sys.stderr)
        sys.exit(1)

    filtered = filter_by_channels(likes, args.channels)
    if not filtered:
        print("No liked videos from the specified channels found.")
        return

    print_likes([like.title for like in filtered])
    print("\nBandcamp search results:")

    rows: list[MatchRow] = []
    for like in filtered:
        query = dash_stripped(like.title)
        result = search_provider.search_track(query)
        result.score = score_match(like.title, result.match_title, result.match_artist)
        matched = (
            result.score >= args.match_threshold
            and bool(result.match_url)
            and not result.error
        )
        rows.append(
            MatchRow(
                uploader=like.uploader,
                youtube_title=like.title,
                youtube_url=like.url,
                search_result=result,
                matched=matched,
            )
        )

        if result.error:
            print(f"- {like.title}: error searching Bandcamp ({result.error}); search URL: {result.search_url}")
            continue

        if not result.match_title and not result.match_artist:
            print(f"- {like.title}: no results; search URL: {result.search_url}")
            continue

        if matched:
            artist = result.match_artist or "Unknown artist"
            title = result.match_title or "Unknown title"
            url = result.match_url or result.search_url
            print(f"- {like.title}: MATCH {result.score:.2f} -> {title} — {artist} ({url})")
        else:
            print(f"- {like.title}: below threshold (score {result.score:.2f}); search URL: {result.search_url}")

    if args.html:
        try:
            report.write(rows)
            abspath = os.path.abspath(report.file_path)
            webbrowser.open_new_tab(f"file://{abspath}")
        except Exception as exc:
            print(f"Failed to write or open {report.file_path}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()

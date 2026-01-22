from __future__ import annotations

import os
from typing import Any, Callable, Iterable

import yt_dlp

from models import YouTubeLike


class YouTubeClient:
    def __init__(
        self,
        browser: str | None = None,
        cookiefile: str | None = None,
        ydl_factory: Callable[[dict[str, Any]], yt_dlp.YoutubeDL] | None = None,
    ) -> None:
        self.browser = browser
        self.cookiefile = cookiefile
        self.ydl_factory = ydl_factory or yt_dlp.YoutubeDL

    def fetch_likes(self, limit: int) -> list[YouTubeLike]:
        ydl_opts: dict[str, Any] = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "playlistend": limit,
        }
        if self.cookiefile:
            ydl_opts["cookiefile"] = self.cookiefile
        elif self.browser:
            ydl_opts["cookiesfrombrowser"] = (self.browser, None, None, None)

        with self.ydl_factory(ydl_opts) as ydl:
            info = ydl.extract_info("https://www.youtube.com/playlist?list=LL", download=False)
        entries = info.get("entries") or []
        likes: list[YouTubeLike] = []
        for item in entries:
            title = item.get("title") or ""
            uploader = item.get("uploader") or ""
            url = item.get("url") or item.get("webpage_url")
            likes.append(YouTubeLike(title=title, uploader=uploader, url=url))
        return likes


def validate_cookie_path(cookie: str | None) -> str | None:
    if not cookie:
        return None
    expanded = os.path.expanduser(cookie)
    if not os.path.isfile(expanded):
        raise FileNotFoundError(f"Cookie file not found: {cookie}")
    return expanded


def dash_stripped(text: str) -> str:
    return text.replace("-", " ").strip()


def filter_by_channels(likes: Iterable[YouTubeLike], channels: Iterable[str]) -> list[YouTubeLike]:
    candidates = {c.casefold(): c for c in channels}
    return [like for like in likes if like.uploader and like.uploader.casefold() in candidates]
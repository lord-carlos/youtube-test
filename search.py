from __future__ import annotations

import urllib.parse
from difflib import SequenceMatcher
from typing import Callable, Protocol

import httpx
from bs4 import BeautifulSoup

from models import SearchResult


class SearchProvider(Protocol):
    name: str

    def search_track(self, query: str) -> SearchResult:
        ...


class BandcampSearch:
    name = "Bandcamp"

    def __init__(self, client_factory: Callable[[], httpx.Client] | None = None) -> None:
        self._client_factory = client_factory or self._default_client_factory
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://bandcamp.com/",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }

    @staticmethod
    def _default_client_factory() -> httpx.Client:
        return httpx.Client(http2=True, timeout=10.0)

    def search_track(self, query: str) -> SearchResult:
        search_url = f"https://bandcamp.com/search?q={urllib.parse.quote_plus(query)}"
        result = SearchResult(query=query, search_url=search_url)
        try:
            with self._client_factory() as client:
                response = client.get(search_url, headers=self._headers)
                response.raise_for_status()
                document = response.text
        except Exception as exc:
            result.error = str(exc)
            return result

        soup = BeautifulSoup(document, "html.parser")
        first = soup.select_one("li.searchresult")
        if not first:
            return result

        link = first.select_one("a")
        title_el = first.select_one(".heading")
        artist_el = first.select_one(".subhead")
        result.match_title = title_el.get_text(strip=True) if title_el else None
        result.match_artist = artist_el.get_text(strip=True) if artist_el else None
        href = link["href"] if link and link.has_attr("href") else None
        result.match_url = urllib.parse.urljoin("https://bandcamp.com", href) if href else search_url
        return result


def score_match(youtube_title: str, match_title: str | None, match_artist: str | None) -> float:
    if not match_title and not match_artist:
        return 0.0
    base = youtube_title.casefold()
    candidate = " ".join(filter(None, [match_artist, match_title])).strip().casefold()
    return SequenceMatcher(None, base, candidate).ratio()
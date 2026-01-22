from dataclasses import dataclass


@dataclass
class YouTubeLike:
    title: str
    uploader: str
    url: str | None


@dataclass
class SearchResult:
    query: str
    search_url: str
    match_title: str | None = None
    match_artist: str | None = None
    match_url: str | None = None
    score: float = 0.0
    error: str | None = None


@dataclass
class MatchRow:
    uploader: str
    youtube_title: str
    youtube_url: str | None
    search_result: SearchResult
    matched: bool
from __future__ import annotations

import re


class QueryNormalizer:
    """Utility helpers for normalizing and sanitizing search queries."""

    @staticmethod
    def dash_stripped(text: str) -> str:
        """Replace hyphens with spaces so Bandcamp sees separate words."""
        return text.replace("-", " ").strip()

    @staticmethod
    def sanitize_search_query(query: str) -> str:
        """Drop bracketed fragments and non-alphanumeric noise to retry Bandcamp queries."""
        cleaned = re.sub(r"[\(\[\{][^\)\]\}]*[\)\]\}]", " ", query)
        cleaned = re.sub(r"[^0-9A-Za-z\s]", " ", cleaned)
        return " ".join(cleaned.split()).strip()

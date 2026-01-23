from __future__ import annotations

import os
import urllib.parse
from typing import Iterable

from jinja2 import Environment, FileSystemLoader

from models import MatchRow


class HtmlReport:
    def __init__(self, file_path: str = "results.html") -> None:
        self.file_path = file_path
        # Setup Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        self.env = Environment(loader=FileSystemLoader(template_dir))
        
        # Register custom filters
        self.env.filters["google_search_url"] = self._google_search_url
        self.env.filters["score_hue"] = self._hue_for_score

    def write(self, rows: Iterable[MatchRow]) -> None:
        template = self.env.get_template("report_template.html")
        
        html_content = template.render(
            rows=list(rows),
            generator_name=os.path.basename(__file__)
        )
        
        with open(self.file_path, "w", encoding="utf-8") as fh:
            fh.write(html_content)

    @staticmethod
    def _hue_for_score(score: float) -> int:
        clamped = max(0.0, min(1.0, score))
        return int(120 * clamped)

    @staticmethod
    def _google_search_url(row: MatchRow) -> str:
        query = f"{row.uploader} {row.search_result.match_title or row.youtube_title}".strip()
        if not query:
            return "https://www.google.com"
        return f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
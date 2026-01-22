from __future__ import annotations

import html as _html
import os
import urllib.parse
from typing import Iterable

from models import MatchRow


class HtmlReport:
    def __init__(self, file_path: str = "results.html") -> None:
        self.file_path = file_path

    def write(self, rows: Iterable[MatchRow]) -> None:
        row_list = list(rows)
        html_parts: list[str] = [
            "<!doctype html>",
            "<html lang=\"en\">",
            "<head>",
            "<meta charset=\"utf-8\">",
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
            "<title>Bandcamp matches</title>",
            "<style>",
            "body{font-family:Inter, system-ui, Arial, sans-serif; margin:24px; background:#f7fafc; color:#0f172a}",
            "h1{font-size:20px;margin-bottom:8px}",
            "table{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 6px 18px rgba(15,23,42,0.08)}",
            "thead th{background:#0f172a;color:#fff;padding:12px 16px;text-align:left;font-weight:600}",
            "tbody td{padding:0;border-top:1px solid #eef2f7}",
            "tr.clickable{cursor:pointer}",
            "tr.clickable:hover .row-link{background:linear-gradient(90deg, rgba(15,23,42,0.03), transparent)}",
            ".row-link{display:block;color:inherit;text-decoration:none;padding:12px 16px}",
            ".cell-inner{display:flex;align-items:center;gap:8px}",
            ".yt-link{display:inline-flex;width:20px;height:20px;align-items:center;justify-content:center}",
            ".score-pill{display:inline-block;padding:6px 10px;border-radius:999px;color:#fff;font-weight:600;font-size:13px}",
            ".search-btn{display:inline-block;padding:6px 10px;border-radius:8px;background:#e6f0ff;color:#1e3a8a;font-weight:700;font-size:13px;text-decoration:none}",
            ".muted{color:#475569;font-size:13px}",
            "</style>",
            "</head>",
            "<body>",
            "<h1>Bandcamp search results</h1>",
            f"<p class=\"muted\">Generated with {os.path.basename(__file__)} — {len(row_list)} rows</p>",
            "<table>",
            "<thead><tr><th>Uploader</th><th>Bandcamp Title</th><th style=\"width:140px;text-align:center\">Search</th><th style=\"width:120px;text-align:right\">Score</th></tr></thead>",
            "<tbody>",
        ]
        for row in row_list:
            uploader = _html.escape(row.uploader or "Unknown")
            bc_title = _html.escape(row.search_result.match_title or "—")
            score = row.search_result.score or 0.0
            bc_url = _html.escape(row.search_result.match_url or row.search_result.search_url or "#")
            yt_url = _html.escape(row.youtube_url or "")
            hue = self._hue_for_score(score)
            color = f"hsl({hue} 75% 45%)"
            score_text = f"{score:.2f}" if isinstance(score, float) else _html.escape(str(score))
            html_parts.append("<tr class=\"clickable\">")
            uploader_cell = [
                f"<a class=\"row-link\" href=\"{bc_url}\" target=\"_blank\" rel=\"noopener noreferrer\">{uploader}</a>"
            ]
            if yt_url:
                yt_svg = (
                    "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 24 24\" width=\"16\" height=\"16\">"
                    "<path fill=\"#FF0000\" d=\"M23.5 6.2a2.9 2.9 0 0 0-2.05-2.06C19.73 3.5 12 3.5 12 3.5s-7.73 0-9.45.64A2.9 2.9 0 0 0 .5 6.2 30.8 30.8 0 0 0 0 12a30.8 30.8 0 0 0 .5 5.8 2.9 2.9 0 0 0 2.05 2.06c1.72.64 9.45.64 9.45.64s7.73 0 9.45-.64A2.9 2.9 0 0 0 23.5 17.8 30.8 30.8 0 0 0 24 12a30.8 30.8 0 0 0-.5-5.8z\"/>"
                    "<path fill=\"#fff\" d=\"M10 15l5-3-5-3v6z\"/></svg>"
                )
                uploader_cell.append(
                    f"<a class=\"yt-link\" href=\"{yt_url}\" target=\"_blank\" rel=\"noopener noreferrer\">{yt_svg}</a>"
                )
            html_parts.append(f"<td><div class=\"cell-inner\">{''.join(uploader_cell)}</div></td>")
            html_parts.append(
                f"<td><a class=\"row-link\" href=\"{bc_url}\" target=\"_blank\" rel=\"noopener noreferrer\">{bc_title}</a></td>"
            )
            google_url = self._google_search_url(row)
            html_parts.append(
                f"<td style=\"text-align:center\"><a class=\"row-link search-btn\" href=\"{google_url}\" target=\"_blank\" rel=\"noopener noreferrer\">Search</a></td>"
            )
            html_parts.append(
                f"<td style=\"text-align:right\"><a class=\"row-link\" href=\"{bc_url}\" target=\"_blank\" rel=\"noopener noreferrer\"><span class=\"score-pill\" style=\"background:{color}\">{score_text}</span></a></td>"
            )
            html_parts.append("</tr>")
        html_parts.extend(["</tbody></table>", "</body></html>"])
        with open(self.file_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(html_parts))

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
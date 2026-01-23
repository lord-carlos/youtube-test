import os
import pytest
from report import HtmlReport
from models import MatchRow, SearchResult

def test_hue_for_score():
    report = HtmlReport()
    # Test min/max clamping and expected values
    assert report._hue_for_score(0.0) == 0      # Red-ish
    assert report._hue_for_score(1.0) == 120    # Green-ish
    assert report._hue_for_score(0.5) == 60     # Yellow-ish
    assert report._hue_for_score(-1.0) == 0     # Clamped min
    assert report._hue_for_score(2.0) == 120    # Clamped max

def test_google_search_url():
    report = HtmlReport()
    search_res = SearchResult(query="Artist - Track", search_url="http://bc.com")
    row = MatchRow(
        uploader="Test Artist",
        youtube_title="Great Track",
        youtube_url="http://yt.com",
        search_result=search_res,
        matched=False
    )
    
    url = report._google_search_url(row)
    assert "https://www.google.com/search?q=Test+Artist+Great+Track" in url

def test_report_generation():
    # Write to a stable file in the workspace for previewing
    report_file = os.path.join(os.path.dirname(__file__), "..", "tests", "test_output.html")
    report = HtmlReport(file_path=report_file)
    
    # Create mock data
    search_res = SearchResult(
        query="Aphex Twin - Flim",
        search_url="https://bandcamp.com/search?q=Aphex+Twin+-+Flim",
        match_title="Flim",
        match_artist="Aphex Twin",
        match_url="https://aphextwin.bandcamp.com/track/flim",
        score=0.95
    )
    row = MatchRow(
        uploader="Aphex Twin",
        youtube_title="Aphex Twin - Flim",
        youtube_url="https://youtube.com/watch?v=XW2E2Fnh52w",
        search_result=search_res,
        matched=True
    )
    
    # Write report
    report.write([row])
    
    # Verify file existence and content
    assert os.path.exists(report_file)
    with open(report_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    assert "Bandcamp Search Results" in content
    assert "Aphex Twin" in content
    assert "0.95" in content
    assert "https://aphextwin.bandcamp.com/track/flim" in content
    assert "tailwindcss" in content
    
    print(f"\nPreview report generated at: {os.path.abspath(report_file)}")

"""Presentation contracts; recorded model outputs remain immutable."""
from html.parser import HTMLParser
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src/searchclinic/web"

class Headings(HTMLParser):
    def __init__(self):
        super().__init__()
        self.level = None
        self.text = []
        self.headings = []
    def handle_starttag(self, tag, attrs):
        if tag == "title" or re.fullmatch(r"h[1-6]", tag):
            self.level = tag
            self.text = []
    def handle_data(self, data):
        if self.level:
            self.text.append(data)
    def handle_endtag(self, tag):
        if tag == self.level:
            self.headings.append("".join(self.text).strip())
            self.level = None

def test_all_web_headings_use_nominal_copy():
    failures = []
    for path in WEB.glob("*.html"):
        parser = Headings()
        parser.feed(path.read_text(encoding="utf-8"))
        for heading in parser.headings:
            if re.search(r"[?？]|했을까|했어요|했다|[가-힣]요[.!]?$", heading):
                failures.append((path.name, heading))
    assert not failures, failures

def test_latest_screen_is_a_case_first_workbench():
    text = (WEB / "generation-v4.html").read_text(encoding="utf-8")
    assert "<h1>검색 품질 검증</h1>" in text
    for name in ["case-list", "case-search", "case-outcome", "panel-cases", "panel-summary", "panel-info"]:
        assert f'id="{name}"' in text
    assert text.index('id="panel-cases"') < text.index('id="panel-summary"')
    assert 'role="tablist"' in text
    assert 'aria-controls="panel-cases"' in text
    assert 'id="panel-summary"' in text and 'id="panel-info"' in text

def test_new_assets_are_local_and_data_projection_is_unchanged():
    import hashlib
    expected = "a1b77a113abf8bb30751b36ecf8fed431e2198a0c119cd4d5506582e819e95de"
    assert hashlib.sha256((WEB / "generation-v4.json").read_bytes()).hexdigest() == expected
    text = (WEB / "generation-v4.html").read_text(encoding="utf-8")
    assert not re.search(r'<script[^>]+src="https?://', text)
    assert "workbench.css?" in text
    assert "generation-v4.js?" in text

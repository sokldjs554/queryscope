"""Browser contracts for the immutable 48-response review workspace (no API calls)."""
from __future__ import annotations
import argparse
import functools
import hashlib
import json
import os
from pathlib import Path
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "src/searchclinic/web"

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--base-url", choices=["https://queryscope-zwia.onrender.com"])
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    raw = (WEB / "generation-v4.json").read_bytes()
    data = json.loads(raw)
    server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(WEB)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = args.base_url or f"http://127.0.0.1:{server.server_address[1]}"
    result = {"passed": False, "source_sha256": hashlib.sha256(raw).hexdigest(), "new_model_calls": 0, "checks": []}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=os.environ.get("CHROME_EXECUTABLE"), args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
            errors, external = [], []
            page.on("pageerror", lambda e: errors.append(str(e)))
            def route_request(route):
                if not route.request.url.startswith(base + "/") or route.request.method not in ("GET", "HEAD"):
                    external.append(route.request.url)
                    route.abort()
                else:
                    route.continue_()
            page.route("**/*", route_request)
            page.goto(base + "/generation-v4.html")
            page.wait_for_function("!document.getElementById('v4-content').hidden")
            page.screenshot(path=str(args.output / "initial-desktop.png"))
            if args.base_url:
                public_data = page.request.get(base + "/generation-v4.json")
                assert public_data.ok and public_data.body() == raw, "public data differs from checked source"
                for name in ["generation-v4.html", "generation-v4.js", "workbench.css"]:
                    public_file = page.request.get(base + "/" + name)
                    assert public_file.ok and public_file.body() == (WEB / name).read_bytes(), name
                result["checks"].append("public HTML/JS/CSS/data match checked source bytes")
            assert page.locator("h1").inner_text() == "검색 품질 검증", "nominal title missing"
            assert page.locator("#panel-cases").is_visible()
            assert not page.locator("#panel-summary").is_visible()
            assert page.locator("#case-list button").count() == 24
            for selector in ["#v4-no-hint", "#v4-hint"]:
                assert page.locator(selector).bounding_box()["y"] < 480, "case results buried below introduction"
            result["checks"].append("case-first viewport and nominal title")
            checked = 0
            for pair in data["pairs"]:
                page.select_option("#v4-case", pair["id"])
                assert page.locator("#case-title").inner_text() == pair["query"]
                for condition, target in [("no_hint", "v4-no-hint"), ("hint", "v4-hint")]:
                    row = pair["conditions"][condition]
                    text = page.locator("#" + target).text_content()
                    assert row["context"]["problem"] in text
                    if row.get("answer"):
                        assert row["answer"]["summary"] in text
                    if row.get("response_id"):
                        assert row["response_id"] in text
                    for quote in row["citation_checks"]:
                        assert quote["quote"] in text
                    record = page.locator("#" + target + " [data-record='row'] pre").text_content()
                    assert json.loads(record) == row, (pair["id"], condition, "raw row changed")
                    effect = (row.get("assessment") or {}).get("patch_effect", {})
                    if effect.get("status") == "measured":
                        assert ("수정안 채택" if effect["gate"]["accepted"] else "수정안 기각") in text
                        assert "기존 36질의" in text and "개발 16질의" in text
                    checked += 1
            assert checked == 48
            result["checks"].append("48 contexts, answers, citations, effect scopes and raw rows match source")
            page.fill("#case-search", "microscope")
            assert page.locator("#case-list button").count() == 1
            assert page.locator("#case-title").inner_text() == "microscope"
            page.reload()
            page.wait_for_function("!document.getElementById('v4-content').hidden")
            assert page.locator("#case-search").input_value() == "microscope"
            assert page.locator("#case-title").inner_text() == "microscope"
            page.fill("#case-search", "존재하지않는검색어")
            assert page.locator("#case-list button").count() == 0
            assert page.locator("#no-selection").is_visible()
            assert not page.locator("#selected-case").is_visible()
            page.click("#reset-filters")
            assert page.locator("#case-list button").count() == 24
            for group in ["paired_v3", "additional_development"]:
                page.select_option("#v4-group", group)
                assert page.locator("#case-list button").count() == 12
                assert page.locator("#v4-case option").count() == 12
            page.select_option("#v4-group", "all")
            page.select_option("#case-outcome", "accepted")
            expected = sum(any((r.get("assessment") or {}).get("patch_effect", {}).get("gate", {}).get("accepted") is True for r in pair["conditions"].values()) for pair in data["pairs"])
            assert page.locator("#case-list button").count() == expected
            page.select_option("#case-outcome", "all")
            page.select_option("#v4-case", "T01")
            page.click("#case-next")
            assert page.locator("#v4-case").input_value() == "T02"
            page.click("#case-prev")
            assert page.locator("#v4-case").input_value() == "T01"
            assert page.locator("#case-prev").is_disabled()
            result["checks"].append("search, empty state, scope/outcome filters, navigation and reload state")
            page.click("#tab-summary")
            assert page.locator("#panel-summary").is_visible()
            assert not page.locator("#panel-cases").is_visible()
            metrics = ["rows", "supported", "abstain", "invalid", "api_errors", "provenance_errors", "gate_measured", "gate_accepted", "gate_rejected", "abstention_contract_pass", "wrong_patch_on_abstain_required"]
            for index, key in enumerate(metrics):
                expected = [str(data["groups"][g][c][key]) for g in ["paired_v3", "additional_development"] for c in ["no_hint", "hint"]]
                assert page.locator("#v4-summary tr").nth(index).locator("td").all_text_contents() == expected
            page.locator("#tab-summary").press("ArrowRight")
            assert page.locator("#tab-info").get_attribute("aria-selected") == "true"
            assert page.locator("#panel-info").is_visible()
            assert str(data["cost"]["known_estimate_usd"]) in page.locator("#v4-cost-scope").inner_text()
            page.locator("#tab-info").press("Home")
            assert page.locator("#tab-cases").get_attribute("aria-selected") == "true"
            result["checks"].append("summary values, cost provenance and keyboard tabs")
            for width in [320, 390, 650, 1024, 1440]:
                page.set_viewport_size({"width": width, "height": 1000})
                for tab in ["cases", "summary", "info"]:
                    page.click("#tab-" + tab)
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (width, tab, "document overflow")
                page.click("#tab-cases")
                page.screenshot(path=str(args.output / f"workbench-{width}.png"), full_page=width < 700)
            page.set_viewport_size({"width": 1440, "height": 1000})
            page.select_option("#v4-case", "T15")
            page.screenshot(path=str(args.output / "workbench-citation-error.png"))
            result["checks"].append("five viewport widths, all tabs, no document overflow")
            for filename in ["index.html", "generation-v3.html", "review-v4.html", "evaluation.html", "evaluation-v2.html", "evaluation-v3.html"]:
                page.goto(base + "/" + filename)
                headings = page.locator("h1,h2,h3").all_text_contents()
                assert not any("?" in s or "했을까" in s or "했어요" in s for s in headings)
                assert page.locator('a[href="generation-v4.html"]').count() > 0, filename
            result["checks"].append("legacy page titles and latest-screen navigation")
            page.route("**/generation-v4.json", lambda route: route.fulfill(status=503, body="unavailable"))
            page.goto(base + "/generation-v4.html")
            page.wait_for_function("document.getElementById('v4-status').textContent.includes('자료 로딩 오류')")
            assert page.locator("#v4-content").is_hidden()
            page.unroute("**/generation-v4.json")
            page.route("**/generation-v4.json", lambda route: route.fulfill(status=200, content_type="application/json", body="{}"))
            page.reload()
            page.wait_for_function("document.getElementById('v4-status').textContent.includes('자료 로딩 오류')")
            assert page.locator("#v4-content").is_hidden()
            assert not errors, errors
            assert not external, external
            result["checks"].append("503 and malformed data fail closed; zero external requests or JavaScript errors")
            result.update(passed=True, slots_checked=checked, viewports=[320, 390, 650, 1024, 1440])
            browser.close()
    except Exception as exc:
        result["error"] = str(exc)
        raise
    finally:
        server.shutdown()
        (args.output / "checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    main()

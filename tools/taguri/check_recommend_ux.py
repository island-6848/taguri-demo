"""Exercise the shipped recommendation screen and JS in Chromium, without network services.

Run: python3 tools/taguri/check_recommend_ux.py
Requires Playwright and Chromium (CHROMIUM_PATH may select the executable).
"""
import json
import os
from pathlib import Path
import subprocess
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = json.loads(subprocess.check_output(
    ["node", "cloudflare/test/screens/recommend_ux_fixture.js"], cwd=ROOT, text=True))


def check(browser, width):
    page = browser.new_page(viewport={"width": width, "height": 900}, reduced_motion="reduce")
    errors, writes = [], []
    page.on("pageerror", lambda e: errors.append(str(e)))
    state = {"fail": False, "fill": True}

    def route(request):
        url = request.request.url
        if url.endswith("/api/react"):
            body = request.request.post_data_json
            writes.append(body)
            if body.get("fill_only"):
                request.fulfill(json={"ok": True, "fill": {"html": FIXTURE["fill"] if state["fill"] else "", "said": "次の候補を追加しました"}})
            elif state["fail"]:
                request.fulfill(status=503, json={"error": "一時的に保存できません"})
            else:
                request.fulfill(json={"ok": True, "value": body.get("value")})
        elif "/api/" in url:
            request.fulfill(json={"ok": True})
        else:
            request.fulfill(content_type="text/html", body='<html lang="ja"><body><aside class="side"></aside>'
                            '<div id="crumbbar"><nav id="crumbnav"></nav></div><main id="content"></main></body></html>')

    page.route("**/*", route)
    page.goto("https://taguri.test/recommend")
    page.evaluate("window.TAGURI={edition:'service',api:location.origin,base:'',demoBase:'/demo'}")
    for name in ("style.css", "theme.css"):
        page.add_style_tag(content=(ROOT / "web" / name).read_text())
    page.add_style_tag(content="#content{max-width:900px;margin:16px}body{margin:0}.side{display:none}")
    page.add_script_tag(content=(ROOT / "web/app.js").read_text())

    def render(scene):
        page.evaluate("d => renderScreen(document.getElementById('content'), '/recommend', d)", FIXTURE["scenes"][scene])

    render("normal")
    controls = page.locator(".rec-controls")
    expect(controls).not_to_have_attribute("open", "")
    expect(controls.locator("summary").first).to_contain_text("全国")
    expect(page.locator(".rec-answer-help")).to_be_visible()
    expect(page.locator(".dismissq-open").first).to_have_attribute("title", "この公演を候補に表示しない（好みには反映しません）")
    controls.locator(":scope > summary").click()
    expect(page.locator(".fil2.tune .ftab")).to_have_count(3)
    expect(page.locator(".fil2.narrow .ftab")).to_have_count(2)
    page.locator('.ftab[data-for="ybox"]').click()
    page.locator(".ysl").evaluate("s => {s.value='0';s.dispatchEvent(new Event('input'))}")
    expect(page.locator(".rec-budget")).not_to_be_empty()
    controls.locator(":scope > summary").click()
    expect(page.locator(".rec-budget")).to_be_visible()
    page.locator(".yclear").click()
    expect(page.locator(".rec-budget")).to_be_empty()
    expect(controls.locator(":scope > summary")).to_be_focused()
    # The recommendation reason still follows the synopsis, both before and after editing.
    assert page.locator(".ticket").first.evaluate("t => !!(t.querySelector('.leadbox').compareDocumentPosition(t.querySelector('.whyh')) & Node.DOCUMENT_POSITION_FOLLOWING)")
    first = page.locator('.ticket[data-stage="101"]')
    original_height = first.bounding_box()["height"]
    state["fail"] = True
    first.locator('[data-v="interest"]').click()
    expect(first.locator(".said").first).to_contain_text("できませんでした")
    assert "answered-compact" not in first.get_attribute("class")
    assert not any(b.get("fill_only") for b in writes)
    state["fail"] = False
    first.locator('[data-v="interest"]').click()
    expect(first.locator(".answered-value")).to_have_text("興味あり")
    expect(first.locator(".cfoot")).not_to_be_visible()
    expect(page.locator('.ticket[data-stage="103"]')).to_have_count(1)
    assert first.bounding_box()["height"] < original_height / 2
    expect(first.locator("[data-answer-expand]")).to_be_focused()
    first.locator("[data-answer-expand]").click()
    expect(first.locator(".cfoot")).to_be_visible()
    expect(first.locator(".why-note")).to_be_visible()
    first.locator(".why-note textarea").fill("この出演者が気になる")
    first.locator('[data-v="nointerest"]').click()
    expect(first.locator(".answered-value")).to_have_text("興味なし")
    assert sum(bool(b.get("fill_only")) for b in writes) == 1, "correcting an answer must not add another candidate"
    first.locator("[data-answer-expand]").click()
    state["fail"] = True
    first.locator('[data-v="interest"]').click()
    expect(first.locator(".said").first).to_contain_text("できませんでした")
    expect(first.locator('[data-v="nointerest"]')).to_have_class("picked")
    expect(first.locator(".answered-value")).to_have_text("興味なし")
    state["fail"] = False
    first.locator('[data-v="owned"]').click()
    expect(first.locator(".answered-value")).to_have_text("購入済")
    first.locator("[data-answer-expand]").click()
    assert first.locator(".why-note textarea").input_value() == "この出演者が気になる"
    first.locator("[data-answer-expand]").click()
    expect(first.locator(".cfoot")).not_to_be_visible()
    page.screenshot(path=f"/tmp/recommend-ux-{width}.png", full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "no horizontal overflow"
    # The × keeps its distinct server action; adding the next card must not duplicate it.
    page.locator('.ticket[data-stage="102"] .dismissq-open').click()
    expect(page.locator(".dismissed")).to_contain_text("候補から消しました")
    assert any(b.get("stage_id") == "102" and b.get("value") == "dismiss" for b in writes)
    expect(page.locator('.ticket[data-stage="103"]')).to_have_count(1)
    # New accounts retain the same three tips and have no settings UI.
    render("empty")
    expect(page.locator(".tips .tip")).to_have_count(3)
    expect(page.locator(".rec-controls")).to_have_count(0)
    # A filter that hides all candidates still exposes the route back to settings.
    render("filtered")
    expect(page.locator(".rec-controls > summary")).to_contain_text("大阪府")
    render("tuned")
    expect(page.locator(".rec-controls > summary")).to_contain_text("選び方を調整中")
    assert not errors, errors
    page.close()


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH", "/usr/bin/chromium"), args=["--no-sandbox"])
    for viewport_width in (390, 1280):
        check(browser, viewport_width)
        print(f"Recommendation UX passed at {viewport_width}px")
    browser.close()

"""Real browser checks of the shared answer buttons and the interest screen, with local mock APIs.
Run: python3 tools/taguri/check_interest_ux.py (Playwright and Chromium required).
"""
import json
import os
from pathlib import Path
import subprocess
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
F = json.loads(subprocess.check_output(['node', 'cloudflare/test/screens/interest_ux_fixture.js'], cwd=ROOT, text=True))


def check(browser, width):
    page = browser.new_page(viewport={'width': width, 'height': 900}, reduced_motion='reduce')
    page.set_default_timeout(6000)
    errors, writes, reads = [], [], []
    page.on('pageerror', lambda e: errors.append(str(e)))
    state = {'fail': False, 'saved': '', 'delay': 0}

    def route(r):
        req = r.request
        if '/api/' in req.url and req.method == 'POST':
            b = req.post_data_json
            writes.append(b)
            if state['fail']:
                r.fulfill(status=503, json={'error': '一時的に保存できません'}); return
            if 'note' in b:
                r.fulfill(json={'ok': True}); return
            if b.get('fill_only'):
                r.fulfill(json={'ok': True, 'fill': {'html': '', 'said': ''}}); return
            state['saved'] = '' if b.get('clear') else b.get('value', b.get('verdict', ''))
            r.fulfill(json={'ok': True, 'cleared': b.get('clear', False), 'value': state['saved']})
        elif '/api/screen/interest' in req.url:
            reads.append(req.url); r.fulfill(json={'ok':True, **F['scene']})
        elif '/api/' in req.url:
            r.fulfill(json={'ok': True})
        else:
            r.fulfill(content_type='text/html', body='<html lang="ja"><body><aside class="side"></aside><div id="crumbbar"><nav id="crumbnav"></nav></div><main id="content"></main></body></html>')

    page.route('**/*', route)
    page.goto('https://taguri.test/recommend/interest?m=2026-11')
    page.evaluate("window.TAGURI={edition:'service',api:location.origin,base:'',demoBase:'/demo'}")
    for name in ('style.css','theme.css'):
        page.add_style_tag(content=(ROOT / 'web' / name).read_text())
    page.add_style_tag(content='#content{max-width:900px;margin:16px}body{margin:0}.side{display:none}')
    page.add_script_tag(content=(ROOT / 'web/app.js').read_text())

    def render(path, html):
        page.evaluate('(p)=>{history.replaceState({},"",p.path);renderScreen(document.getElementById("content"),p.path,{body_html:p.html,title:"検証"})}', {'path': path, 'html': html})

    render('/recommend/interest', F['scene']['body_html'])
    expect(page.locator('.sortf input[name=m]')).to_have_value('2026-11')
    page.locator('.sortf select').select_option('end')
    try:
        page.wait_for_function('document.querySelector(".sortf input[name=m]")?.value === "2026-11"', timeout=6000)
    except Exception:
        raise AssertionError({'errors':errors,'reads':reads,'body':page.locator('#content').inner_text()})
    assert any('m=2026-11' in u and 's=end' in u for u in reads)
    memo = page.locator('.why-memo')
    expect(memo.locator('summary')).to_contain_text('演出が気になって保存しました')
    expect(memo.locator('textarea')).not_to_be_visible()
    memo.locator('summary').click()
    expect(memo.locator('textarea')).to_have_value('演出が気になって保存しました。\nあの出演者の新しい役も楽しみです。')
    memo.locator('textarea').fill('書き換えたメモです。\n続きも残します。')
    memo.locator('summary').click()
    expect(memo.locator('summary')).to_contain_text('書き換えたメモです')
    for value in ('nointerest','cantgo','owned','interest'):
        b = page.locator(f'.ticket button[data-v="{value}"]')
        if value == 'interest':
            # Initially selected; a double click at this point would first clear.
            page.locator('.ticket button[data-v="nointerest"]').click()
        b.click()
        expect(b).to_have_attribute('aria-pressed','true')
        expect(page.locator('.answer-state')).to_contain_text({'nointerest':'興味なし','cantgo':'行けない','owned':'購入済','interest':'興味あり'}[value])
        b.click()
        expect(b).to_have_attribute('aria-pressed','false')
        expect(page.locator('.answer-state')).to_contain_text('未回答')
        assert writes[-1].get('clear') is True
        assert writes[-1]['siblings'] == ['101','102']
    state['fail'] = True
    page.locator('.ticket button[data-v="owned"]').click()
    expect(page.locator('.btns .said')).to_contain_text('できませんでした')
    expect(page.locator('.ticket button[data-v="owned"]')).to_have_attribute('aria-pressed','false')
    state['fail'] = False
    # Two clicks while the first request is still in flight are one save, not an accidental undo.
    before=len(writes)
    page.locator('.ticket button[data-v="nointerest"]').evaluate('(b)=>{b.click();b.click()}')
    expect(page.locator('.ticket button[data-v="nointerest"]')).to_have_attribute('aria-pressed','true')
    assert len(writes)==before+1
    state['fail']=True
    page.locator('.ticket button[data-v="nointerest"]').click()
    expect(page.locator('.btns .said')).to_contain_text('できませんでした')
    expect(page.locator('.ticket button[data-v="nointerest"]')).to_have_attribute('aria-pressed','true')
    state['fail']=False
    # Already saved choices can be cleared immediately on other screens too.
    for path, key, selected in (('/tickets','owned','owned'),('/recommend/favourites','favourite','owned')):
        render(path,F[key]); b=page.locator(f'.btns button[data-v="{selected}"]')
        opener=page.locator('[data-btns-open]')
        if opener.count(): opener.click()
        b.click(); expect(b).to_have_attribute('aria-pressed','false'); assert writes[-1].get('clear')
    for path in ('/recommend','/search','/recommend/reminder'):
        render(path,F['recommend']); b=page.locator('.btns button[data-v="interest"]')
        b.click(); expect(b).to_have_attribute('aria-pressed','true')
        if path == '/recommend': page.locator('[data-answer-expand]').click()
        b.click(); expect(b).to_have_attribute('aria-pressed','false'); assert writes[-1].get('clear')
    # Every supported rating scale follows the same toggle rule.
    for scale, html in F['ratings'].items():
        render('/rate',html); b=page.locator('.rb button[data-v]').first
        b.click(); expect(b).to_have_attribute('aria-pressed','true')
        b.click(); expect(b).to_have_attribute('aria-pressed','false')
        assert writes[-1].get('clear') and writes[-1]['work_key']=='work-1'
        expect(page.locator('[data-stamp]')).to_have_text('未評価')
    for saved in F['savedRatings']:
        render('/rate',saved['html'])
        b=page.locator('.rb button[data-v="'+saved['value']+'"]')
        expect(b).to_have_attribute('aria-pressed','true')
        b.click(); expect(b).to_have_attribute('aria-pressed','false'); assert writes[-1].get('clear')
    render('/recommend/interest',F['scene']['body_html'])
    page.screenshot(path=f'/tmp/interest-ux-{width}.png', full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert page.locator('.ticket').evaluate('(t)=>{const r=t.getBoundingClientRect();return [...t.querySelectorAll(".btns button")].every(b=>{const v=b.getBoundingClientRect();return v.left>=r.left && v.right<=r.right})}')
    assert not errors, errors
    page.close()


with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=os.environ.get('CHROMIUM_PATH','/usr/bin/chromium'),args=['--no-sandbox'])
    for width in (390,1280):
        check(browser,width)
        print(f'Interest UX and shared answer toggles passed at {width}px')
    browser.close()

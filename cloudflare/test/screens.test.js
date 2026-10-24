// The original screens ported to the Worker (src/screens/) must answer exactly
// as the Python app on Render does. test/screens/python_screens.py runs each
// scenario in test/screens/scenarios.json on the Python app; here the same
// steps run on the Worker (NATIVE_UI=all) with a fresh signed-in account.
import {readFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {setup, step, signIn} from './screens/harness.js';

const here = p => new URL(p, import.meta.url).pathname;
const scenarios = JSON.parse(readFileSync(here('./screens/scenarios.json'), 'utf8'));
const python = JSON.parse(execFileSync('python3', [here('./screens/python_screens.py'), here('./screens/scenarios.json')], {maxBuffer: 256 * 1024 * 1024, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore']}));

// 記録を直す欄（<details class="editor">）は 2026-10-14 からサービス版（Worker）だけの形にした
// （起案者の指摘「公演詳細を編集するところがわかりにくい」「メール本文を見るってメールを保存してる？」）。
// Python は持ち主のメール機能つきのままなので、この欄だけは比べずに印に置き換え、形は drop-expiry.test.js で確かめる。
// 「いますぐ消す」（purge_work）もサービス版はその場で記録を消す（Python は印を付けるだけ）ので、比べずに drop-expiry.test.js で確かめる。
const EDITOR_PY = /<details class="editor"[\s\S]*?<div class="ed-mail" hidden>[\s\S]*?<\/div><\/details>/g;
const EDITOR_JS = /<details class="editor"[\s\S]*?<!--\/editor--><\/details>/g;
// 評価の段階は 2026-10-14 からサービス版だけ星 5 段階が初期設定（screens/grade.js、起案者の指示「星5段階を初期設定にして」）。
// Python は ◎○△× のままなので、星のボタンは ◎○△× のボタンに読み替えて比べ、星の形は grade.test.js で確かめる。
// 星の後ろの押し口は 2026-10-18 から「評価しない」でなく、評価を消す ✕（起案者の指示「星の右端に✕ボタンをつけることでnullにできるようにして」）
const STAR_BTNS = /(?:<button class="star(?: on)?" data-v="[1-5]\/5" aria-label="星 [1-5]"><\/button>){5}<button type="button" class="gclr" data-clear="1" aria-label="評価を消す（未評価に戻す）" title="評価を消す"(?: hidden)?>✕<\/button>/g;
const MARK_BTNS = ['◎', '○', '△', '×'].map(g => `<button data-v="${g}">${g}</button>`).join('');
// 星の行は余白の判子を出さず、星の列を常に出す（2026-10-15 起案者の指示「下に星で表示されるんなら、〇の枠いらなくない？」、
// screens/row.js の starRow）。Python の行は判子と「評価を押し直す」のままなので、星の段階の人の画面では Python の側を星の行の形に直して比べる。
const STAMP = /<span class="stamp[^"]*" data-stamp="1"[^>]*>[^<]*<\/span>/g;
const asStarRows = r => (r && typeof r.body?.body_html === 'string'
  ? {...r, body: {...r.body, body_html: r.body.body_html.replace(STAMP, '')
    .replace(/<button class="wnb" data-rate-open="1">評価を押し直す<\/button>(<span class="rb" data-work="[^"]*") hidden>/g, '$1>')}} : r);
// 評価一覧・未評価・日記帳の 1 件に添える、つながった公演の作り手・あらすじ（screens/rowinfo.js）は 2026-10-18 から
// サービス版だけの形（起案者の指示「評価一覧や日記帳のカードもおすすめと揃えて」）。Python の行のあらすじ・出演の欄と
// サービス版の欄はどちらも比べずに外し、形は rowinfo.test.js で確かめる。
const RINFO_JS = /<div class="rinfo"[^>]*>[\s\S]*?<!--\/rinfo--><\/div>/g;
const ROWINFO_PY = /<div class="syn"><p class="txt">[^<]*<\/p><button class="mrb" data-more="1">続きを読む<\/button><\/div>|<div class="cast">(?:<div class="cr">[\s\S]*?<\/span><\/div>)+<\/div>/g;
const noRowInfo = r => (r && typeof r.body?.body_html === 'string' && r.body.body_html.includes('rec-row')
  ? {...r, body: {...r.body, body_html: r.body.body_html.replace(RINFO_JS, '').replace(ROWINFO_PY, '')}} : r);
// 2026-10-21 からサービス版だけ: 1 回の記録の開演の時刻、まとめた回を足した回数、まとめた回の一覧（起案者の問い「ツアー公演を複数回追加するとき、
// またまとめた公演を見るとき周辺のUXが悪い」、screens/row.js visitsHtml）。Python の行には無いので外して比べ、形は visits.test.js で確かめる
const VISITS_JS = / <span class="at">[^<]*<\/span>| ?<span class="mtimes">[^<]*<\/span>|<details class="visits">[\s\S]*?<\/details>/g;
const noVisits = r => (r && typeof r.body?.body_html === 'string' ? {...r, body: {...r.body, body_html: r.body.body_html.replace(VISITS_JS, '')}} : r);
const noEditor = (r, re) => (r && typeof r.body === 'object' && typeof r.body?.body_html === 'string'
  ? {...r, body: {...r.body, body_html: r.body.body_html.replace(re, '<EDITOR/>').replace(STAR_BTNS, MARK_BTNS).replaceAll('この場で★を押せます', 'この場で ◎○△× を押せます')}} : r);

for (const [i, sc] of scenarios.entries()) {
  test(`screen scenario: ${sc.name}`, async () => {
    const {sqlite, env} = setup();
    const cookie = await signIn(env);
    for (const [j, s] of sc.steps.entries()) {
      const raw = await step(env, cookie, s);
      const got = noVisits(noRowInfo(noEditor(raw, EDITOR_JS)));
      // 判子が 1 つも無い画面は星の段階の人の画面（◎○△× の人は判子のまま）
      const starPage = typeof raw?.body?.body_html === 'string' && !raw.body.body_html.includes('data-stamp="1"');
      const want = noRowInfo(noEditor(starPage ? asStarRows(python[i].steps[j]) : python[i].steps[j], EDITOR_PY));
      if (typeof want.body === 'object' && typeof got.body === 'object' && got.body.body_html !== want.body.body_html && got.body.body_html && want.body.body_html) {
        // Show where the HTML first differs (the whole page is long).
        const a = got.body.body_html, b = want.body.body_html;
        let k = 0; while (k < a.length && a[k] === b[k]) k++;
        assert.fail(`step ${j} ${s.get || s.post}: body_html differs at ${k}\n  worker: ${JSON.stringify(a.slice(Math.max(0, k - 80), k + 120))}\n  python: ${JSON.stringify(b.slice(Math.max(0, k - 80), k + 120))}`);
      }
      assert.deepStrictEqual(got, want, `step ${j} ${s.get || s.post}`);
    }
    sqlite.close();
  });
}
test('scenarios ran on both servers', () => assert.equal(python.length, scenarios.length));

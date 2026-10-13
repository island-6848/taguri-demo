// measure_nets.parse_credits and app.hand_credit_count, ported to
// src/screens/credits.js, must read every way of writing credits the same.
import {execFileSync} from 'node:child_process';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {parseCredits, handCreditCount} from '../src/screens/credits.js';

const CASES = [
  {'出演': '俳優甲、俳優乙・俳優丙\n（Wキャスト）俳優丁', '演出': '【演出】 演出家丙'},
  {'出演': 'ボブ・ウォルトン／加藤 温, 作り手26・作り手18', '脚本': '作：作家A（原作：作家B）'},
  {'出演': '鎌塚慎平(劇団・木製ボイジャー14号)、正門良規(Aぇ!group、関西ジャニーズJr.)※出演日注意'},
  {'スタッフ': '美術：美術家A　照明:照明家B\n音響\n  音響家C\n【衣裳】衣裳家D【照明】照明家E\n2026年10月1日 劇場A'},
  {'スタッフ': '舞台監督 監督者F\n　続きの人G\n■作・演出：作演H\nパルクール演出 動く人I\nディレクター：\n名前だけJ'},
  {'スタッフ': 'CAST-Team\nABC DEF\n▶チケット発売中\n宣伝美術デザイン：絵描きK\r\n制作デスク：机L 音楽プラン 音M'},
  {'出演': 'ア', '脚本': '脚本', 'スタッフ': ''},
  {'出演': '  全角　空白　の人 ', '演出': '演出家丙\n演出家丙'},
  {'出演': 'ＡＢＣ　ＤＥＦ、ｶﾀｶﾅ', 'スタッフ': '映像オペレーション：映像N\n【】空の括弧\n協力:協力者O/協力者P'},
  {},
];

test('parse_credits matches Python on assorted credit fields', () => {
  const script = [
    'import json, sys',
    "sys.path[:0] = ['tools/review', 'tools/taguri', 'tools']",
    'import measure_nets as M',
    'cases = json.loads(sys.stdin.read())',
    'out = [{"pairs": [list(p) for p in M.parse_credits(c)], "people": len({p for _r, p in M.parse_credits(c)}) if c else 0} for c in cases]',
    'print(json.dumps(out, ensure_ascii=False))',
  ].join('\n');
  const want = JSON.parse(execFileSync('python3', ['-c', script], {cwd: new URL('../../', import.meta.url).pathname, input: JSON.stringify(CASES), encoding: 'utf8'}));
  CASES.forEach((c, i) => {
    assert.deepStrictEqual(parseCredits(c), want[i].pairs, `case ${i}`);
    assert.equal(handCreditCount(c), want[i].people, `count ${i}`);
  });
});

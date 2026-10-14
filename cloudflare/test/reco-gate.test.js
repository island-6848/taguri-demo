// 裏の答え合わせ (src/reco-gate.js): a variant of the scoring rules is used
// for a user only when it clearly predicted that user's own later ratings
// better than the default.
import {execFileSync} from 'node:child_process';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {chooseVariant, stageScore, ROLE_W, BACKSTAGE_W, GENRE_W, groupOf} from '../src/reco-gate.js';
import {personValues, ASPECTS} from '../src/recommend.js';

test('role weights and groups are the same as Python', () => {
  const py = JSON.parse(execFileSync('python3', ['-c', `
import json, sys
sys.path[:0] = ['../tools/review', '../tools/taguri']
import recommend2 as RC, app as APP, user_recommender as UR
print(json.dumps({"w": RC.ROLE_W, "back": RC.BACKSTAGE_W, "genre": UR.GENRE_W,
  "aspects": {k: [l, m] for k, (l, m) in UR.ASPECTS.items()},
  "groups": {r: g for g, _l, roles in APP.ROLE_GROUPS for r in roles}}, ensure_ascii=False))`], {encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore']}));
  assert.deepEqual(ROLE_W, py.w);
  assert.equal(BACKSTAGE_W, py.back);
  assert.equal(GENRE_W, py.genre);
  assert.deepEqual(ASPECTS, py.aspects);
  for (const [role, g] of Object.entries(py.groups)) assert.equal(groupOf(role), g, role);
  assert.equal(groupOf('#形式'), 'theme');
  assert.equal(groupOf('知らない役職'), 'other');
});

// Deterministic made-up user. Each production has six cast members, a
// director and a form tag; `drive` decides what the rating follows:
// 'dir' (half of the directors are liked), 'form', or 'none' (random).
function user(n, drive, seed = 1, p = 0.9) {
  let x = seed;
  const rnd = () => (x = (x * 1103515245 + 12345) % 2147483648) / 2147483648;
  const rows = [];
  for (let i = 0; i < n; i++) {
    const musical = rnd() < 0.5, dir = Math.floor(rnd() * 6);
    const people = [];
    for (let c = 0; c < 6; c++) people.push(['出演', `俳優${Math.floor(rnd() * 12)}`]);
    people.push(['演出', `演出家${dir}`], ['#形式', musical ? 'ミュージカル' : '音楽劇']);
    const good = drive === 'form' ? musical : dir < 3;
    const verdict = drive === 'none' ? ['◎', '○', '△', '×'][Math.floor(rnd() * 4)]
      : good ? (rnd() < p ? '◎' : '△') : (rnd() < p ? '×' : '○');
    rows.push({key: `w${i}`, stage_id: `s${i}`, verdict, updated_at: new Date(Date.UTC(2026, 0, 1, 0, 0, i)).toISOString(), people});
  }
  return rows;
}

test('a user who follows directors gets the director-strong rules once the evidence is clear', () => {
  assert.equal(chooseVariant(user(20, 'dir')).variant, 'base', 'too few ratings: keep the default');
  let chosen = 0;
  for (let seed = 1; seed <= 40; seed++) {
    const g = chooseVariant(user(120, 'dir', seed));
    assert.notEqual(g.variant, 'kinds_strong');
    chosen += g.variant === 'author_strong';
  }
  assert.ok(chosen >= 28, `chosen for ${chosen} of 40`);
  const g = chooseVariant(user(120, 'dir', 1));
  assert.deepEqual(g.multipliers, g.variant === 'author_strong' ? {author: 2.5} : {});
});

test('users with no pattern almost always keep the default rules', () => {
  let moved = 0;
  for (let seed = 1; seed <= 200; seed++) moved += chooseVariant(user(120, 'none', seed)).variant !== 'base';
  assert.ok(moved <= 10, `${moved} of 200 moved off the default`);
});

test('when the default already follows the kind of show, nothing changes', () => {
  // Doubling the kind weight orders the same pairs: no clear win, keep base.
  for (let seed = 1; seed <= 10; seed++) assert.equal(chooseVariant(user(120, 'form', seed)).variant, 'base');
});

test('the replay only uses ratings made before each one (predict, then check)', () => {
  // The same records in a different time order give a different check.
  const rows = user(60, 'dir');
  const reversed = rows.map((r, i) => ({...r, updated_at: rows[rows.length - 1 - i].updated_at}));
  assert.notDeepEqual(chooseVariant(rows).checked, chooseVariant(reversed).checked);
});

test('stage scores follow person-ordinal-v3 (people top 3 up and down, plus the mean of kind tags)', () => {
  const rated = [
    {key: 'a', verdict: '◎', people: [['出演', '甲'], ['#形式', 'ミュージカル']]},
    {key: 'b', verdict: '×', people: [['出演', '乙'], ['#形式', '朗読']]},
  ];
  const v = personValues(rated);
  const s = stageScore(v, [['出演', '甲'], ['出演', '乙'], ['#形式', 'ミュージカル']]);
  const exp = v.get('出演\u0000甲')[1] + v.get('出演\u0000乙')[1] + v.get('#形式\u0000ミュージカル')[1];
  assert.ok(Math.abs(s - exp) < 1e-12);
  assert.equal(stageScore(v, [['出演', '知らない人']]), null);
});

// 気になった所: a user who rates by the cast but marks "price" when an
// expensive show disappointed. Using the aspects should predict them better
// than ignoring them, and the check must not switch the aspects off.
function priceUser(n, seed, marks) {
  let x = seed;
  const rnd = () => (x = (x * 1103515245 + 12345) % 2147483648) / 2147483648;
  const rows = [];
  for (let i = 0; i < n; i++) {
    const cast = [0, 1, 2, 3].map(() => Math.floor(rnd() * 16));
    const dir = Math.floor(rnd() * 6), pricey = rnd() < 0.4;
    const people = [...cast.map(c => ['出演', `俳優${c}`]), ['演出', `演出家${dir}`], ['#値段', pricey ? '高い' : '安い']];
    const liked = cast.filter(c => c < 8).length;
    let v = liked >= 3 ? 5 : liked === 2 ? 4 : liked === 1 ? 2 : 1, aspects = [];
    if (pricey && rnd() < 0.7) { v = Math.max(1, v - 2); aspects = ['price']; }
    if (marks === 'random') aspects = rnd() < 0.4 ? [['price', 'acting', 'story', 'venue'][Math.floor(rnd() * 4)]] : [];
    rows.push({key: `w${i}`, stage_id: `s${i}`, verdict: `${v}/5`, aspects, updated_at: new Date(Date.UTC(2026, 0, 1, 0, 0, i)).toISOString(), people});
  }
  return rows;
}

test('marked 気になった所 predict the user better than ignoring them, and stay on', () => {
  let wins = 0, losses = 0;
  for (let seed = 1; seed <= 60; seed++) {
    const g = chooseVariant(priceUser(60, seed, 'price'));
    assert.equal(g.aspects, true, `seed ${seed}`);
    wins += g.checked.aspects_off.wins; losses += g.checked.aspects_off.losses;
  }
  assert.ok(losses > wins * 1.15, `ignoring aspects won ${wins} blocks, lost ${losses}`);
});

test('aspects marked at random can be switched off by the check', () => {
  let wins = 0, losses = 0;
  for (let seed = 1; seed <= 60; seed++) {
    const g = chooseVariant(priceUser(120, seed, 'random'));
    wins += g.checked.aspects_off.wins; losses += g.checked.aspects_off.losses;
    if (!g.aspects) assert.equal(g.variant, 'aspects_off');
  }
  assert.ok(wins > losses, `ignoring random aspects won ${wins} blocks, lost ${losses}`);
});

// 詳細 with good marks: cast and story vary separately and the rating is their
// sum; the user marks the better side "+good" and the worse one a trouble.
function castStoryUser(n, seed) {
  let x = seed;
  const rnd = () => (x = (x * 1103515245 + 12345) % 2147483648) / 2147483648;
  const rows = [];
  for (let i = 0; i < n; i++) {
    const cast = [0, 1, 2].map(() => Math.floor(rnd() * 12)), writer = Math.floor(rnd() * 10);
    const people = [...cast.map(c => ['出演', `俳優${c}`]), ['脚本', `作家${writer}`], ['演出', `演出家${Math.floor(rnd() * 6)}`]];
    const c = cast.filter(k => k < 6).length / 3, w = writer < 5 ? 1 : 0;
    const v = Math.max(1, Math.min(5, Math.round(1 + 2 * c + 2 * w + (rnd() - 0.5))));
    let aspects = [];
    if (rnd() < 0.6) {
      if (c >= 0.66 && !w) aspects = ['+acting', 'story'];
      else if (c <= 0.34 && w) aspects = ['acting', '+story'];
    }
    rows.push({key: `w${i}`, stage_id: `s${i}`, verdict: `${v}/5`, aspects, updated_at: new Date(Date.UTC(2026, 0, 1, 0, 0, i)).toISOString(), people});
  }
  return rows;
}

test('honest good / trouble marks predict the user better than ignoring them', () => {
  let wins = 0, losses = 0;
  for (let seed = 1; seed <= 60; seed++) {
    const g = chooseVariant(castStoryUser(60, seed));
    assert.equal(g.aspects, true, `seed ${seed}`);
    wins += g.checked.aspects_off.wins; losses += g.checked.aspects_off.losses;
  }
  assert.ok(losses > wins * 1.2, `ignoring marks won ${wins} blocks, lost ${losses}`);
});

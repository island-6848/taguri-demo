// src/screens/charts.js gives charts.venue_panel's and charts.spiral_panel's HTML.
import {test} from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {spiralPanel, venuePanel} from '../src/screens/charts.js';

const here = p => new URL(p, import.meta.url).pathname;
const fx = JSON.parse(execFileSync('python3', [here('./screens/charts_fixture.py')], {encoding: 'utf8'}));

function same(got, want, what) {
  if (got === want) return;
  let k = 0; while (k < got.length && got[k] === want[k]) k++;
  assert.fail(`${what}: differs at ${k}\n js: ${got.slice(Math.max(0, k - 100), k + 120)}\n py: ${want.slice(Math.max(0, k - 100), k + 120)}`);
}

test('観劇の年輪 matches charts.spiral_panel', () => {
  fx.spiral.forEach((c, i) => same(spiralPanel(c.works), c.html, `spiral ${i}`));
});

test('よく行く劇場 matches charts.venue_panel', () => {
  fx.venue.forEach((c, i) => same(venuePanel(c.rated), c.html, `venue ${i}`));
});

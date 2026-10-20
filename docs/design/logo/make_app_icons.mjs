// アプリのアイコン（manifest の 192・512 と、Android の丸や角丸に切られても欠けない maskable 512）を、
// make_type.py の icon()（オペラグラス）から作る（起案者 2026-10-20「アプリにしたい」、impl-pwa-base）。
// 使い方: python3 docs/design/logo/make_type.py の icon() を SVG に書き出して渡す
//   node docs/design/logo/make_app_icons.mjs <icon.svg> web/assets/logo
import {readFileSync} from 'node:fs';
import {join} from 'node:path';
import {chromium} from 'playwright';

const [svgPath, outDir] = process.argv.slice(2);
const svg = readFileSync(svgPath, 'utf8');
const BG = '#fbeee2';   // make_type.py の BG（ホーム画面のアイコンと同じ地）
// scale: 絵が占める幅の割合。maskable は中央 80% の円に収める（四隅は切られる）
const jobs = [['icon-192.png', 192, 0.86], ['icon-512.png', 512, 0.86], ['icon-maskable-512.png', 512, 0.62]];
const b = await chromium.launch({executablePath: '/opt/pw-browsers/chromium'});
for (const [name, size, scale] of jobs) {
  const p = await b.newPage({viewport: {width: size, height: size}});
  await p.setContent(`<html><body style="margin:0;width:${size}px;height:${size}px;background:${BG};display:flex;align-items:center;justify-content:center">`
    + `<div style="width:${Math.round(size * scale)}px;height:${Math.round(size * scale)}px">${svg.replace('<svg', '<svg width="100%" height="100%"')}</div></body></html>`);
  await p.screenshot({path: join(outDir, name)});
  await p.close();
}
await b.close();

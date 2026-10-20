// Android のランチャーアイコン（mipmap の各密度）を make_type.py の icon() から作る（plan-app-release、impl-android-twa）。
//   ic_launcher.png: 角の丸い四角に収めた昔の形（Android 7 まで）
//   ic_launcher_foreground.png: Android 8 からの adaptive icon の前景（108dp。中央 66dp に絵を収める。地の色は values/colors.xml）
// 使い方: node docs/design/logo/make_android_icons.mjs <icon.svg> android/app/src/main/res
import {readFileSync, mkdirSync} from 'node:fs';
import {join} from 'node:path';
import {chromium} from 'playwright';

const [svgPath, resDir] = process.argv.slice(2);
const svg = readFileSync(svgPath, 'utf8').replace('<svg', '<svg width="100%" height="100%"');
const BG = '#fbeee2';
const DENS = {mdpi: 1, hdpi: 1.5, xhdpi: 2, xxhdpi: 3, xxxhdpi: 4};
const b = await chromium.launch({executablePath: '/opt/pw-browsers/chromium'});
async function shot(file, size, art, bg, radius) {
  const p = await b.newPage({viewport: {width: size, height: size}});
  await p.setContent(`<html><body style="margin:0;width:${size}px;height:${size}px;background:transparent">`
    + `<div style="width:${size}px;height:${size}px;background:${bg};border-radius:${radius}px;display:flex;align-items:center;justify-content:center">`
    + `<div style="width:${art}px;height:${art}px">${svg}</div></div></body></html>`);
  await p.screenshot({path: file, omitBackground: true});
  await p.close();
}
for (const [d, k] of Object.entries(DENS)) {
  const dir = join(resDir, `mipmap-${d}`);
  mkdirSync(dir, {recursive: true});
  await shot(join(dir, 'ic_launcher.png'), Math.round(48 * k), Math.round(44 * k), BG, Math.round(9 * k));
  await shot(join(dir, 'ic_launcher_foreground.png'), Math.round(108 * k), Math.round(64 * k), 'transparent', 0);
}
await b.close();

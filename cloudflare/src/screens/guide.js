// 一覧が空のときの案内（興味あり・購入済み公演）。起案者の指示 2026-10-18「0 件のときの案内を、おすすめ画面の初めての
// ワンポイントを参考に、イラスト付きの案内にする」。作りは screens/recommend.js の TIPS・tip()（.card.tips）と同じで、
// 絵も同じく使い方ガイドのような線の絵。色は画面の色（--ink2・--surf・--curtain・--wax）だけなので、暗い画面でもそのまま読める

const ART = {
  // 興味あり: 公演の札（カード）と、立てた旗
  interest: `<svg class="tip-art" viewBox="0 0 64 64" width="64" height="64" aria-hidden="true">
<rect x="8" y="12" width="34" height="44" rx="4" fill="var(--surf)" stroke="var(--ink2)" stroke-width="2"/>
<rect x="14" y="18" width="22" height="16" rx="2" fill="var(--ink2)" opacity=".18"/>
<path d="M14 41h22M14 48h14" stroke="var(--ink2)" stroke-width="2" stroke-linecap="round" opacity=".55"/>
<path d="M46 14v40" stroke="var(--ink2)" stroke-width="2" stroke-linecap="round"/>
<path d="M46 14h13l-3.5 6 3.5 6H46z" fill="var(--curtain)"/></svg>`,
  // 購入済み: 切り取り線のある券と、確かめた印
  owned: `<svg class="tip-art" viewBox="0 0 64 64" width="64" height="64" aria-hidden="true">
<path d="M6 18h44v8a6 6 0 0 0 0 12v8H6v-8a6 6 0 0 0 0-12z" fill="var(--surf)" stroke="var(--ink2)" stroke-width="2" stroke-linejoin="round"/>
<path d="M36 20v24" stroke="var(--ink2)" stroke-width="2" stroke-dasharray="3 3" opacity=".55"/>
<path d="M13 27h16M13 34h12" stroke="var(--ink2)" stroke-width="2" stroke-linecap="round" opacity=".55"/>
<circle cx="48" cy="46" r="11" fill="var(--curtain)"/>
<path d="M42.5 46.5l4 4 7-8" fill="none" stroke="var(--surf)" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
};

/** 空のときの案内の枠。art は ART の鍵、text は中の文（<p> を含む HTML）。 */
export const emptyGuide = (art, head, text) => `<section class="card tips eguide">
<div class="tip"><div class="tip-t"><p class="tip-h"><b>${head}</b></p>${text}</div>${ART[art]}</div>
</section>`;

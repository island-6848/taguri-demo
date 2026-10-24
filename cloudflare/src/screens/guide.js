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
  // お気に入り: 名前の札（#）と星（起案者の指示 2026-10-19「お気に入りが１件もないときは、おすすめが１件もないときの画面と同じように
  // アイコンイラストを使ってそのことをわかりやすく説明」）
  favourite: `<svg class="tip-art" viewBox="0 0 64 64" width="64" height="64" aria-hidden="true">
<rect x="6" y="20" width="38" height="16" rx="8" fill="var(--surf)" stroke="var(--ink2)" stroke-width="2"/>
<path d="M14 25l-1.5 6M18.5 25 17 31M11.5 26.8h8M11 29.3h8" stroke="var(--ink2)" stroke-width="1.6" stroke-linecap="round"/>
<path d="M24 28h13" stroke="var(--ink2)" stroke-width="2" stroke-linecap="round" opacity=".55"/>
<rect x="12" y="42" width="26" height="12" rx="6" fill="var(--surf)" stroke="var(--ink2)" stroke-width="2" opacity=".6"/>
<path d="M50 30l3.1 6.3 7 1-5 4.9 1.2 6.9-6.3-3.3-6.3 3.3 1.2-6.9-5-4.9 7-1z" fill="var(--curtain)"/></svg>`,
  // 公演カレンダー: 月の暦と、上演期間の帯（起案者の指示 2026-10-24「公演カレンダーの初期画面、おすすめと同じようにイラスト付きで」）
  calendar: `<svg class="tip-art" viewBox="0 0 64 64" width="64" height="64" aria-hidden="true">
<rect x="6" y="12" width="52" height="44" rx="5" fill="var(--surf)" stroke="var(--ink2)" stroke-width="2"/>
<path d="M6 22h52" stroke="var(--ink2)" stroke-width="2"/>
<path d="M18 8v8M46 8v8" stroke="var(--ink2)" stroke-width="2.4" stroke-linecap="round"/>
<rect x="12" y="28" width="26" height="6" rx="3" fill="var(--curtain)"/>
<rect x="24" y="38" width="28" height="6" rx="3" fill="var(--ink2)" opacity=".35"/>
<rect x="12" y="48" width="18" height="4" rx="2" fill="var(--ink2)" opacity=".2"/></svg>`,
  // 評価一覧: 観た公演の券と、星の評価（起案者の指示 2026-10-24「評価一覧の初期画面、おすすめと同じようにイラスト付きで」）
  rate: `<svg class="tip-art" viewBox="0 0 64 64" width="64" height="64" aria-hidden="true">
<rect x="8" y="10" width="36" height="46" rx="4" fill="var(--surf)" stroke="var(--ink2)" stroke-width="2"/>
<path d="M15 20h22M15 27h16" stroke="var(--ink2)" stroke-width="2" stroke-linecap="round" opacity=".55"/>
<path d="M17 40l1.6 3.3 3.6.5-2.6 2.5.6 3.6-3.2-1.7-3.2 1.7.6-3.6-2.6-2.5 3.6-.5zM30 40l1.6 3.3 3.6.5-2.6 2.5.6 3.6-3.2-1.7-3.2 1.7.6-3.6-2.6-2.5 3.6-.5z" fill="var(--curtain)"/>
<circle cx="48" cy="44" r="11" fill="var(--surf)" stroke="var(--ink2)" stroke-width="2"/>
<path d="M48 38v12M42 44h12" stroke="var(--curtain)" stroke-width="2.6" stroke-linecap="round"/></svg>`,
  // 未評価が 0 件（評価は付いている）: 花束（起案者の指示 2026-10-24「『ご回答ありがとうございました！』のような感謝の文章をイラスト付きで」）
  thanks: `<svg class="tip-art" viewBox="0 0 64 64" width="64" height="64" aria-hidden="true">
<path d="M26 36l-5-12M32 36V20M38 36l5-12" stroke="var(--mute)" stroke-width="2"/>
<circle cx="20" cy="21" r="7" fill="var(--acc)"/><circle cx="20" cy="21" r="2.5" fill="var(--surf)"/>
<circle cx="44" cy="21" r="7" fill="var(--acc)"/><circle cx="44" cy="21" r="2.5" fill="var(--surf)"/>
<circle cx="32" cy="15" r="8" fill="var(--curtain)"/><circle cx="32" cy="15" r="3" fill="var(--surf)"/>
<path d="M19 36h26L32 60z" fill="var(--surf)" stroke="var(--ink2)" stroke-width="2" stroke-linejoin="round"/>
<path d="M25 44q7 6 14 0" stroke="var(--curtain)" stroke-width="2.6" fill="none" stroke-linecap="round"/></svg>`,
};

/** 空のときの案内の枠。art は ART の鍵、text は中の文（<p> を含む HTML）。 */
export const emptyGuide = (art, head, text) => `<section class="card tips eguide">
<div class="tip"><div class="tip-t"><p class="tip-h"><b>${head}</b></p>${text}</div>${ART[art]}</div>
</section>`;

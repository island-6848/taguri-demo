// リンクを X・LINE などに貼ったときのカード（OGP と X のカード。起案者の指示 2026-10-19「Twitterとかで共有した時に出るURLの
// カード設定して」）。どのページも同じ 1 枚: 貼られたリンクはログインの前の人にも見えるので、記録や公演の中身は載せない。
// 画像 public/assets/og.png（1200×630）はログインなしで読める（gate が /assets/ を通す）。og:image は絶対 URL にする
export const CARD = {title: 'たぐり ― 観劇の記録から、次の一本を', image: '/assets/og.png',
  description: '観た演劇の記録と評価から、これから観られる公演の中であなたに合いそうな舞台を毎週届けるアプリです。'};
export const cardMeta = origin => {
  const a = v => String(v).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
  return [['property', 'og:type', 'website'], ['property', 'og:site_name', 'たぐり'], ['property', 'og:title', CARD.title],
    ['property', 'og:description', CARD.description], ['property', 'og:url', origin + '/'], ['property', 'og:image', origin + CARD.image],
    ['property', 'og:image:width', '1200'], ['property', 'og:image:height', '630'], ['property', 'og:image:alt', 'たぐり ― 観たかった舞台を、見逃さない。'],
    ['property', 'og:locale', 'ja_JP'], ['name', 'twitter:card', 'summary_large_image'], ['name', 'twitter:title', CARD.title],
    ['name', 'twitter:description', CARD.description], ['name', 'twitter:image', origin + CARD.image]]
    .map(([k, n, v]) => `<meta ${k}="${n}" content="${a(v)}">`).join('');
};
export function withCard(response, url) {
  if (!(response.headers.get('content-type') || '').includes('text/html') || typeof HTMLRewriter === 'undefined') return response;
  return new HTMLRewriter().on('head', {element(el) { el.append(cardMeta(url.origin), {html: true}); }}).transform(response);
}
// リンクのカードを作りに来るクローラー。ログインしていないので、ふつうは /login へ 302 で送る。送り先を読まないクローラーもあるので、
// ページの道ではその場でログインの画面（カード付き）を返す。ログインの画面は誰でも開けるので、出してよいものは同じ
export const PREVIEW_BOT = /Twitterbot|facebookexternalhit|Facebot|Slackbot|Discordbot|LinkedInBot|line-poker|TelegramBot|WhatsApp|Hatena|SkypeUriPreview|Embedly|Pinterest|redditbot|Mastodon|Bluesky|Cardyb/i;

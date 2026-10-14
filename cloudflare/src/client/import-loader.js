// Loads the calendar / mail import (import.js) only when 「公演情報の登録」① is on
// screen. The screens are drawn into the page after it loads, so watch for it.
const watch = new MutationObserver(() => check());
function check() {
  if (!document.querySelector('[data-import]')) return;
  watch.disconnect();
  import('/vendor/import.js').catch(() => watch.observe(document.body, {childList: true, subtree: true}));
}
watch.observe(document.body, {childList: true, subtree: true});
check();

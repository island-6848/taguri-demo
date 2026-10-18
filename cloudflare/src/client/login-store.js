// メールのリンクでログインするときに、ブラウザーに控えるもの（src/client/login.js が使う）。
// Firebase の手順どおり、リンクを開いたときのためにアドレスを localStorage に置く。あわせて、
// どちらの欄から送ったか（'login' ならアカウントを作らない）と、新規登録の同意の版も置く。
//
// 期限（issue #132）: メールを開かずに離れても、共用の端末にアドレスが長く残らないように、控えた時刻を持ち、
// PENDING_TTL_MS を過ぎた控えは消す（時刻の無い古い控えも消す）。/login を開くたびに expire() を先に呼ぶ。
// 消えたあとにリンクを開いても、アドレスを入力し直せばログインの欄としては続けられる
// （新規登録の欄からだったときは、同意が消えているので、もう一度送り直す）。
// 消す場面: リンクで戻ってきて処理したとき・Google やパスキーを始めたとき・ログアウトしたとき（web/app.js）・期限切れ。
export const EMAIL_KEY = 'taguri_login_email';
export const AGREE_KEY = 'taguri_login_agree';
export const INTENT_KEY = 'taguri_login_intent';
export const SAVED_AT_KEY = 'taguri_login_saved_at';
export const PENDING_KEYS = [EMAIL_KEY, AGREE_KEY, INTENT_KEY, SAVED_AT_KEY];
export const PENDING_TTL_MS = 60 * 60 * 1000;

/** storage: () => localStorage（読めない・書けないブラウザーでは何もしない） */
export function loginStore(storage, now = () => Date.now()) {
  const use = (fn, fallback) => { try { return fn(storage()); } catch { return fallback; } };
  const store = {
    get: () => use(s => s.getItem(EMAIL_KEY) || '', ''),
    set: v => use(s => { s.setItem(EMAIL_KEY, v); s.setItem(SAVED_AT_KEY, String(now())); }),
    clear: () => use(s => { for (const k of PENDING_KEYS) s.removeItem(k); }),
    expire: () => use(s => {
      const at = Number(s.getItem(SAVED_AT_KEY)), age = now() - at;
      const any = [EMAIL_KEY, AGREE_KEY, INTENT_KEY].some(k => s.getItem(k) !== null);
      if (any && !(at > 0 && age >= 0 && age < PENDING_TTL_MS)) store.clear();
    }),
    intent: () => use(s => s.getItem(INTENT_KEY) || 'login', 'login'),
    setIntent: v => use(s => { s.setItem(INTENT_KEY, v); }),
    agree: () => use(s => s.getItem(AGREE_KEY) || undefined, undefined),
    setAgree: v => use(s => { if (v) s.setItem(AGREE_KEY, v); else s.removeItem(AGREE_KEY); }),
  };
  return store;
}

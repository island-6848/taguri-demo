-- 過去の公演のあらすじ（起案者の指示 2026-10-18「あらすじ取れたのなら、日記帳にもそのあらすじ出るようにして」）。
-- あらすじの読み取り（extract_theme_llm、本文に実在するかの検査つき）で取れたものを deliver_past が入れる。
-- 日記帳・評価一覧のカード（screens/rowinfo.js）が、これからの公演のあらすじが無いときに使う。
ALTER TABLE past_stage ADD COLUMN synopsis TEXT NOT NULL DEFAULT '';

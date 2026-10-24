-- 行けばよかったを 1 件ずつ取り消せるようにする（起案者の指示 2026-10-24「行けばよかった、各公演取り消せるようにして」）。
-- 取り消した題名は行を消さずに hidden=1 で残す。興味ありのまま終わって自動で入る分（settings.autoMissed）は、ここに同じ題名の
-- 行があると出さないので、消すと次に開いたときにまた出てしまう。もう一度足すと hidden=0 に戻る
ALTER TABLE missed ADD COLUMN hidden INTEGER NOT NULL DEFAULT 0;

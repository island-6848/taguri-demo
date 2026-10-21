#!/usr/bin/env python3
"""推薦の再生（tools/review/replay_eval.py replay）を、手元のパソコン無しで GitHub Actions の中で動かす。

起案者の指示（2026-10-18）「パソコン環境じゃなくても動かせるようにして」。非公開の taguri-crawler の
Replay のワークフロー（tools/taguri/deploy/github-actions/replay.yml）が、スマートフォンの GitHub から
手で動かす。結果はその実行の画面（Summary）に表で出る。

    python3 cloudflare/scripts/replay_job.py --data data [--owner U] [--step-days 7]

- 利用者の記録は、毎日の控え（backup_d1.py）と同じ表（DERIVED 以外）を D1 から書き出す。読むのは数千行で、
  D1 の無料枠（1 日 500 万行の読み出し）のわずか。REPLAY_MAX_ROWS を越えるなら読まずに止まる。
- 索引は作業データから build_recommend_index.py で、過去の公演（past_stage）は data/past/stages.jsonl から
  手元で作る（D1 から読まない）。
- 書き出した記録は一時ディレクトリに置き、終わったら（失敗しても）消す。作業データ（data/）には書かない
  （data/ は state ブランチに保存されることがある。安全の点検 2026-10-17）。
- 出すのは集計だけ（人数・AUC・p 値）。user_id・公演・名前・感想はログにも Summary にも出さない。
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "tools" / "review"))
import backup_d1 as BK                                             # noqa: E402
import deliver_past as DP                                          # noqa: E402
import replay_eval as RE                                           # noqa: E402
from build_recommend_index import _inserts                         # noqa: E402

REPLAY_MAX_ROWS = 300_000      # 利用者の記録の行数の上限（D1 の 1 日の読み出し 500 万行の 6%。数える分と書き出す分で 2 倍読む）


def past_sql(data: Path, path: Path) -> int:
    """data/past/stages.jsonl の全部を past_stage の INSERT に（deliver_past.row_values と同じ列）。"""
    text = (data / DP.ROWS).read_text(encoding="utf-8") if (data / DP.ROWS).exists() else ""
    themes, synopses = DP.load_themes(data), DP.load_synopses(data)
    rows = [DP.row_values(r, themes, synopses) for r in (json.loads(x) for x in text.split("\n") if x.strip()) if r.get("stage_id") and r.get("title")]
    stmts = [s.replace("INSERT INTO", "INSERT OR REPLACE INTO", 1) for s in
             _inserts("past_stage", DP.COLUMNS, rows)]
    path.write_text("\n".join(stmts) + "\n", encoding="utf-8")
    return len(rows)


def export_records(path: Path) -> int:
    tables = BK.user_tables(BK.remote_tables(BK.DB_NAME))
    rows = sum(BK.remote_counts(BK.DB_NAME, tables).values())
    if rows > REPLAY_MAX_ROWS:
        raise SystemExit(f"利用者の記録が {rows:,} 行あり、上限 {REPLAY_MAX_ROWS:,} 行を越えるので読まない（D1 の無料枠）")
    BK.wrangler("d1", "export", BK.DB_NAME, "--remote", "--output", str(path), *[x for t in tables for x in ("--table", t)])
    return rows


def build_index(path: Path) -> None:
    r = subprocess.run([sys.executable, str(HERE / "build_recommend_index.py"), "--output", str(path)],
                       cwd=ROOT, capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise SystemExit("索引を作れなかった: " + r.stderr.strip()[-400:])


def fmt(v) -> str:
    if v is None:
        return "—"
    return f"{v:.3f}" if isinstance(v, float) else str(v)


def summary(res: dict, counts: dict, mats: dict | None = None, sat: dict | None = None) -> str:
    """集計だけの表（Markdown）。"""
    if "error" in res:
        return f"## 推薦の再生\n\n{res['error']}\n"
    out = ["## 推薦の再生（replay）", "",
           f"- 答え: {res['first_answer']} 〜 {res['last_answer']}、区切り {res['step_days']} 日 × {res['origins']} 回",
           f"- 後で答えた公演のうち、その時点のおすすめ（400 枠）に入っていた割合: {fmt(res['answers_ranked_share'])}",
           f"- たまった数: 利用者 {counts['users']} 人（答え 10 件以上 {counts['users_10_answers']} 人）、答え {counts['answers']} 件"
           f"（開幕リマインド {counts['answers_reminder']} 件）、分析から外れた人 {counts['opted_out']} 人",
           *[f"- 日 {o['t']} まで → その後 {res['step_days']} 日: 答えた人 {o['users']} 人・答え {o['answers']} 件、"
             f"評価が残っていた人 {o['with_ratings']} 人、おすすめが出た人 {o['with_recommendations']} 人"
             + f"、索引: 後で載った公演 {o.get('index_dropped', 0)} 件を外した・後で中身が変わった公演 {o.get('index_changed', 0)} 件"
             + ("（載った日を控える前の日なので、控え始めに載っていた公演は外せていない）" if o.get("index_unknown", True) else "")
             for o in res.get("per_origin", [])],
           "", "AUC は 0.5 が当てずっぽう、1.0 が全部当たり。人数が少ないうちの p 値は偶然の差を拾いやすい。", ""]
    if mats:
        g = lambda k: mats.get(k, 0)
        out += ["### 今の記録のうち、推薦の材料になれている数", "",
                f"- 記録 {g('records')} 件、そのうち評価あり {g('rated')} 件",
                f"- 評価ありのうち: 観た日が今日より先 {g('rated_future')} 件（学ばない）、公演につながっていない {g('rated_unlinked')} 件（学べない）",
                f"- 公演につながっている: これからの索引の公演 {g('linked_index')} 件、過去の公演 {g('linked_past')} 件、公演が見つからない {g('linked_missing')} 件",
                f"- 人物の名前がある {g('with_names')} 件、種類の言葉（題材・形式など）がある {g('with_kinds')} 件、"
                f"感想がある {g('with_note')} 件（そのうち種類の言葉もある {g('with_note_and_kinds')} 件）", ""]
    names = {"reminder": "開幕リマインドの答え（主な結果）", "other": "ほかの画面の答え（参考）", "all": "全部"}
    trials = {"affil": "所属（劇団）から推し量る"}
    parts = {"split": "興味ありの配り分け", "expand": "1 段広げる", "spread": "並べ直し", "gate": "裏の答え合わせ", "impression": "感想の好み", "rollup": "題材の上位への積み上げ"}
    for key, title in names.items():
        e = res[key]
        out += [f"### {title}", "", f"- 利用者 {e['users']} 人・区切り {e['windows']} 回、AUC の中央値 {fmt(e['median_auc'])}、"
                f"H1 の p（符号検定） {fmt(e['p_sign_H1'])}"]
        if "owner" in e:
            out.append(f"- 持ち主（別に出す）: AUC {fmt(e['owner']['auc'])}")
        out += ["", "| 外した部品 (H5) | 差の中央値 | 効いた人 | 逆の人 | p（Holm） |", "|---|---:|---:|---:|---:|"]
        for a, h in e["H5"].items():
            out.append(f"| {parts.get(a, a)} | {fmt(h['median_diff'])} | {h['users_better']} | {h['users_worse']} | {fmt(h['p_holm'])} |")
        out.append("")
        if e.get("H6"):
            out += ["| 足して試した部品 (H6) | 差の中央値（足した − 今） | 当たりが増えた人 | 減った人 | p（Holm） |", "|---|---:|---:|---:|---:|"]
            for t, h in e["H6"].items():
                out.append(f"| {trials.get(t, t)} | {fmt(h['median_diff'])} | {h['users_better']} | {h['users_worse']} | {fmt(h['p_holm'])} |")
            out.append("")
    if res.get("curve"):
        out += ["### 学習曲線: 評価を古いほうから k 件だけ残したとき（#103）", "",
                "同じ区切り・同じ後の答え・同じ索引のまま、日 t までの評価の数だけを変えて測る。k 件以上の評価がある人だけを数える。"
                "全員がいつも良くなるとは限らないので、良くなった人と悪くなった人を両方出す。", "",
                "| 評価の数 k | 人数 | AUC の中央値 | おすすめに入っていた答えの割合 | k=1 より良い人 | 悪い人 | p（符号検定） |",
                "|---|---:|---:|---:|---:|---:|---:|"]
        for c in res["curve"]:
            out.append(f"| {'全部' if c['k'] == 'all' else c['k']} | {c['users']} | {fmt(c['median_auc'])} | {fmt(c['answers_ranked_share'])} | "
                       f"{c['better_than_first']} | {c['worse_than_first']} | {fmt(c['p_sign'])} |")
        out.append("")
    if sat and "error" not in sat:
        miss = sat["missing"]
        out += ["### 観る前の点と、観たあとの評価（H3・#114）", "",
                "H1 は「気になったか」、こちらは「観てよかったか」。観た公演だけを数え、観なかった公演は負例にしない。", "",
                f"- 評価 {sat['rated']} 件のうち、観る前の点と結べた {sat['paired']} 件"
                f"（公演につながっていない {miss['no_stage']} 件・観る前の点が無い {miss['no_score_before']} 件）",
                f"- 結べた公演のうち、観る前に興味あり・購入済と答えていた割合 {fmt(sat['paired_after_positive_share'])}（選んで観た偏り）",
                f"- 利用者 {sat['users']} 人、τ の中央値 {fmt(sat['median_tau'])}、p（符号検定） {fmt(sat['p_sign_H3'])}"
                + (f"、持ち主（別に出す） τ {fmt(sat['owner_tau'])}" if "owner_tau" in sat else ""), ""]
    ga = res.get("gate_affil")
    if ga:
        out += ["### 裏の答え合わせ: 所属（劇団）から推し量る（測るだけ）", "",
                f"- 測れた人 {ga['users']} 人、区切りの勝ち {ga['wins']}・負け {ga['losses']}"
                f"（勝ちが多い人 {ga['users_better']} 人・負けが多い人 {ga['users_worse']} 人）",
                "- 1 人の中で「はっきり良い」とみなすのは、勝ち − 負け ≥ 1.96 √（勝ち＋負け）で、決まった区切りが 6 以上のとき",
                *([f"- 持ち主（別に出す）: 勝ち {ga['owner'].get('wins', 0)}・負け {ga['owner'].get('losses', 0)}"] if ga.get("owner") else []), ""]
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--data", type=Path, default=ROOT / "data")
    ap.add_argument("--owner", default="", help="持ち主の user_id（除いて別に出す。任意）")
    ap.add_argument("--step-days", type=int, default=RE.STEP_DAYS)
    ap.add_argument("--curve", action="store_true", help="学習曲線も出す（#103。区切りごとに 6 回多く計算する）")
    a = ap.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="taguri-replay-") as tmp:
        tmp = Path(tmp)
        records, index, past = tmp / "records.sql", tmp / "index.sql", tmp / "past.sql"
        export_records(records)
        build_index(index)
        past_sql(a.data, past)
        seen_path = a.data / "d1" / "index-hashes.json"      # 公演の載った日（#72。deliver_catalogue.INDEX_HASHES）
        seen = json.loads(seen_path.read_text(encoding="utf-8")) if seen_path.exists() else None
        res = RE.replay(str(records), index, [past], owner=a.owner or None, step_days=a.step_days, seen=seen,
                        curve=RE.CURVE if a.curve else None)
        db = RE.load(str(records))
        counts = RE.counts(db, a.owner or None)
        sat = RE.h3(db, a.owner or None, 1)
        db.close()
        mats = RE.materials(str(records), index, [past], RE.jst_day(datetime.datetime.now(datetime.timezone.utc).isoformat()))
    text = summary(res, counts, mats, sat)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

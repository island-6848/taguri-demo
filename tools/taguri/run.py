#!/usr/bin/env python3
"""「たぐり」の入口。**利用者が行うのは、これを 1 回実行することだけである。**

    python3 tools/taguri/run.py            # 週次。数秒で一覧が開く
    python3 tools/taguri/run.py --fetch    # 月 1 回。材料を取り直す（新規ぶんだけ・約 5 分）
    python3 tools/taguri/run.py --mail     # 購入確認メールの差分も取る（認証が要る）
    python3 tools/taguri/run.py --no-open  # 開かずに終わる（検証・確認用）

## なぜ 1 本にまとめるのか

企画書 5 章は「**常駐プロセスを持たないので定期実行はできない。利用者が行うのは
ショートカットを 1 つ押すことだけ**」と書いているが、実体は 5 つのスクリプトを手で順に
叩く運用だった。**順番を間違えると、古い一覧に新しい反応が付く**（提示の記録が無い反応は
作品単位の抑制が効かず、ツアーの別会場として戻ってくる ── 検証 026）。
**順序そのものが仕様なので、1 本のコードに固定する。**

## 段の並び（企画書 5 章「更新の手順」）

| | 何をするか | いつ走るか |
|---|---|---|
| 1 | 購入確認メールの差分を取り、公演を特定する | `--mail` のとき |
| 2 | 上演が終わって評価が付いていない作品を「評価待ち」に集め、一覧の先頭に出す | 毎回 |
| 3 | 候補を取り直し、**材料の無い記録を題名から公演ページに結び付け**、あらすじを引く（候補側と学習側の両方） | `--fetch` のとき（月 1 回・**前回すでに取れている分は使い回すので約 5 分**） |
| 4 | **お気に入りの名前で公演を直接引く**（母集団の一覧に頼らない） | 毎回・初回だけ約 1 分。**名前を登録した直後にも走る**（`serve.py`） |
| 5 | **ステイジーズカレンダーを取り込む**（網羅を担う側） | 毎回・1 回のダウンロード |
| 6 | 推薦を計算し、**出した一覧を `presented` に保存する** | 毎回 |
| 7 | ポスターの画像を端末内に取り込む | 毎回（差分だけ）。**公演を足した／結び付けた直後にも、その 1 件ぶんが走る**（`enrich.py`） |
| 8 | 記録を見返す画面の材料を組む | 毎回 |
| 9 | `127.0.0.1` に一時プロセスを立てて開き、閉じたら落ちる | `--no-open` 以外 |

**開くのは 1 つのリンクである。** そこから、おすすめ（推薦・お気に入り）・公演情報の登録・
記録を見返す・探す・設定へナビゲーションで移動する（`tools/taguri/app.py`）。
**画面ごとに HTML を書き出して別々に開く形はやめた。**

## 押した直後に走るもの（2026-08-24）

起案者の指示 ──「データベースから公演を拾ってくるのは月 1 でいいけど、それ以外はできる
だけ即時更新にしてほしい。新しく公演を追加したときのポスターとか、すぐ取得してほしい」。

**段 3（母集団を集め直す・約 15 分）だけが月 1 のままである。** それ以外は、押した操作に
結び付いた分をその場で走らせる ── 公演を足した／公演ページに結び付けたときは
その 1 件ぶんの材料（`tools/taguri/enrich.py`）、お気に入りに名前を登録したときは
その名前の公演と一覧の組み直し（`tools/taguri/serve.py` の仕事の列）。
**この段の一覧は、押さなかったぶんを後から拾う網として残る。**

**4 を飛ばして 6 に行けない。** 反応は「その週に出した一覧」に対して付くので、
提示の記録（`presented` の label）が先に無いと書き戻す先が決まらない。

## 途中の段で失敗しても止めない

**取得と取り込みは、外の都合で失敗する**（認証切れ・相手のサーバ・API の枠）。
そこで止めると一覧が開かず、**その週は何も見ないことになる** ── 見逃さないことが
この企画の価値なので、**取れなかったことを画面に出したうえで開くほうが正しい。**
ただし 4 と 5 は失敗したら止める（出すものが無い）。
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
DB = ROOT / "data" / "review" / "ratings.db"
WAITING = ROOT / "data" / "review" / "waiting.json"
HTML = ROOT / "data" / "review" / "recommend.html"
# **本人しか読めない場所に持つもの。** 観劇記録・お気に入り・購入メールから抜いた分。
# `data/credits` は公演ページから拾った公開情報なので対象に含めない
PRIVATE_DIRS = (ROOT / "data" / "review", ROOT / "data" / "tickets")


def _harden_permissions() -> None:
    """**この端末の他アカウントから読めないようにする**（起案者の指摘・2026-08-27）。

    2 つ行う。①この後の全段（`sh()` で起こす子プロセスも含む）が新しく作るファイルを、
    最初から本人だけが読める権限で作る ── `umask` はプロセスの属性として子プロセスに
    そのまま引き継がれるので、ここ 1 か所で以降すべてに効く。②`umask` は「これから
    作るファイル」にしか効かないので、**既にある分は個別に閉じる**（一度きりでよい ──
    次からは umask がそのまま守る）。

    メールの OAuth トークン（`~/.config/nau-mail/google_token_tickets.json`）は
    前からこの権限で保存されていたが、観劇記録・お気に入り・評価は既定のまま
    （誰でも読める権限）だった。
    """
    os.umask(0o077)
    for d in PRIVATE_DIRS:
        if not d.exists():
            continue
        try:
            d.chmod(0o700)
            for p in d.rglob("*"):
                p.chmod(0o700 if p.is_dir() else 0o600)
        except OSError as e:                                           # noqa: BLE001
            print(f"  権限を閉じられなかった（{d}）: {e}")


def step(i: int, name: str) -> None:
    # **溜めずに出す。** 子プロセスの出力は直に端末へ行くので、親が溜めると段の見出しが
    # 実行結果より後に出て、どの段で何が起きたのか読めなくなる
    print(f"\n\033[1m[{i}] {name}\033[0m", flush=True)


# **どの段が通ったかを、画面にも渡す。**
#
# 上に「取れなかったことを画面に出したうえで開くほうが正しい」と書いてありながら、
# **失敗は端末に出るだけだった**（2026-08-24 の指摘）。ショートカットから開いた人は
# 端末を見ないので、**カレンダーを取り込めなかった週も、いつもと同じ一覧が出てくる。**
# 件数が減っていても気づけない。そこで段ごとの結果をここに書き、画面の先頭で出す
# （`tools/taguri/app.py` の `run_status_html`）。
#
# **画面に出す文はここに書かない。** ここが持つのは段の名札だけで、
# 「それができないと何が起きるのか」は使う人の言葉で画面の側に置く。
STATUS = ROOT / "data" / "review" / "run_status.json"
RESULT: dict[str, str] = {}


def sh(cmd: list[str], *, required: bool, tag: str = "") -> bool:
    """1 段を実行する。**必須でない段の失敗は記録して進む**（上記）。"""
    t0 = time.time()
    r = subprocess.run([sys.executable, *cmd], cwd=ROOT)
    dt = time.time() - t0
    if tag:
        RESULT[tag] = "ok" if r.returncode == 0 else "failed"
    if r.returncode == 0:
        print(f"  ── 済（{dt:.1f} 秒）", flush=True)
        return True
    if required:
        save_status()
        raise SystemExit(f"  ── 失敗（この段は飛ばせない）: {' '.join(cmd)}")
    print(f"  ── 失敗したので飛ばす（returncode={r.returncode}）")
    return False


def save_status() -> None:
    """段ごとの結果を書き出す。**飛ばした段は書かない** ── `--fetch` を付けなかった
    ことは失敗ではないので、画面に出す必要がない。"""
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(
        {"at": datetime.datetime.now().isoformat(timespec="seconds"), "steps": RESULT},
        ensure_ascii=False, indent=1), encoding="utf-8")


def waiting(today: str) -> list[dict]:
    """**上演が終わって評価が付いていない作品を集める。**

    通知を送らない構成なので、**次に一覧を開いたときに先頭へ出すことが唯一の催促である**
    （企画書 2 章）。ここが動かないと ◎○△× が貯まらず、名簿が増えない ── 推薦の精度が
    上がる経路そのものが止まる。

    **「まだ判断できない」は評価待ちに戻さない。** 段階とは別に置いた欄で、本人はもう
    答えている（集計では欠測として分母から外す ── 企画書 4 章）。

    **「行かなかった」と答えた公演も並べない**（2026-08-24）。**一度答えたことを聞き直す
    画面にしない** ── 本人が 2026-08-20 に前の画面で答えた 23 回ぶんをこの段が読んで
    いなかったため、**観ていない 7 件が評価待ちの 15 件に混ざっていた。** 観ていない公演に
    評価を付けると、その作り手が名簿に入る（名簿は ◎ を付けた公演から作る）ので、
    **聞き直すことは間違った材料を作る入口でもある。**
    """
    import app as APP
    # **数える規則は画面と同じ 1 か所に置く**（`app.waiting_rows`）。ここに写すと、
    # **控えと画面が違う件数を出す**ようになる（画面は開くたびに数え直している）
    rows = APP.waiting_rows(today)
    WAITING.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return rows


def latest_label() -> str:
    """**いま出した一覧の label を取る。** 反応はこの label に紐づける。

    `recommend2.py` が `presented` に書いた直後の最新行を読む。同じ日に 2 回出すと
    `2026-08-24#2` になる（`feedback.free_label`。上書きせずに残す規則）ので、
    **日付から組み立てずに、書かれた値をそのまま読む。**
    """
    con = sqlite3.connect(DB)
    row = con.execute("SELECT label FROM presented ORDER BY created_at DESC, rowid DESC"
                      " LIMIT 1").fetchone()
    con.close()
    return row[0] if row else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--today", default=datetime.date.today().isoformat())
    ap.add_argument("--top", type=int, default=15)
    ap.add_argument("--fetch", action="store_true",
                    help="候補とあらすじを取り直す（月 1 回・新規と前回空だった分だけ取るので約 5 分）")
    ap.add_argument("--mail", action="store_true",
                    help="購入確認メールの差分を取る（Gmail の認証が要る）")
    ap.add_argument("--no-open", action="store_true", help="画面を開かずに終わる")
    ap.add_argument("--port", type=int, default=0)
    a = ap.parse_args()

    _harden_permissions()
    print(f"\033[1mたぐり\033[0m ── {a.today} 時点の一覧を作る", flush=True)

    step(1, "購入の取り込み" + ("" if a.mail else "（--mail が無いので飛ばす）"))
    if a.mail:
        sh(["tools/tickets/extract_performances.py", "--run"], required=False, tag="mail")
    else:
        # **止まっていることを黙って通さない。** 購入は「興味ありより強い正」であり、
        # 連鎖（提示 → 興味あり → 購入 → ◎）の 3 段目である（問題 D10）
        print("  買ったことは画面の「すでにチケットを持っている」でしか入らない")

    step(2, "評価待ちの洗い出し")
    w = waiting(a.today)
    print(f"  上演が終わって評価が付いていない作品 {len(w)} 件"
          + (f"（最新: {w[0]['title'][:30]}）" if w else ""))

    step(3, "材料の取得" + ("" if a.fetch else "（--fetch が無いので飛ばす）"))
    if a.fetch:
        # **前回すでにクレジットが取れている候補は取り直さない**（2026-08-26・起案者の
        # 指示で見直した）。もとは「取得済みの公演も毎回取り直す」だった ── 初報の
        # 時点ではあらすじもクレジットも載っていないことがあり、未取得だけを取る方式
        # （差分だけを取る形）では一度空で取った公演が 109 日ぶん更新されなかった
        # （企画書 5 章「差分だけを取る形は撤回した」）。**その問題は残したまま**、
        # 「見たことがあるか」ではなく「前回の中身が空だったか」で判定するよう
        # `fetch_candidates.py` 側を直した。前回すでに役職つきクレジットが取れている
        # 候補は使い回し、**新規の候補と、前回空だった候補だけ、これまでどおり毎回
        # 取りに行く**（詳細は `fetch_candidates.py` のコメント）。
        # **`--since-days` は指定しない。** `--keep-days`（既定 180 日）から決まるように
        # したので、ここで固定すると**終わった公演を残す指示だけが効かなくなる**
        # ── 一覧の条件は初日に掛かるため、さかのぼる日数が足りないと 1 件も入らない。
        # **`--today` を渡す。** 渡さないと既定の 2026-08-20 で走り、残す期間の境目が
        # 実行日とずれる
        sh(["tools/review/fetch_candidates.py", "--today", a.today], required=False, tag="candidates")
        # **学習側も一緒に引き直す（`both`）。** 記録に公演を結び付けられるようにしたので、
        # **結び付けた記録のあらすじは、次の取得で取りに行かないと永久に空のままになる**
        # ── 取ることと使える形にすることを別の実行に分けると、片方だけ進んだ状態が
        # 出力に出る。**費用はほぼ増えない** ── 済んだ行は飛ばし、本文が取れない行は
        # LLM を呼ばずに終わる（`extract_theme_llm.py` の `done` / `notext`）
        # **あらすじを引く前に、題名から公演ページを探し直す。** 画面には結び付ける口が
        # あるが、**画面が選べるのは手元の控えにある公演だけ**で、古い公演はどちらの控えにも
        # 無い（控えの 155 行のうち 25 行は題名だけで id を持たない）。**画面から外へは
        # 取りに行かない**ので、この段でしか直せない。**先に置くのは、結び付いた公演の
        # あらすじを同じ 1 回で取るためである** ── 分けると、次の月まで空のままになる
        sh(["tools/credits/link_works.py"], required=False, tag="link")
        sh(["tools/credits/extract_theme_llm.py", "--side", "both"], required=False, tag="themes")
    else:
        print("  手元の候補とあらすじをそのまま使う")

    step(4, "お気に入りの名前で公演を直接引く")
    # **母集団の一覧に頼らない。** 登録した名前は「無条件で出す」と決めた対象なので、
    # 一覧に載っていない公演も引いてくる（企画書 4 章）。**毎回走らせる** ──
    # お気に入りは見逃したくないものなので、月 1 回では最大 4 週遅れる
    sh(["tools/taguri/favourites.py", "--today", a.today], required=False, tag="favourites")

    step(5, "ステイジーズカレンダーの取り込み")
    # **CoRich とほとんど重なっていない。** カレンダーの楽日が今日以降 738 件のうち
    # 470 件は CoRich から集めた候補に無い（企画書 5 章の役割分担 ── 網羅はカレンダー、
    # クレジットは CoRich）。**ダウンロードは 1 回だけなので毎回走らせる。**
    # クレジットは重いので `--fetch` のときだけ辿る
    sh(["tools/taguri/fetch_stage_calendar.py", "--today", a.today]
       + (["--credits"] if a.fetch else []), required=False, tag="calendar")

    step(6, "推薦の計算と、出した一覧の保存")
    sh(["tools/review/recommend2.py", "--today", a.today, "--top", str(a.top)],
       required=True, tag="recommend")
    label = latest_label()
    print(f"  提示の label = {label}")

    step(7, "ポスターの取り込み")
    # **画面から外部サイトを叩かないため、画像もここで端末内に写す**（企画書 5 章の守り 5）。
    # 1 リクエスト／秒なので、新しく出す公演のぶんだけ取る。
    # **`--fetch` のときだけ、手で足す欄の候補のぶんも取る**（起案者の指示・2026-08-24）。
    # 候補 818 件ぶんで約 11 分かかるので毎週は走らせない ── 候補の一覧が入れ替わるのは
    # `--fetch` のときだけなので、そこに寄せれば取りこぼさない
    sh(["tools/taguri/posters.py"] + (["--all-candidates"] if a.fetch else []),
       required=False, tag="posters")

    step(8, "記録を見返す画面の材料を組む")
    # **好みのまとめは新しい判断を足さない。** 推薦の順位を付けるために内部で持っている量を
    # 組み直すだけである（企画書 1 章）。失敗しても推薦の画面は開く
    sh(["tools/review/build_lookback.py"], required=False, tag="lookback")

    # **開く直前に書く。** ここまでの段の結果が出そろっている
    save_status()

    step(9, "画面を開く" + ("（--no-open なので開かない）" if a.no_open else ""))
    if a.no_open:
        # 確認用に 1 枚だけ書き出す。**ボタンは効かない**（トークンが入らない）
        sh(["tools/review/render_recommend.py"], required=False)
        print(f"  確認用の 1 枚: {HTML}")
        print("  **これを直接開いてもボタンは効かない。** 書き戻すには --no-open を外す")
        return 0
    import serve as SV                                              # noqa: N812
    n = SV.serve(label, port=a.port)
    print("\n閉じた ── " + "／".join(
        f"{k} {v} 件" for k, v in
        (("反応", n["react"]), ("評価", n["rate"]), ("感想", n["note"]),
         ("お気に入り", n["fav"]), ("観ればよかった", n["missed"]))))
    if any(n.values()):
        print("次に同じコマンドを実行すると、これが反映された一覧が出る")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

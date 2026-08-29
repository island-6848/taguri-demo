#!/usr/bin/env python3
"""押した直後に、その 1 件ぶんの材料を取りに行く。

    python3 tools/taguri/enrich.py 12345        # 1 公演ぶん（確認用）

## なぜ要るのか ── 「次の起動から」では、押した意味が分からない

起案者の指示（2026-08-24）──「データベースから公演を拾ってくるのは月 1 でいいけど、
それ以外はできるだけ即時更新にしてほしい。新しく公演を追加したときのポスターとか、
すぐ取得してほしい」。

**これまでは、材料を取る仕事が全部 `run.py` の段に寄っていた。** 手で公演を足しても、
公演ページに結び付けても、**ポスターもクレジットも次にシステムを起動し直すまで空**で、
画面には何も起きなかったように見える。しかも `link_works.py` が探すのは
**「評価が付いているのに材料の無い記録」**なので、足したばかりで評価の無い記録は
月 1 回の段でも拾われない ── **押したのに、いつまでも何も付かない。**

## 何を即時にして、何を月 1 のままにするか

| | いつ | なぜ |
|---|---|---|
| 公演の母集団を集め直す（`fetch_candidates`） | **月 1（`--fetch`）** | 1,300 件を辿るので 15 分かかる。起案者の指示どおり据え置く |
| **1 件ぶんの材料**（公演ページ・クレジット・ポスター） | **押した直後** | 外への要求は 2 つで済む。押した人が待てる |
| お気に入りの名前で公演を引く | **押した直後**（`serve.py`） | 名前ごとに貯めるので、増えた 1 名ぶんしか引かない |

## 守り ── 画面から外部サイトを叩かない、は破っていない

企画書 5 章の守り 5 の中身は **ブラウザが外部へ要求を出さないこと**である
（取得の範囲と間隔を 1 か所で守る／どの公演を見たかが相手のサーバに残らない）。
ここで取りに行くのは**端末の中で動いているこちらのプロセス**で、経路も間隔も
更新の段と同じ 1 か所（`fetch_credits.get`・1 リクエスト／秒）を通る。

**そして、画面を開いただけでは取りに行かない。** 走るのは、本人が
「登録する」「結び付ける」「これは追う」を押したときだけである ── 一覧を眺める操作で
外に要求が出ないことは、これまでと変わらない。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("tools/review", "tools/credits", "tools/taguri"):
    sys.path.insert(0, str(ROOT / p))

import posters as PO                                                # noqa: E402


def stage(stage_id, *, work_key: str = "", title: str = "", date: str = "") -> str:
    """1 公演ぶんの材料を取りに行く。**返すのは画面にそのまま出せる 1 行である。**

    **順番に意味がある。** 先に公演ページを取ってからでないとポスターの URL が分からない
    （`posters.poster_url` は控えたページから読む）。取ることと使える形にすることを別の
    実行に分けると、**片方だけ進んだ状態が画面に出る。**

    **すでに手元にあるものは取りに行かない。** 押すたびに同じページを取りに行くと、
    相手のサーバに同じ要求を何度も出すことになる。
    """
    sid = str(stage_id or "").strip()
    if not sid.isdigit():
        return "公演ページに結び付いていないので、材料は取りに行けません"
    done = []
    # ---- 1 クレジット（公演ページの取得を含む）--------------------------------
    # **写す口は 1 つにする。** 手で足す欄で検索して選んだときと同じ `adopt` を呼ぶ
    # （`stage_search.py`）── 同じ控えに 2 通りの書き方があると、読む側が両方を
    # 見なければならなくなる。**控えたページがあれば通信は 0 回で済む。**
    try:
        import stage_search as SS
        r = SS.adopt(sid, work_key=work_key, title=title, date=date)
        if not r.get("ok"):
            done.append(f"クレジットを取れませんでした（{r.get('why', '')[:40]}）")
        elif not r.get("wrote"):
            done.append("クレジットは手元にありました")
        else:
            n = r.get("n_fields") or 0
            done.append(f"クレジットを {n} 欄取り込みました" if n else
                        "公演ページに出演者の欄がありませんでした")
    except Exception as e:                                          # noqa: BLE001
        done.append(f"クレジットを取れませんでした（{type(e).__name__}）")
    # ---- 2 ポスター -----------------------------------------------------------
    if sid in PO.have():
        done.append("ポスターは取り込み済みでした")
    elif not PO.page_of(sid).exists():
        # **公演ページを取れていないときに「ポスターはありません」と書かない。**
        # 画像の URL はページの中にあるので、**ページが無いのは「取れなかった」であって
        # 「無い」ではない** ── 事実でないことを画面に出さない
        done.append("公演ページを取れなかったので、ポスターも取れませんでした")
    else:
        try:
            n = PO.fetch([sid])
            done.append("ポスターを取り込みました" if n.get("取得") else
                        "この公演にポスターはありませんでした"
                        if n.get("画像なし") else "ポスターを取れませんでした")
        except Exception as e:                                      # noqa: BLE001
            done.append(f"ポスターを取れませんでした（{type(e).__name__}）")
    # ---- 3 あらすじ（起案者の指示・2026-08-26 ── 「結び付けたときに自動で
    # クレジットやあらすじを読み取って日記帳上に表示してほしい」）------------------
    # **`work_key` が無いと書けない。** `themes.jsonl` はこの鍵で `_synopsis_by_key`
    # から引かれるので、無ければ書いても読まれない（呼ばずに済ませる）
    if work_key:
        try:
            import extract_theme_llm as TH
            done.append(TH.enrich_one(sid, work_key, title))
        except Exception as e:                                      # noqa: BLE001
            done.append(f"あらすじを取れませんでした（{type(e).__name__}）")
    return "／".join(done)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    print(stage(sys.argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

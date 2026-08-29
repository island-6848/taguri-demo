#!/usr/bin/env python3
"""公演ページから内容を読み取れなかった公演に、**本人が内容を入れる**（2026-08-25）。

## なぜ要るのか

[検証 048](../../docs/verification/048-empty-and-cap.md) で、あらすじが取れなかった候補
344 件の中身を読み直した。**取りこぼしは 0 件で、45% は本文がどこにも書かれていない。**
抽出をどう直しても、書かれていないものは取れない。**残る道は、本人が入れることである。**

起案者の問い ──「『あらすじを取れませんでした』の作品を自分で追加することはできる？」

## 入れられるものは 3 つ

| 入れるもの | 何に効くか |
|---|---|
| **題材の札** | いちばん安い。**システムが推薦に使っているのは札そのもの**なので、あらすじを経由せずに効く |
| **あらすじの本文** | 貼ると、そこから札を読み取る（`extract_theme_llm` と同じ担い手）。文章も画面に出る |
| **公演ページの URL** | 公式サイトの欄が X やリンク集を指している公演（空だったうちの 23%）に効く。**探すのは機械がやる** |

## 機械と手入力のどちらを採るか

**起案者の判断（2026-08-25）── 機械が取れたら、そちらに入れ替える。**
初報の時点では本文が載っていない公演があり、あとから載ることがあるので、
**最新のページに追随できるほうを採る**という判断である。
**引き換えに、手で入れた内容は機械が取れた時点で画面から消える** ── 消えるのは表示であって、
この控えは残るので、機械が取れなくなればまた出てくる。

**空欄と「消す」を分ける。** `None` を渡した欄は触らない。`""` を渡した欄だけ消える。

    python3 tools/review/hand_themes.py            # 手で入れた分を一覧する
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILE = ROOT / "data" / "review" / "hand_themes.json"

MAX_SYNOPSIS = 1200
MAX_WORDS = 12
MAX_WORD = 24
# **出演者・作り手の欄。** `tools/taguri/app.py` の `HAND_FIELDS` と同じ役職名にする
# （役職名がずれると、`measure_nets.parse_credits` が読み分けられない）
CAST_ROLES = ("出演", "演出", "脚本", "スタッフ")
MAX_FIELD = 2000


def load() -> dict[str, dict]:
    """{公演の id: {synopsis, elements, url, at}} を返す。"""
    if not FILE.exists():
        return {}
    try:
        d = json.loads(FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    rows = d.get("stages") if isinstance(d, dict) else None
    return rows if isinstance(rows, dict) else {}


def _write(rows: dict[str, dict]) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps({"stages": rows}, ensure_ascii=False, indent=1),
                    encoding="utf-8")


def save(stage_id: str, *, synopsis: str | None = None,
         words: list[str] | None = None, url: str | None = None,
         fields: dict | None = None) -> dict:
    """1 公演ぶんを書く。**`None` の欄は触らず、`""`（空の一覧）を渡した欄だけ消える。**"""
    sid = str(stage_id or "").strip()
    if not sid:
        raise ValueError("公演の id が要る")
    rows = load()
    row = dict(rows.get(sid) or {})
    if synopsis is not None:
        row["synopsis"] = " ".join(str(synopsis).split())[:MAX_SYNOPSIS]
    if words is not None:
        # **kind は付けない。** 網 C は kind を落として語だけで照合するので（`net_c.words`）、
        # 本人に「これは題材か舞台設定か」を選ばせる意味が無い。
        seen: set[str] = set()
        keep: list[dict] = []
        for w in words:
            w = str(w or "").strip().lstrip("#＃").strip()[:MAX_WORD]
            if w and w not in seen:
                seen.add(w)
                keep.append({"kind": "題材", "word": w})
        row["elements"] = keep[:MAX_WORDS]
    if url is not None:
        u = str(url).strip()
        if u and not u.startswith(("http://", "https://")):
            raise ValueError("http から始まる URL を入れてください")
        row["url"] = u[:400]
    if fields is not None:
        row["fields"] = {k: str(fields.get(k) or "").strip()[:MAX_FIELD]
                         for k in CAST_ROLES if str(fields.get(k) or "").strip()}
    row = {k: v for k, v in row.items() if v not in ("", [], None, {})}
    row["at"] = datetime.date.today().isoformat()
    if len(row) <= 1:                       # 中身が無くなったら行ごと消す
        rows.pop(sid, None)
    else:
        rows[sid] = row
    _write(rows)
    return rows.get(sid, {})


def merge_fields(machine: dict | None, hand: dict | None) -> dict:
    """公演ページのクレジットに、手で入れた出演者・作り手を**足す。**

    起案者の判断（2026-08-26）── あらすじと違い、出演者は機械が取れていても
    足す。公演ページの抽出は役職ごとに 1 行しか拾えない書式があり（実測 ──
    「出演」が 1 行に 1 名ずつ何行も続く公式サイトで、複数名いても 1 名しか
    拾えていなかった）、**取れている＝全員取れているとは限らない。** 消さずに
    足すことで、抽出が漏らした分だけを補える。
    """
    out = dict(machine or {})
    for role, names in (hand or {}).items():
        if not names:
            continue
        out[role] = f"{out[role]}、{names}" if out.get(role) else names
    return out


def blend(machine: dict | None, hand: dict | None) -> dict:
    """機械の抽出に手入力を重ねる。**手で入れた欄があれば、そちらを優先する。**

    ## 2026-08-25 の判断を覆す（2026-08-26・起案者の指示）

    前は「機械が取れている欄は機械が勝つ」だった ── 初報の時点では本文が
    載っていない公演があり、あとから載ることがあるので、最新のページに
    追随できるほうを採るという判断だった。**この前提は「機械の抽出は空か、
    いずれ正しく埋まる」というものだった。**

    その前提が崩れた。**機械の抽出は空でなくても間違っていることがある**
    （実測 ── 出演者が 1 行に 1 名ずつ何行も続く公式サイトで、複数名いても
    1 名しか拾えていなかった）。「機械が勝つ」ままだと、**間違いに気づいて
    手で直しても、その場では直ったように見えて次の読み込みで機械の間違った
    値に戻ってしまう。** 起案者の指示で、手で入れた分がある欄はそちらを常に
    優先し、**空の欄だけ機械の抽出を使う**（＝機械には空の欄を埋める仕事を
    引き続き任せる）形に変えた。

    重ねた欄には `*_by` を立てる ── **画面で出典を「自分で入れた」と書けるようにする**
    ためである（公演ページの本文と照らす検査は、手で入れた文には当たらない）。
    """
    out = dict(machine or {})
    if not hand:
        return out
    if (hand.get("synopsis") or "").strip():
        out["synopsis"] = hand["synopsis"]
        out["synopsis_by"] = "手入力"
    if hand.get("elements") or []:
        out["elements"] = hand["elements"]
        out["elements_by"] = "手入力"
    return out


def apply(themes: dict) -> dict:
    """`{(side, id): 行}` の候補側に手入力を重ねて返す。**学習側には重ねない**
    ── 手で入れる口は候補の札にしか無い（記録側は「公演ページに結び付ける」が担う）。"""
    hand = load()
    if not hand:
        return themes
    out = dict(themes)
    for sid, h in hand.items():
        key = ("candidate", str(sid))
        out[key] = blend(out.get(key) or {"side": "candidate", "id": str(sid),
                                          "synopsis": "", "elements": []}, h)
    return out


def _llm():
    """抽出の部品を局所で読み込む。**相互参照を避けるため、関数の中で読む。**"""
    import sys
    sys.path.insert(0, str(ROOT / "tools" / "credits"))
    import extract_theme_llm as E
    return E


def read_content(stage_id: str, title: str, text: str) -> tuple[str, list[str]]:
    """**貼られた本文から、あらすじと題材の札を読み取る。**

    担い手は抽出と同じ（`extract_theme_llm.ask`）で、**同じ指示・同じ版を使う** ──
    公演ページから取った札と、貼った本文から取った札で語の作り方が変わると、
    持ち上がりを数える母数が揃わなくなる。

    **読み取れなくても失敗にしない。** 貼った本文はそれ自体が画面に出るし、
    申告した題材との照合にも使われる（`net_c.declared_hits`）。
    """
    E = _llm()
    got = E.ask([{"id": str(stage_id), "title": title or "", "text": text}],
                E.MODEL, E.PROMPT_VERSION)
    for g in got:
        if isinstance(g, dict) and str(g.get("id")) == str(stage_id):
            return ((g.get("synopsis") or "").strip(),
                    [e["word"] for e in (g.get("elements") or [])
                     if isinstance(e, dict) and e.get("word")])
    return "", []


def fetch_text(url: str) -> str:
    """貼られた URL のページを取ってきて、本文だけにする。

    **経路は取得の段と同じ 1 か所を通る**（`fetch_credits.get`・1 リクエスト／秒）。
    画面から外部サイトを叩いているのではなく、**端末の中のこちらのプロセスが辿る**
    （企画書 5 章の守り 5 は、`tools/taguri/enrich.py` と同じ理由でそのままである）。
    """
    E = _llm()
    html, err = E.get(url)
    if not html:
        raise ValueError(f"そのページを取れませんでした（{err or '応答なし'}）")
    return E.prep(html, 5000)


def extract_to_themes(stage_id: str, title: str, url: str) -> dict:
    """貼られた URL のページを取りに行って抽出し、**機械の抽出として控えに残す。**

    **手入力の控えではなく `themes.jsonl` に書く。** URL を貼り直すことは
    「**取りに行く先を直す**」ことであって、内容を人が書くことではない ──
    出典の照合（`render_recommend.synopsis_source`）も、取ってきたページの控えに当たる。
    **人がやるのは探すところまでで、辿って読むのは機械である。**
    """
    import datetime as _dt
    import json as _json
    E = _llm()
    text = fetch_text(url)
    got = E.ask([{"id": str(stage_id), "title": title or "", "text": text}],
                E.MODEL, E.PROMPT_VERSION)
    g = next((x for x in got if isinstance(x, dict) and str(x.get("id")) == str(stage_id)), None)
    if g is None:
        return {"ok": False, "said": "そのページからは読み取れませんでした"}
    syn = (g.get("synopsis") or "")[:400]
    els = [e for e in (g.get("elements") or [])
           if isinstance(e, dict) and e.get("word")][:E.MAX_ELEMENTS.get(E.PROMPT_VERSION, 5)]
    if syn and not E.verbatim(syn, text):       # **本文に無いものは落とす**（製品と同じ）
        syn, els = "", []
    with E.OUT.open("a", encoding="utf-8") as fp:
        fp.write(_json.dumps({"side": "candidate", "id": str(stage_id), "title": title or "",
                              "url": url, "synopsis": syn, "elements": els, "reason": "",
                              "model": E.MODEL, "prompt_version": E.PROMPT_VERSION,
                              "at": _dt.date.today().isoformat()}, ensure_ascii=False) + "\n")
    return {"ok": bool(syn or els), "synopsis": syn,
            "words": [e["word"] for e in els]}


def main() -> int:
    rows = load()
    if not rows:
        print("手で入れた内容はまだありません")
        return 0
    print(f"手で入れた公演 {len(rows)} 件")
    for sid, r in sorted(rows.items()):
        ws = "／".join(e["word"] for e in (r.get("elements") or []))
        print(f"  {sid:<10} 札 {ws or 'なし':<28} "
              f"あらすじ {len(r.get('synopsis') or '')} 字 "
              f"{'URL 差し替えあり' if r.get('url') else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

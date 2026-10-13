#!/usr/bin/env python3
"""調べたこと・今後調べること・決めたことを、ナレッジグラフとしてまとめる。

    python3 tools/knowledge/build_graph.py          # 索引と図を作り直す
    python3 tools/knowledge/build_graph.py --check  # 壊れた参照・古い索引があれば失敗（CI）

1 件 = 1 ファイル（`docs/knowledge/notes/<id>.md`）。冒頭に属性とつながりを書く:

    ---
    id: render-free-no-disk
    type: finding
    status: confirmed
    date: 2026-10-13
    title: Render の無料プランは永続ディスクを付けられない
    sources:
      - https://render.com/docs/free
    links:
      - supports: decision-vm-cloudflare
      - affects: comp-serve-cloud
    ---
    本文（何を調べ、何が分かり、何が分からないか）

ここから `docs/knowledge/README.md`（一覧と図）と `docs/knowledge/graph.json` を作る。
`docs/*.md` の本文で `〔id〕` と書けば項目を指せる（無い id を指すと失敗する）。
この 2 つは手で直さない。標準ライブラリだけで動かす（`tools/README.md` の方針）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs" / "knowledge"
NOTES = BASE / "notes"
INDEX = BASE / "README.md"
GRAPH = BASE / "graph.json"

TYPES = {
    "finding": ("調べたこと", {"confirmed", "unverified", "outdated"}),
    "question": ("今後調べること", {"open", "answered", "dropped"}),
    "decision": ("決めたこと", {"adopted", "proposed", "superseded"}),
    "component": ("仕組みの部品", {"current", "planned", "retired"}),
}
RELS = {
    "supports": "根拠になる",
    "contradicts": "食い違う",
    "raises": "新たな問いを生む",
    "answers": "答える",
    "affects": "影響する",
    "depends_on": "前提にする",
    "supersedes": "置き換える",
    "verifies": "検証項目",
}
STATUS_LABEL = {
    "confirmed": "確認済み", "unverified": "未確認", "outdated": "古い",
    "open": "未着手", "answered": "回答済み", "dropped": "取り下げ",
    "adopted": "採用", "proposed": "提案", "superseded": "置き換え済み",
    "current": "現行", "planned": "予定", "retired": "廃止",
}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REQUIRED = ("id", "type", "status", "date", "title")


class NoteError(ValueError):
    pass


def parse(path: Path) -> dict:
    """冒頭の `---` で囲んだ属性を読む。使う形はこの文書の冒頭に書いた範囲だけ。"""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        raise NoteError(f"{path.name}: 冒頭の --- が無い")
    head, body = m.group(1), m.group(2).strip()
    note: dict = {"sources": [], "links": [], "verifies": [], "body": body, "file": path.name}
    key = None
    for raw in head.splitlines():
        if not raw.strip():
            continue
        if raw.startswith("  - ") or raw.startswith("- "):
            if key not in ("sources", "links", "verifies"):
                raise NoteError(f"{path.name}: 一覧を取れない項目 {key!r}")
            item = raw.split("- ", 1)[1].strip()
            if key == "links":
                rel, _, target = item.partition(":")
                note["links"].append((rel.strip(), target.strip()))
            else:
                note[key].append(item)
            continue
        k, sep, v = raw.partition(":")
        if not sep:
            raise NoteError(f"{path.name}: 読めない行 {raw!r}")
        key = k.strip()
        if v.strip():
            note[key] = v.strip()
    for k in REQUIRED:
        if not note.get(k):
            raise NoteError(f"{path.name}: {k} が無い")
    return note


def load() -> list[dict]:
    notes = [parse(p) for p in sorted(NOTES.glob("*.md"))]
    errors = []
    ids = {}
    for n in notes:
        if not ID_RE.match(n["id"]):
            errors.append(f"{n['file']}: id の形が違う")
        if n["file"] != n["id"] + ".md":
            errors.append(f"{n['file']}: ファイル名と id が違う")
        if n["id"] in ids:
            errors.append(f"{n['file']}: id が重複（{ids[n['id']]}）")
        ids[n["id"]] = n["file"]
        if n["type"] not in TYPES:
            errors.append(f"{n['file']}: type は {sorted(TYPES)} のどれか")
        elif n["status"] not in TYPES[n["type"]][1]:
            errors.append(f"{n['file']}: {n['type']} の status は {sorted(TYPES[n['type']][1])} のどれか")
        if not DATE_RE.match(n["date"]):
            errors.append(f"{n['file']}: date は YYYY-MM-DD")
        if n["type"] == "finding" and n["status"] == "confirmed" and not n["sources"]:
            errors.append(f"{n['file']}: 確認済みの調べたことには sources が要る")
    for n in notes:
        for rel, target in n["links"]:
            if rel not in RELS:
                errors.append(f"{n['file']}: つながりの種類 {rel!r} は {sorted(RELS)} のどれか")
            if target not in ids:
                errors.append(f"{n['file']}: つながり先 {target!r} が無い")
            if target == n["id"]:
                errors.append(f"{n['file']}: 自分自身へのつながり")
    for n in notes:
        if n["type"] == "question" and n["status"] == "answered":
            if not any(rel == "answers" and t == n["id"] for m in notes for rel, t in m["links"]):
                errors.append(f"{n['file']}: 回答済みなのに、答える調べたこと（answers）が無い")
    if errors:
        raise NoteError("\n".join(errors))
    return notes


REF_RE = re.compile(r"〔([a-z0-9][a-z0-9-]*)〕")


def check_refs(notes: list[dict]) -> list[str]:
    """`docs/*.md` の本文から `〔id〕` で指した項目が、ナレッジグラフにあるか。"""
    ids = {n["id"] for n in notes}
    out = []
    for doc in sorted((ROOT / "docs").glob("*.md")):
        for ref in REF_RE.findall(doc.read_text(encoding="utf-8")):
            if ref not in ids:
                out.append(f"{doc.relative_to(ROOT)}: 〔{ref}〕 がナレッジグラフに無い")
    return out


def graph_json(notes: list[dict]) -> str:
    data = {
        "version": "taguri-knowledge-v1",
        "nodes": [{k: n.get(k) for k in ("id", "type", "status", "date", "title", "sources", "verifies")}
                  for n in notes],
        "edges": [{"from": n["id"], "rel": rel, "to": t} for n in notes for rel, t in n["links"]],
    }
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def _label(s: str) -> str:
    return s.replace('"', "'").replace("[", "（").replace("]", "）")


def mermaid(notes: list[dict]) -> str:
    key = {n["id"]: f"n{i}" for i, n in enumerate(notes)}
    shape = {"finding": ('("', '")'), "question": ('{{"', '"}}'),
             "decision": ('[["', '"]]'), "component": ('[/"', '"/]')}
    lines = ["```mermaid", "flowchart LR"]
    for n in notes:
        a, b = shape[n["type"]]
        lines.append(f"  {key[n['id']]}{a}{_label(n['title'])}{b}")
    for n in notes:
        for rel, t in n["links"]:
            lines.append(f"  {key[n['id']]} -- {RELS[rel]} --> {key[t]}")
    for n in notes:
        lines.append(f"  class {key[n['id']]} {n['type']}_{n['status']}")
    lines += [
        "  classDef finding_confirmed fill:#e6f4ea,stroke:#2e7d32",
        "  classDef finding_unverified fill:#fff8e1,stroke:#b26a00,stroke-dasharray:4 3",
        "  classDef finding_outdated fill:#eeeeee,stroke:#9e9e9e",
        "  classDef question_open fill:#fdecea,stroke:#c62828",
        "  classDef question_answered fill:#eeeeee,stroke:#9e9e9e",
        "  classDef question_dropped fill:#eeeeee,stroke:#9e9e9e",
        "  classDef decision_adopted fill:#e3f2fd,stroke:#1565c0",
        "  classDef decision_proposed fill:#e3f2fd,stroke:#1565c0,stroke-dasharray:4 3",
        "  classDef decision_superseded fill:#eeeeee,stroke:#9e9e9e",
        "  classDef component_current fill:#f3e5f5,stroke:#6a1b9a",
        "  classDef component_planned fill:#f3e5f5,stroke:#6a1b9a,stroke-dasharray:4 3",
        "  classDef component_retired fill:#eeeeee,stroke:#9e9e9e",
        "```",
    ]
    return "\n".join(lines)


def index_md(notes: list[dict]) -> str:
    by = {n["id"]: n for n in notes}
    incoming: dict[str, list[tuple[str, str]]] = {}
    for n in notes:
        for rel, t in n["links"]:
            incoming.setdefault(t, []).append((rel, n["id"]))

    def link(i: str) -> str:
        return f"[{by[i]['title']}](notes/{i}.md)"

    def rels(n: dict) -> str:
        out = [f"{RELS[r]} → {link(t)}" for r, t in n["links"]]
        out += [f"{link(s)} が{RELS[r]}" for r, s in incoming.get(n["id"], [])]
        return "<br>".join(out) or "─"

    parts = [
        "# たぐり ナレッジグラフ",
        "",
        "調べたこと・今後調べること・決めたことを 1 件ずつ記録し、つながりで管理する。",
        "**このファイルと `graph.json` は `tools/knowledge/build_graph.py` が作る。手で直さない。**",
        "",
        "## 書き足し方",
        "",
        "1. `docs/knowledge/notes/<id>.md` を作る（形は `tools/knowledge/build_graph.py` の冒頭）",
        "2. 調べたら `type: finding`。出典 URL を `sources` に、確かめた日を `date` に書く。"
        "一次情報（公式文書・実物の確認）で確かめたものだけ `confirmed`。ブログや推測は `unverified`",
        "3. 分からないことは `type: question`（`open`）。答えが出たら答えの finding に "
        "`answers: <問いの id>` を書き、問いを `answered` にする",
        "4. 古くなった事実は消さずに `outdated`、取り消した決定は `superseded` にして、新しい方から `supersedes` でつなぐ",
        "5. 計画などの文書（`docs/*.md`）から項目を指すときは `〔id〕` と書く。無い id を指すと検査で失敗する",
        "6. `python3 tools/knowledge/build_graph.py` で索引と図を作り直してからコミットする（CI が `--check` で確かめる）",
        "",
        "つながりの種類: " + "、".join(f"`{k}`（{v}）" for k, v in RELS.items()),
        "",
        "## 図",
        "",
        "形: 丸＝調べたこと、六角＝今後調べること、二重枠＝決めたこと、平行四辺形＝仕組みの部品。"
        "点線の枠は未確認・提案中。灰色は古い・回答済み・置き換え済み。",
        "",
        mermaid(notes),
        "",
    ]
    order = [("question", "open"), ("decision", None), ("finding", None), ("component", None), ("question", "closed")]
    for typ, which in order:
        rows = [n for n in notes if n["type"] == typ]
        if typ == "question":
            rows = [n for n in rows if (n["status"] == "open") == (which == "open")]
            head = "今後調べること" if which == "open" else "答えの出た問い・取り下げた問い"
        else:
            head = TYPES[typ][0]
        if not rows:
            continue
        rows.sort(key=lambda n: (n["status"], n["date"], n["id"]))
        parts += [f"## {head}（{len(rows)} 件）", "",
                  "| 項目 | 状態 | 日付 | 検証項目 | つながり |", "| --- | --- | --- | --- | --- |"]
        for n in rows:
            parts.append(f"| {link(n['id'])} | {STATUS_LABEL[n['status']]} | {n['date']} | "
                         f"{', '.join(n['verifies']) or '─'} | {rels(n)} |")
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="書き出さず、壊れた参照・古い索引で失敗する")
    a = ap.parse_args()
    try:
        notes = load()
    except NoteError as e:
        print(e, file=sys.stderr)
        return 1
    bad_refs = check_refs(notes)
    if bad_refs:
        print("\n".join(bad_refs), file=sys.stderr)
        return 1
    want = {INDEX: index_md(notes), GRAPH: graph_json(notes)}
    if a.check:
        stale = [p.name for p, text in want.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
        if stale:
            print("索引が古い: " + ", ".join(stale) + "（build_graph.py を実行してコミットする）", file=sys.stderr)
            return 1
        print(f"ok: {len(notes)} 件・つながり {sum(len(n['links']) for n in notes)} 本")
        return 0
    for p, text in want.items():
        p.write_text(text, encoding="utf-8")
    print(f"{len(notes)} 件を書き出した: {INDEX.relative_to(ROOT)}, {GRAPH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

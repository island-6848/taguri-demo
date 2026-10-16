#!/usr/bin/env python3
"""調べたことをナレッジグラフへ記録し忘れないための Claude Code のフック（.claude/settings.json）。

    research  … WebSearch・WebFetch の後。調べた内容を控え（.claude/knowledge-inbox.jsonl）に足し、
                記録するよう促す
    rebuild   … Write・Edit の後。docs/knowledge/notes/ が変わったら索引と図を作り直す
    stop      … 応答を終える前。記録していない調べものが残っているか、索引が壊れていれば止める
    dismiss   … 控えを空にする（記録するまでもない調べものだったとき。手で実行する）

控えは作業環境ごとのもので、リポジトリには入れない（.gitignore）。
調べたあとにノートを 1 件でも書けば（ノートの更新時刻が調べた時刻より新しければ）記録済みとみなす。
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOTES = ROOT / "docs" / "knowledge" / "notes"
INBOX = ROOT / ".claude" / "knowledge-inbox.jsonl"
URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+")

sys.path.insert(0, str(Path(__file__).resolve().parent))


def _read_stdin() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}


def _emit(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=False))


def _entries() -> list[dict]:
    if not INBOX.exists():
        return []
    out = []
    # **`splitlines()` で割らない。** U+2028 でも割れるが、`json.dumps(ensure_ascii=False)` は
    # それを escape しないので、1 件が 2 つに割れて読めなくなる（test_rate_performances の検査）
    for line in INBOX.read_text(encoding="utf-8").split("\n"):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _write(entries: list[dict]) -> None:
    INBOX.parent.mkdir(parents=True, exist_ok=True)
    INBOX.write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in entries), encoding="utf-8")


def research(payload: dict) -> int:
    tool = payload.get("tool_name", "")
    ti = payload.get("tool_input") or {}
    what = ti.get("query") or ti.get("url") or ""
    urls = URL_RE.findall(json.dumps(payload.get("tool_response") or "", ensure_ascii=False))
    if ti.get("url"):
        urls.insert(0, ti["url"])
    entries = _entries()
    entries.append({"at": time.time(), "tool": tool, "what": str(what)[:300],
                    "urls": list(dict.fromkeys(urls))[:20]})
    _write(entries)
    _emit({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": (
        "【ナレッジグラフ】この調べもので分かったこと・分からなかったことを docs/knowledge/notes/ に記録する"
        "（finding は出典と日付つき。一次情報で確かめたものだけ confirmed。新しい問いは question）。"
        "書いたら python3 tools/knowledge/build_graph.py。詳しくは CLAUDE.md。")}})
    return 0


def rebuild(payload: dict) -> int:
    ti = payload.get("tool_input") or {}
    path = str(ti.get("file_path") or (payload.get("tool_response") or {}).get("filePath") or "")
    if "docs/knowledge/notes/" not in path:
        return 0
    import build_graph as G
    try:
        notes = G.load()
    except G.NoteError as e:
        _emit({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                      "additionalContext": f"【ナレッジグラフ】ノートに誤りがある:\n{e}"}})
        return 0
    G.INDEX.write_text(G.index_md(notes), encoding="utf-8")
    G.GRAPH.write_text(G.graph_json(notes), encoding="utf-8")
    return 0


def pending(entries: list[dict]) -> list[dict]:
    """まだ記録していない調べもの。調べた後にノートが更新されていれば記録済みとみなす。"""
    newest = max((p.stat().st_mtime for p in NOTES.glob("*.md")), default=0.0)
    sources = " ".join(p.read_text(encoding="utf-8") for p in NOTES.glob("*.md"))
    return [e for e in entries
            if e.get("at", 0) > newest and not any(u in sources for u in e.get("urls") or [])]


def stop(payload: dict) -> int:
    import build_graph as G
    problems = []
    left = pending(_entries())
    if left:
        shown = "\n".join(f"- {e.get('tool')}: {e.get('what')}" for e in left[-8:])
        problems.append(f"記録していない調べものが {len(left)} 件ある:\n{shown}\n"
                        "docs/knowledge/notes/ に記録する（記録するまでもなければ "
                        "`python3 tools/knowledge/hook.py dismiss`）。")
    else:
        _write([])          # 記録済みの控えは捨てる
    try:
        notes = G.load()
        stale = [p.name for p, text in ((G.INDEX, G.index_md(notes)), (G.GRAPH, G.graph_json(notes)))
                 if not p.exists() or p.read_text(encoding="utf-8") != text]
        if stale:
            problems.append("索引が古い。`python3 tools/knowledge/build_graph.py` を実行する。")
        bad = G.check_refs(notes)
        if bad:
            problems.append("文書の〔id〕の指し間違い:\n" + "\n".join(bad))
    except G.NoteError as e:
        problems.append(f"ノートに誤りがある:\n{e}")
    if not problems:
        return 0
    reason = "【ナレッジグラフ】" + "\n".join(problems)
    if payload.get("stop_hook_active"):
        # 2 度目は止めない（終わらなくなるのを防ぐ）。気付けるように表示だけする
        _emit({"systemMessage": reason})
        return 0
    _emit({"decision": "block", "reason": reason})
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "dismiss":
        _write([])
        print("控えを空にした")
        return 0
    payload = _read_stdin()
    handler = {"research": research, "rebuild": rebuild, "stop": stop}.get(cmd)
    if handler is None:
        print(__doc__, file=sys.stderr)
        return 2
    return handler(payload)


if __name__ == "__main__":
    raise SystemExit(main())

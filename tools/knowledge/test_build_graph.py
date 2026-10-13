"""ナレッジグラフの検査（壊れた参照・決まりの破れ・古い索引を見逃さない）。

    python3 tools/knowledge/test_build_graph.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_graph as G                                              # noqa: E402


def write(d: Path, id: str, head: str, body: str = "本文") -> None:
    (d / f"{id}.md").write_text(f"---\nid: {id}\n{head}\n---\n{body}\n", encoding="utf-8")


class Graph(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.notes = base / "notes"
        self.notes.mkdir()
        self.patches = [patch.object(G, "NOTES", self.notes), patch.object(G, "INDEX", base / "README.md"),
                        patch.object(G, "GRAPH", base / "graph.json"), patch.object(G, "ROOT", base)]
        for p in self.patches:
            p.start()
        write(self.notes, "q-a", "type: question\nstatus: answered\ndate: 2026-10-13\ntitle: 問い")
        write(self.notes, "f-a", "type: finding\nstatus: confirmed\ndate: 2026-10-13\ntitle: 答え\n"
                                 "sources:\n  - https://example.com\nlinks:\n  - answers: q-a")

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def test_valid_notes_build_and_check(self):
        with patch.object(sys, "argv", ["x"]):
            self.assertEqual(G.main(), 0)
        with patch.object(sys, "argv", ["x", "--check"]):
            self.assertEqual(G.main(), 0)
        self.assertIn("答える", (Path(self.tmp.name) / "README.md").read_text(encoding="utf-8"))

    def test_stale_index_fails_check(self):
        with patch.object(sys, "argv", ["x"]):
            G.main()
        write(self.notes, "q-b", "type: question\nstatus: open\ndate: 2026-10-13\ntitle: 新しい問い")
        with patch.object(sys, "argv", ["x", "--check"]):
            self.assertEqual(G.main(), 1)

    def test_broken_rules_are_reported(self):
        cases = {
            "dangling": "type: finding\nstatus: unverified\ndate: 2026-10-13\ntitle: t\nlinks:\n  - supports: nothing",
            "badrel": "type: finding\nstatus: unverified\ndate: 2026-10-13\ntitle: t\nlinks:\n  - likes: q-a",
            "nosource": "type: finding\nstatus: confirmed\ndate: 2026-10-13\ntitle: t",
            "badstatus": "type: decision\nstatus: open\ndate: 2026-10-13\ntitle: t",
            "baddate": "type: question\nstatus: open\ndate: 10/13\ntitle: t",
        }
        for name, head in cases.items():
            write(self.notes, name, head)
            with self.assertRaises(G.NoteError, msg=name):
                G.load()
            (self.notes / f"{name}.md").unlink()

    def test_answered_question_needs_an_answer(self):
        write(self.notes, "f-a", "type: finding\nstatus: confirmed\ndate: 2026-10-13\ntitle: 答え\n"
                                 "sources:\n  - https://example.com")
        with self.assertRaises(G.NoteError):
            G.load()


if __name__ == "__main__":
    unittest.main()

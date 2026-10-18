"""あらすじの読み取りを起案者の Claude に任せる流れ（読み取り待ち → 答え → 検査して足す）の検査。

LLM も通信も使わない。

    python3 tools/credits/test_theme_queue.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_theme_llm as E                                        # noqa: E402

TEXT = ("[CoRich の公演ページ]\n検査劇場で上演する新作。海辺の町で暮らす三姉妹が、"
        "父の残した古い手紙をきっかけに、それぞれの秘密と向き合っていく会話劇です。")
SYN = "海辺の町で暮らす三姉妹が、父の残した古い手紙をきっかけに、それぞれの秘密と向き合っていく会話劇"


def cand(i: str) -> dict:
    return {"side": "candidate", "id": i, "title": f"公演{i}", "url": "", "text": TEXT}


class QueueTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.patches = [patch.object(E, "QUEUE", self.tmp / "q.jsonl"),
                        patch.object(E, "QUEUE_PROMPT", self.tmp / "p.txt"),
                        patch.object(E, "OUT", self.tmp / "themes.jsonl")]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def test_write_queue_keeps_other_side(self):
        E.QUEUE.write_text(json.dumps({"side": "rated", "id": "w1", "title": "", "url": "",
                                       "text": TEXT, "prompt_version": "g2"}) + "\n", encoding="utf-8")
        n = E.write_queue([cand("1"), cand("2")], ["candidate"], "g2")
        self.assertEqual(n, 3)
        self.assertEqual(E.QUEUE_PROMPT.read_text(encoding="utf-8"), E.PROMPTS["g2"])

    def test_import_checks_verbatim_and_drains_queue(self):
        E.write_queue([cand("1"), cand("2"), cand("3")], ["candidate"], "g2")
        ans = self.tmp / "a.json"
        ans.write_text(json.dumps([
            {"id": "1", "synopsis": SYN, "elements": [{"kind": "題材", "word": "家族"}] * 12},
            {"id": "2", "synopsis": "本文に無い創作の筋書きをここに長々と書いたものとする。" * 2,
             "elements": [{"kind": "題材", "word": "戦争"}]},
            {"id": "99", "synopsis": SYN, "elements": []},       # 待ちに無い
            {"id": "1", "synopsis": SYN, "elements": []},        # 重複
        ], ensure_ascii=False), encoding="utf-8")
        n, ok, dropped = E.import_answers(ans, E.CLAUDE_MODEL)
        self.assertEqual((n, ok, dropped), (2, 1, 2))
        rows = [json.loads(l) for l in E.OUT.read_text(encoding="utf-8").splitlines()]
        r1, r2 = rows
        self.assertEqual(r1["synopsis"], SYN)
        self.assertEqual(len(r1["elements"]), E.MAX_ELEMENTS["g2"])
        self.assertEqual((r1["model"], r1["prompt_version"]), ("claude-routine", "g2"))
        self.assertEqual((r2["synopsis"], r2["elements"], r2["reason"]), ("", [], "本文に無い"))
        left = [json.loads(l)["id"] for l in E.QUEUE.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(left, ["3"])

    def test_import_accepts_jsonl(self):
        E.write_queue([cand("1")], ["candidate"], "g2")
        ans = self.tmp / "a.jsonl"
        ans.write_text(json.dumps({"id": "1", "synopsis": "", "elements": []}) + "\n", encoding="utf-8")
        self.assertEqual(E.import_answers(ans, E.CLAUDE_MODEL), (1, 0, 0))

    def test_print_queue_uses_same_prompt(self):
        E.write_queue([cand("1"), cand("2")], ["candidate"], "g2")
        out = E.queue_prompt(1)
        self.assertIn(E.PROMPTS["g2"], out)
        self.assertIn("### id: 1\nside: candidate\n題名: 公演1", out)
        self.assertNotIn("### id: 2", out)

    def test_short_pages_are_settled_by_rule_and_not_queued(self):
        # 本文が MIN_STORY_TEXT 字に満たないページは、Claude に回さず規則で空にする（起案者 2026-10-18）
        long = dict(cand("1"), text=TEXT * 10)
        short = dict(cand("2"), text=TEXT)
        self.assertLess(len(short["text"]), E.MIN_STORY_TEXT)
        with patch.object(E, "READER", "queue"), patch.object(E, "targets", return_value=[long, short]), \
                patch.object(sys, "argv", ["x", "--side", "candidate", "--no-fetch"]):
            self.assertEqual(E.main(), 0)
        queued = [json.loads(l) for l in E.QUEUE.read_text(encoding="utf-8").split("\n") if l.strip()]
        self.assertEqual([q["id"] for q in queued], ["1"])
        row = json.loads(E.OUT.read_text(encoding="utf-8").strip())
        self.assertEqual((row["id"], row["model"], row["reason"], row["synopsis"]), ("2", "rule", "本文が短い", ""))

    def test_rated_side_without_credits_is_skipped(self):
        with patch.object(E, "CREDITS", self.tmp / "missing.jsonl"), \
             patch.object(E.HT, "load", return_value={}):
            self.assertEqual(E.targets("rated", fetch=False), [])



class PromptChainTest(unittest.TestCase):
    def test_g3_keeps_g1_self_check_and_g2_concrete_words(self):
        # g2 は c6 から作ったので g1 の自問が抜けていた（〔q-prompt-g2-base〕）。g3 は両方を持つ
        g1, g2, g3 = E.PROMPTS["g1"], E.PROMPTS["g2"], E.PROMPTS["g3"]
        self_check = "自身の物語だという根拠"
        concrete = "「人間関係」のような曖昧な語に丸めず"
        self.assertIn(self_check, g1)
        self.assertNotIn(self_check, g2)
        self.assertIn(concrete, g2)
        self.assertIn(self_check, g3)
        self.assertIn(concrete, g3)
        self.assertEqual(E.MAX_ELEMENTS["g3"], E.MAX_ELEMENTS["g2"])

    def test_g4_is_g3_plus_the_festival_exception_and_is_in_use(self):
        # 起案者の判断（2026-10-18）「フェスの場合に限る。g3 に切り替えてよい」
        g3, g4 = E.PROMPTS["g3"], E.PROMPTS["g4"]
        self.assertTrue(g4.startswith(g3.split("空文字を避けようとして")[0]))
        self.assertIn("フェスティバル", g4)
        self.assertNotIn("フェスティバル（", g3)

    def test_g5_keeps_g4_synopsis_rules_and_is_in_use(self):
        # 起案者の判断（2026-10-18）「まずそれでやってみる」（eval-g5-trial-1018）
        g4, g5 = E.PROMPTS["g4"], E.PROMPTS["g5"]
        self.assertTrue(g5.split("2. elements")[0].replace("3 つ", "2 つ").startswith(
            g4.split("2. elements")[0].split("その次から")[0]))
        self.assertIn("フェスティバル", g5)
        for kind in E.G5_KINDS:
            self.assertIn(f"「{kind}」", g5)
        self.assertIn("SF＝サイエンスフィクション", g5, "語彙表を付ける")
        self.assertEqual(E.PROMPT_VERSION, "g5")
        self.assertEqual(E.DIRECT_VERSION, "g4", "Gemini で直接読む経路は g4 のまま")

    def test_g5_checks_basis_quotes_and_caps(self):
        text = "海辺の町で暮らす三姉妹が、父の残した古い手紙をきっかけに、それぞれの秘密と向き合っていく会話劇です。"
        g = {"elements": [
            {"kind": "関係・感情", "word": "姉妹", "basis": "本文"},
            {"kind": "関係・感情", "word": "すれ違い", "basis": "推定", "from": "それぞれの 秘密と向き合っていく"},
            {"kind": "時代", "word": "昭和", "basis": "推定", "from": "昭和の町"},
            {"kind": "舞台設定", "word": "昭和", "basis": "推定", "from": "昭和の町"},
            {"kind": "味わい", "word": "人情", "basis": "作風", "from": "人情"},
            {"kind": "ジャンル", "word": "喜劇", "basis": "作風", "from": "喜劇"},
        ] + [{"kind": "題材", "word": f"題材{i}", "basis": "本文"} for i in range(6)],
             "tags": ["#三姉妹", "手紙", "#" + "長" * 30]}
        els = E.g5_elements(g, text, "団体「劇団A」・… 半数以上に付いている言葉: 喜劇、家族")
        words = [e["word"] for e in els]
        self.assertIn("すれ違い", words, "引用が本文にある推定は残す（空白は無視）")
        self.assertNotIn("昭和", words, "引用が本文に無い推定と、知らない種類は落とす")
        self.assertNotIn("人情", words, "手がかりに無い作風は落とす")
        self.assertIn("喜劇", words)
        self.assertEqual(sum(1 for e in els if e["kind"] == "題材"), E.G5_KINDS["題材"])
        row = E.to_row({"side": "candidate", "id": "1", "title": "t", "url": "", "text": text, "hint": ""},
                       {**g, "synopsis": ""}, "claude", "g5")
        self.assertEqual(row["tags"], ["#三姉妹"])
        self.assertNotIn("喜劇", [e["word"] for e in row["elements"]], "手がかりが無ければ作風は残らない")

if __name__ == "__main__":
    unittest.main()

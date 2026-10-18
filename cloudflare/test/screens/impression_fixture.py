"""感想の好み（tools/review/impression_preferences.py）の答えを、Worker の src/impression.js と突き合わせる見本。

    python3 test/screens/impression_fixture.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "review"))
import impression_preferences as IP  # noqa: E402

EL = [{"kind": "題材", "word": w} for w in ("家族", "恋愛", "会話劇", "観客参加型", "コメディ", "戦争", "友情")]
NOTES = [
    "家族の描写がよかった。でも恋愛は苦手だった。",
    "会話の掛け合いが最高。",
    "恋愛は苦手ではない。",
    "家族の話で演技がよかった",
    "戦争の描写は悲しかった",
    "コメディとして面白くなかった、友情はとても心地よかった！",
    "観客参加型の演出が楽しめた",
    "家族がよかった、家族は退屈だった",
    "「家族が好き」と言う台詞があった",
    "喜劇だったので楽しかったかもしれない",
    "ラブストーリーとしては悪くなかった",
    "恋愛が多すぎた。家族　が　よかった",
    "",
]
WORKS = [
    {"work_key": "a", "title": "A", "first_date": "2026-01-02", "note_impression": NOTES[0], "elements": EL},
    {"work_key": "b", "title": "B", "first_date": "2026-03-04", "note_impression": NOTES[5], "elements": EL},
    {"work_key": "c", "title": "C", "first_date": "2026-03-04", "note_impression": NOTES[11], "elements": EL},
    {"work_key": "d", "title": "D", "first_date": "2026-05-01", "note_impression": NOTES[7], "elements": EL},
    {"work_key": "a", "title": "A2", "first_date": "2026-06-01", "note_impression": "恋愛がよかった", "elements": EL},
    {"work_key": "e", "title": "E", "first_date": "2026-07-01", "note_impression": "家族がよかった", "elements": EL, "unseen": True},
]
CANDIDATES = [EL[:2], EL[2:5], [{"word": "家族"}, {"word": "友情"}, {"word": "恋愛"}, {"word": "コメディー"}], []]


def main() -> None:
    themes = {("rated", w["work_key"]): {"elements": w["elements"]} for w in WORKS}
    profile = IP.build_profile(WORKS, themes)
    out = {
        "extract": [{"note": n, "signals": IP.extract(n, EL)} for n in NOTES],
        "works": WORKS,
        "profile": {k: {"weight": v["weight"], "count": v["count"], "keys": [e["work_key"] for e in v["evidence"]]}
                    for k, v in sorted(profile.items())},
        "score": [{"elements": c, "result": list(IP.score(c, profile))} for c in CANDIDATES],
    }
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()

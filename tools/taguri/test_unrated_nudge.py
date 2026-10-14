#!/usr/bin/env python3
"""おすすめを開いたときの「未評価が◯件あります」の材料（app.unrated_ends）の試験。

    python3 tools/taguri/test_unrated_nudge.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import app as APP                                                  # noqa: E402


class UnratedEndsTest(unittest.TestCase):
    def test_dates_only_sorted(self):
        rows = [{"last_date": "2026-10-12", "title": "秘密の題名", "work_key": "k1"},
                {"last_date": "2026-09-01", "title": "もう一つ", "work_key": "k2"}]
        with patch.object(APP, "waiting_rows", return_value=rows) as w:
            got = APP.unrated_ends("alice", "2026-10-14")
        w.assert_called_once_with("alice", "2026-10-14")
        self.assertEqual(got, ["2026-09-01", "2026-10-12"])     # 題名などは返さない


if __name__ == "__main__":
    unittest.main()

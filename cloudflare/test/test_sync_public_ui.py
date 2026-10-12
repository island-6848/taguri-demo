"""cloudflare/public must be the current copy of web/ (only asset paths differ).

Fails when master changed web/ and the preview copy was not refreshed with
`python3 cloudflare/scripts/sync_public_ui.py`; the visual check would otherwise
only show it as differing pixels.
"""
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'sync_public_ui.py'


class SyncTest(unittest.TestCase):
    def test_public_copy_is_current(self):
        result = subprocess.run([sys.executable, str(SCRIPT), '--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()

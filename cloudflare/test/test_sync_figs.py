"""cloudflare/public/figs must be the current copy of the figures that run in the
browser (src/screens/figs.js and what it imports), and none of them may be a
module that reads D1 (scripts/sync_figs.py)."""
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'sync_figs.py'


class SyncFigsTest(unittest.TestCase):
    def test_figs_copy_is_current(self):
        result = subprocess.run([sys.executable, str(SCRIPT), '--check'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()

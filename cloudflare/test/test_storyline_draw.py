"""The storyline figure that actually runs in the app is web/storyline-draw.js (app.js
fixupStoryline loads it; the <script> inside the screen's HTML is inert). It must be
storyline.SCRIPT as scripts/write_icons.py writes it, and the Worker's STORYLINE_JS must be
the same script. Before 2026-10-24 the file was a hand copy and missed the touch fix."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _write_icons():
    spec = importlib.util.spec_from_file_location('write_icons', ROOT / 'cloudflare' / 'scripts' / 'write_icons.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class StorylineDrawTest(unittest.TestCase):
    def test_draw_script_is_written_from_storyline_script(self):
        w = _write_icons()
        self.assertEqual((ROOT / 'web' / 'storyline-draw.js').read_text(encoding='utf-8'), w.DRAW_JS,
                         'run python3 cloudflare/scripts/write_icons.py and sync_public_ui.py')

    def test_worker_script_is_the_same(self):
        w = _write_icons()
        src = (ROOT / 'cloudflare' / 'src' / 'screens' / 'storyline_js.js').read_text(encoding='utf-8')
        body = src[src.index('= ') + 2:].rstrip().rstrip(';')
        self.assertEqual(json.loads(body), w.SL.SCRIPT)

    def test_touch_is_left_to_the_browser(self):
        # 指の操作を d3.zoom に渡すと、図の上で横にも縦にもスクロールできない（起案者の指摘 2026-10-24）
        self.assertIn('.touchable(() => false)', (ROOT / 'web' / 'storyline-draw.js').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()

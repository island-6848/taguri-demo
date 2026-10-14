"""Write src/screens/icons.js from tools/taguri/icons.py and src/screens/calendar_js.js
from stage_calendar.JS (the Worker's screens use the
same icons as the Python ones). test/icons.test.js fails when the two drift apart.

    python3 cloudflare/scripts/write_icons.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "taguri"))
import icons as IC                                                   # noqa: E402

SRC = f'''// Icon paths of tools/taguri/icons.py, written by scripts/write_icons.py (do not edit;
// test/icons.test.js checks they match). ico() and h2() give icons.ico / icons.h2's markup.
export const P = {json.dumps(IC.P, ensure_ascii=False, indent=1)};
export const ALIAS = {json.dumps(IC.ALIAS, ensure_ascii=False)};
export function ico(name, size = 16, cls = '') {{
  const d = P[ALIAS[name] || name];
  if (!d) return '';
  return `<svg class="ico ${{cls}}" viewBox="0 0 24 24" width="${{size}}" height="${{size}}"`
    + ' fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"'
    + ` stroke-linejoin="round" aria-hidden="true"><path d="${{d}}"/></svg>`;
}}
export const h2 = (name, text, extra = '') => `<h2>${{ico(name, 18)}}<span>${{text}}</span>${{extra}}</h2>`;
'''

sys.path.insert(0, str(ROOT / "tools" / "review"))
import stage_calendar as SC                                          # noqa: E402
import chronicle as CR                                               # noqa: E402

# The <script> the Python calendar puts after its grid (inert once inserted with innerHTML,
# kept so the screen's HTML stays the same as the Python one).
CAL_JS = ("// stage_calendar.JS and chronicle.JS, written by scripts/write_icons.py (do not edit).\n"
          f"export const CALENDAR_JS = {json.dumps(SC.JS, ensure_ascii=False)};\n"
          f"export const CHRONICLE_JS = {json.dumps(CR.JS, ensure_ascii=False)};\n")

import storyline as SL                                               # noqa: E402

# The <script> storyline.panel appends (src/screens/storyline.js; test/storyline.test.js).
SL_JS = ("// storyline.SCRIPT, written by scripts/write_icons.py (do not edit).\n"
         f"export const STORYLINE_JS = {json.dumps(SL.SCRIPT, ensure_ascii=False)};\n")

if __name__ == "__main__":
    (ROOT / "cloudflare" / "src" / "screens" / "icons.js").write_text(SRC, encoding="utf-8")
    (ROOT / "cloudflare" / "src" / "screens" / "calendar_js.js").write_text(CAL_JS, encoding="utf-8")
    (ROOT / "cloudflare" / "src" / "screens" / "storyline_js.js").write_text(SL_JS, encoding="utf-8")

"""Write src/screens/icons.js from tools/taguri/icons.py (the Worker's screens use the
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

if __name__ == "__main__":
    (ROOT / "cloudflare" / "src" / "screens" / "icons.js").write_text(SRC, encoding="utf-8")

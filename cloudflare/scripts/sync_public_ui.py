"""Copy the original UI (web/) into the Cloudflare preview (cloudflare/public/).

    python3 cloudflare/scripts/sync_public_ui.py           # rewrite the copies
    python3 cloudflare/scripts/sync_public_ui.py --check   # exit 1 if out of date

The preview serves the same screens from the site root instead of GitHub
Pages' /taguri-demo/, so only asset paths change. API_BASE comes from
public/config.js (same origin), which is the preview's own file and is not
copied. When master changes web/, run this after merging master into the
preview branch; the CI check fails until the copies match.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB, PUBLIC = ROOT / "web", ROOT / "cloudflare" / "public"
COPIED = ("tour.js", "style.css", "tour.css", "theme.css", "recommendation-exposure.js")


def expected() -> dict[str, str]:
    out = {name: (WEB / name).read_text(encoding="utf-8") for name in COPIED}
    app = (WEB / "app.js").read_text(encoding="utf-8")
    out["app.js"] = app.replace('"/taguri-demo/vendor/d3.v7.min.js"', '"/vendor/d3.v7.min.js"')
    html = (WEB / "index.html").read_text(encoding="utf-8")
    html = html.replace('src="/taguri-demo/', 'src="/').replace('href="/taguri-demo/', 'href="/')
    out["index.html"] = html.replace("URL(例: /taguri-demo/recommend/reminder)", "URL(例: /recommend/reminder)")
    return out


def main() -> int:
    check = "--check" in sys.argv[1:]
    stale = []
    for name, text in expected().items():
        dest = PUBLIC / name
        if not dest.exists() or dest.read_text(encoding="utf-8") != text:
            stale.append(name)
            if not check:
                dest.write_text(text, encoding="utf-8")
    if check and stale:
        print("cloudflare/public is out of date with web/: " + ", ".join(stale)
              + "\nrun: python3 cloudflare/scripts/sync_public_ui.py")
        return 1
    print(("updated: " + ", ".join(stale)) if stale else "cloudflare/public matches web/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

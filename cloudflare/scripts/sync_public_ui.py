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
COPIED = ("tour.js", "style.css", "tour.css", "theme.css", "fonts.css", "recommendation-exposure.js",
          "assets/fonts/OFL-ZenKakuGothicAntique.txt", "assets/fonts/OFL-SawarabiGothic.txt",
          "assets/fonts/OFL-ZenKakuGothicNew.txt")
# Self-hosted title font (SIL OFL, subset to the page titles). Copied byte for byte.
BINARY = ("assets/fonts/zkga-title.woff2",
          "assets/logo/apple-touch-icon.png")   # ホーム画面のアイコン（docs/design/logo/make_type.py）
# 押すものと公演名の文字（さわらびゴシック Regular、SIL OFL）。文字の範囲ごとのファイルを丸ごと写す
BINARY += tuple("assets/fonts/sawarabi-gothic/" + p.name for p in sorted((WEB / "assets/fonts/sawarabi-gothic").glob("*.woff2")))
# 本文（Zen角ゴシック New の Regular・Bold、SIL OFL）
BINARY += tuple("assets/fonts/zen-kaku-gothic-new/" + p.name for p in sorted((WEB / "assets/fonts/zen-kaku-gothic-new").glob("*.woff2")))


def expected() -> dict[str, str | bytes]:
    out: dict[str, str | bytes] = {name: (WEB / name).read_text(encoding="utf-8") for name in COPIED}
    out.update({name: (WEB / name).read_bytes() for name in BINARY})
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
        binary = isinstance(text, bytes)
        current = (dest.read_bytes() if binary else dest.read_text(encoding="utf-8")) if dest.exists() else None
        if current != text:
            stale.append(name)
            if not check:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(text) if binary else dest.write_text(text, encoding="utf-8")
    # デモ（GitHub Pages）は深い URL を読み込み直すと web/404.html を返す。index.html と違うと、
    # 読み込み直したときだけ昔の見た目が出る（起案者の指摘 2026-10-14）。pages.yml も毎回写すが、ここでも揃える
    idx, nf = WEB / "index.html", WEB / "404.html"
    if nf.read_text(encoding="utf-8") != idx.read_text(encoding="utf-8"):
        stale.append("web/404.html")
        if not check:
            nf.write_text(idx.read_text(encoding="utf-8"), encoding="utf-8")
    if check and stale:
        print("cloudflare/public is out of date with web/: " + ", ".join(stale)
              + "\nrun: python3 cloudflare/scripts/sync_public_ui.py")
        return 1
    print(("updated: " + ", ".join(stale)) if stale else "cloudflare/public matches web/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

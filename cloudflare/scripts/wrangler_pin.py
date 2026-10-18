"""本番の権限で動かす wrangler を、`cloudflare/package-lock.json` で決めた版にそろえる（issue #131）。

前は `npx --yes wrangler@4` で、動かすたびにその時いちばん新しい 4 系を取ってきていた。同じコミットでも
日によって別の wrangler が本番の鍵を持って動くことになる。ここでは:

- `cloudflare/node_modules` に lockfile と同じ版の wrangler があれば、それを使う（`npm ci` 済みのとき。
  wrangler が使う部品の版も lockfile のとおり）
- 無ければ、lockfile の版を名指しで取る（`npx --yes wrangler@<版>`）。wrangler 自身の版は固定されるが、
  その部品の版は npx が決める。部品まで固定したいときは、先に `cd cloudflare && npm ci` をする

標準ライブラリだけで動かす。
"""
from __future__ import annotations

import json
from pathlib import Path

CLOUDFLARE = Path(__file__).resolve().parents[1]
LOCK = CLOUDFLARE / "package-lock.json"


def locked_version(lock: Path = LOCK) -> str:
    data = json.loads(lock.read_text(encoding="utf-8"))
    v = (data.get("packages", {}).get("node_modules/wrangler") or {}).get("version")
    if not v:
        raise RuntimeError(f"{lock} に wrangler の版がありません（cd cloudflare && npm install で作り直す）")
    return v


def installed_version(root: Path = CLOUDFLARE) -> str:
    p = root / "node_modules" / "wrangler" / "package.json"
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("version") or ""
    except (OSError, ValueError):
        return ""


def wrangler_cmd(npx: str = "npx", root: Path = CLOUDFLARE, lock: Path = LOCK) -> list[str]:
    """`[npx, …]` の頭の部分。この後ろに wrangler の引数を足す。cwd は cloudflare/ にして動かす。"""
    want = locked_version(lock)
    if installed_version(root) == want:
        return [npx, "--no-install", "wrangler"]
    return [npx, "--yes", f"wrangler@{want}"]

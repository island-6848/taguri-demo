#!/usr/bin/env bash
# 調査ツールの実行環境を構築する。
#
# この環境（Ubuntu 26.04 / WSL2）には最初 pip も npm も無かった。sudo は
# インストール済みでユーザも sudo グループに属しているが、パスワード入力が
# 必要なため非対話では使えない。そこで **sudo が要る部分と要らない部分を
# 明確に分離** してある。
#
#   前半（sudo 不要）: pip・Node.js/npm・Python パッケージ・Chromium 本体
#   後半（sudo 必須）: Chromium が依存する共有ライブラリ 3 つ
#
# 冪等に書いてあるので、何度実行しても壊れない。
#
# 結果として **sudo は一切不要** になった。Chromium が要求する共有ライブラリも、
# .deb を root 権限なしでダウンロードしてユーザ領域に展開し LD_LIBRARY_PATH で
# 読ませることで解決している（システムには触らない）。
#
# 使い方:
#   bash tools/setup_env.sh
#   source tools/lib/env.sh   # ブラウザを使うスクリプトの実行前に必要

set -euo pipefail

LOCAL_BIN="$HOME/.local/bin"
NODE_VERSION="v22.20.0"
NODE_DIR="$HOME/.local/nodejs"
DEPS_DIR="$HOME/.local/chromium-deps"
DEPS_LIB="$DEPS_DIR/root/usr/lib/x86_64-linux-gnu"

# PEP 668 の externally-managed-environment 保護により、素の pip install は
# 拒否される。--user と併用する限り書き込み先は ~/.local に限定され OS 側の
# site-packages には触らないため、--break-system-packages で回避している。
PIP_FLAGS=(--user --break-system-packages --no-warn-script-location)

mkdir -p "$LOCAL_BIN"

echo "==> pip"
if python3 -m pip --version >/dev/null 2>&1; then
  echo "    既にインストール済み: $(python3 -m pip --version)"
else
  # この Python には ensurepip も venv も無いため、get-pip.py で直接導入する。
  tmp="$(mktemp -d)"
  curl -sSL https://bootstrap.pypa.io/get-pip.py -o "$tmp/get-pip.py"
  python3 "$tmp/get-pip.py" "${PIP_FLAGS[@]}"
  rm -rf "$tmp"
  echo "    導入完了: $(python3 -m pip --version)"
fi

echo "==> Node.js / npm"
if [ -x "$NODE_DIR/bin/node" ]; then
  echo "    既にインストール済み: $("$NODE_DIR/bin/node" --version)"
else
  # 公式のビルド済み tarball を ~/.local に展開する。sudo は不要。
  tmp="$(mktemp -d)"
  curl -sSL "https://nodejs.org/dist/$NODE_VERSION/node-$NODE_VERSION-linux-x64.tar.xz" \
    -o "$tmp/node.tar.xz"
  mkdir -p "$NODE_DIR"
  tar -xJf "$tmp/node.tar.xz" -C "$NODE_DIR" --strip-components=1
  rm -rf "$tmp"
fi
# npm / npx の shebang は PATH 上の `node` を探すため、symlink が必須。
for bin in node npm npx; do
  ln -sf "$NODE_DIR/bin/$bin" "$LOCAL_BIN/$bin"
done
echo "    node=$(node --version) npm=$(npm --version)"

echo "==> Python パッケージ"
python3 -m pip install "${PIP_FLAGS[@]}" --quiet instaloader playwright
echo "    instaloader=$(python3 -c 'import instaloader;print(instaloader.__version__)')"
echo "    playwright=$(python3 -m playwright --version)"

echo "==> Chromium（Playwright 同梱版）"
python3 -m playwright install chromium

echo "==> Chromium の共有ライブラリ（root 不要）"
# Ubuntu 26.04 では大半のライブラリが既に入っており、不足はこの 3 つのみ
# （libnspr4 / libnss3 / libasound2t64）。
#
# これらは通常 apt でシステムに入れるが、sudo はパスワード入力を要求し
# 非対話では実行できない。そこで **.deb を root 権限なしでダウンロードして
# ユーザ領域に展開し、LD_LIBRARY_PATH で読ませる**。システムには一切触らない。
#
# `playwright install-deps` は使わない。xvfb や各種フォントまで入れようとして
# このリリースに存在しないパッケージで失敗するため。
if [ -f "$DEPS_LIB/libnspr4.so" ]; then
  echo "    既に展開済み: $DEPS_LIB"
else
  mkdir -p "$DEPS_DIR"
  (
    cd "$DEPS_DIR"
    apt-get download libnspr4 libnss3 libasound2t64
    for deb in *.deb; do dpkg-deb -x "$deb" root/; done
  )
  echo "    展開完了: $DEPS_LIB"
fi
echo "    実行時は次を設定すること（tools/lib/env.sh を source すればよい）:"
echo "      export LD_LIBRARY_PATH=\"$DEPS_LIB:\$LD_LIBRARY_PATH\""

echo
echo "==> 検証"
LD_LIBRARY_PATH="$DEPS_LIB:${LD_LIBRARY_PATH:-}" python3 - <<'PY'
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.goto("https://example.com", timeout=60000)
        print(f"    Chromium 起動 OK / タイトル={pg.title()!r}")
        b.close()
except Exception as exc:
    head = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
    print(f"    Chromium 起動 NG: {head}")
    print("    共有ライブラリが不足している可能性があります（上記の apt-get を実行）")
PY

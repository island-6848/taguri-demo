# ブラウザを使うスクリプトの実行前に source する。
#   source tools/lib/env.sh
#
# Playwright 同梱の Chromium は libnspr4 / libnss3 / libasound2t64 を要求するが、
# これらはシステムに入っていない。sudo が非対話で使えないため、.deb を
# ユーザ領域に展開して LD_LIBRARY_PATH で読ませている（tools/setup_env.sh 参照）。
_deps_lib="$HOME/.local/chromium-deps/root/usr/lib/x86_64-linux-gnu"
if [ -d "$_deps_lib" ]; then
  export LD_LIBRARY_PATH="$_deps_lib:${LD_LIBRARY_PATH:-}"
else
  echo "警告: $_deps_lib が無い。bash tools/setup_env.sh を先に実行すること" >&2
fi
unset _deps_lib

#!/bin/sh
# Mac: ダブルクリックで、たぐりの管理画面を開く（止めるにはこの窓を閉じるか Ctrl-C）
cd "$(dirname "$0")/../.." || exit 1
exec python3 tools/admin/serve_admin.py

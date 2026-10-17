@echo off
rem Windows: ダブルクリックで、たぐりの管理画面を開く（止めるにはこの窓を閉じる）
chcp 65001 >nul
cd /d "%~dp0..\.."
where py >nul 2>nul && (py -3 tools\admin\serve_admin.py) || (python tools\admin\serve_admin.py)
pause

@echo off
REM Запуск @MarquisCraftBot (отдельный токен, не пересекается с @TeamCaptainBot).
REM Безопасен для параллельного запуска с Claude Code telegram-плагином.
REM Токен читается из %USERPROFILE%\.claude\channels\marquiscraft\.env
setlocal
cd /d "%~dp0"
py marquis_bot.py
endlocal

@echo off
REM ============================================================
REM  ВНИМАНИЕ: НЕ запускай этот скрипт, если в Claude Code активен
REM  плагин telegram (plugin:telegram:telegram). Оба процесса
REM  поллят один и тот же токен @TeamCaptainBot, что приводит к
REM  409 Conflict на каждом getUpdates и делает плагин нестабильным.
REM
REM  Сценарии использования:
REM    1) Claude Code ЗАПУЩЕН -> НЕ запускать bot.py (используй плагин).
REM       Для отправки файлов агентами используй tools\send_telegram.py.
REM    2) Claude Code НЕ запущен и ты хочешь автономного бота ->
REM       убедись, что /reload-plugins не вызывал плагин в недавней
REM       сессии, и запускай отсюда.
REM ============================================================
setlocal
cd /d "%~dp0"
py bot.py
endlocal

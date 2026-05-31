<#
.SYNOPSIS
  Регистрирует опциональные MCP-серверы, требующие API-ключ (Firecrawl, Morph),
  в USER-scope конфиге Claude Code (~/.claude.json). Ключи берутся ТОЛЬКО из
  переменных окружения — в репозиторий ничего не пишется.

.DESCRIPTION
  Принцип безопасности (CLAUDE.md): секреты не хранятся в git-tracked коде.
  Скрипт читает $env:FIRECRAWL_API_KEY и $env:MORPH_API_KEY и настраивает сервер
  только если соответствующий ключ задан. Идемпотентен: повторный запуск
  перенастраивает с актуальным ключом.

.EXAMPLE
  # 1. Задать ключи (один раз, перенести в переменные пользователя):
  setx FIRECRAWL_API_KEY "fc-..."
  setx MORPH_API_KEY     "sk-..."
  # 2. Открыть НОВЫЙ терминал (setx виден только новым процессам), затем:
  pwsh -File tools/setup_optional_mcp.ps1

.NOTES
  Firecrawl key:  https://firecrawl.dev/app/api-keys
  Morph key:      https://morphllm.com/dashboard/api-keys
  Higgsfield:     ключ НЕ нужен — добавлен как HTTP MCP с OAuth (mcp.higgsfield.ai/mcp)
  Exa:            уже доступен через плагин everything-claude-code
#>

[CmdletBinding()]
param(
    [string]$Scope = "user"
)

$ErrorActionPreference = "Stop"

Write-Host "== Опциональные MCP (нужен API-ключ) ==" -ForegroundColor Yellow

# --- Firecrawl: чистый веб-скрейпинг ---------------------------------------
if ($env:FIRECRAWL_API_KEY) {
    Write-Host "→ firecrawl" -ForegroundColor Cyan
    & claude mcp remove --scope $Scope firecrawl *> $null
    try {
        # Ключ передаётся подпроцессу как env; в URL не кладём (правило 7 CLAUDE.md).
        & claude mcp add --scope $Scope firecrawl `
            -e "FIRECRAWL_API_KEY=$($env:FIRECRAWL_API_KEY)" `
            -- npx -y firecrawl-mcp
        Write-Host "  OK firecrawl настроен (scope: $Scope)" -ForegroundColor Green
    }
    catch {
        Write-Host "  FAIL firecrawl: $($_.Exception.Message)" -ForegroundColor Red
    }
}
else {
    Write-Host "→ firecrawl ПРОПУЩЕН — нет `$env:FIRECRAWL_API_KEY" -ForegroundColor DarkYellow
    Write-Host "    Получить ключ: https://firecrawl.dev/app/api-keys" -ForegroundColor DarkGray
}

# --- Morph: fast-apply правки файлов ---------------------------------------
if ($env:MORPH_API_KEY) {
    Write-Host "→ morph (через официальный установщик)" -ForegroundColor Cyan
    try {
        # Установщик Morph сам прописывает Claude Code/Cursor/Codex/VS Code.
        & npx -y "@morphllm/morph-setup" --morph-api-key $env:MORPH_API_KEY
        Write-Host "  OK morph настроен" -ForegroundColor Green
    }
    catch {
        Write-Host "  FAIL morph: $($_.Exception.Message)" -ForegroundColor Red
    }
}
else {
    Write-Host "→ morph ПРОПУЩЕН — нет `$env:MORPH_API_KEY" -ForegroundColor DarkYellow
    Write-Host "    Получить ключ: https://morphllm.com/dashboard/api-keys" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Готово. Проверить: claude mcp list" -ForegroundColor Yellow
Write-Host "Перезапусти Claude Code, чтобы новые MCP подхватились." -ForegroundColor Yellow

#!/bin/bash
# Claude Code Statusline
# Format: "Opus 4.6  ctx:11%  5h:[████] 0% 4h38m  7d:[████] 47% 18h38m  21900 tokens"
# Reads JSON from stdin, outputs formatted status line

input=$(cat)

# --- Extract fields ---
MODEL=$(echo "$input" | jq -r '.model.display_name // .model.id // "unknown"')
CTX_PCT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | cut -d. -f1)
DURATION_MS=$(echo "$input" | jq -r '.cost.total_duration_ms // 0')
TOTAL_IN=$(echo "$input" | jq -r '.context_window.total_input_tokens // 0')
TOTAL_OUT=$(echo "$input" | jq -r '.context_window.total_output_tokens // 0')
TOTAL_TOKENS=$((TOTAL_IN + TOTAL_OUT))

# --- 5h session progress & time remaining ---
SESSION_LIMIT_MS=$((5 * 60 * 60 * 1000))  # 5 hours in ms
SESS_PCT=$((DURATION_MS * 100 / SESSION_LIMIT_MS))
[ "$SESS_PCT" -gt 100 ] && SESS_PCT=100

REMAINING_MS=$((SESSION_LIMIT_MS - DURATION_MS))
[ "$REMAINING_MS" -lt 0 ] && REMAINING_MS=0
REMAIN_TOTAL_MIN=$((REMAINING_MS / 60000))
REMAIN_H=$((REMAIN_TOTAL_MIN / 60))
REMAIN_M=$((REMAIN_TOTAL_MIN % 60))

# --- 7d week progress & time remaining ---
DOW=$(date +%u)   # 1=Mon, 7=Sun
HOUR=$(date +%H)
MIN=$(date +%M)
WEEK_MINS=$(( (DOW - 1) * 1440 + 10#$HOUR * 60 + 10#$MIN ))
WEEK_TOTAL=10080   # 7 * 24 * 60
WEEK_PCT=$((WEEK_MINS * 100 / WEEK_TOTAL))

WEEK_REMAIN=$((WEEK_TOTAL - WEEK_MINS))
WK_REM_H=$((WEEK_REMAIN / 60))
WK_REM_M=$((WEEK_REMAIN % 60))

# --- Progress bar [4 chars] from percentage ---
make_bar() {
  local pct=$1
  local filled=$((pct * 4 / 100))
  [ "$filled" -gt 4 ] && filled=4
  local empty=$((4 - filled))
  local bar=""
  for ((i=0; i<filled; i++)); do bar+="█"; done
  for ((i=0; i<empty; i++)); do bar+="░"; done
  echo "$bar"
}

SESS_BAR=$(make_bar "$SESS_PCT")
WEEK_BAR=$(make_bar "$WEEK_PCT")

# --- Colors ---
RST='\033[0m'
DIM='\033[2m'
BOLD='\033[1m'
CYAN='\033[36m'
GREEN='\033[32m'
YELLOW='\033[33m'
RED='\033[31m'
MAGENTA='\033[35m'

# Context color
if [ "$CTX_PCT" -ge 80 ]; then
  CTX_CLR=$RED
elif [ "$CTX_PCT" -ge 50 ]; then
  CTX_CLR=$YELLOW
else
  CTX_CLR=$GREEN
fi

# Session color
if [ "$SESS_PCT" -ge 80 ]; then
  SESS_CLR=$RED
elif [ "$SESS_PCT" -ge 50 ]; then
  SESS_CLR=$YELLOW
else
  SESS_CLR=$CYAN
fi

# Week color
if [ "$WEEK_PCT" -ge 80 ]; then
  WK_CLR=$RED
elif [ "$WEEK_PCT" -ge 50 ]; then
  WK_CLR=$YELLOW
else
  WK_CLR=$CYAN
fi

# --- Build status line ---
printf "${BOLD}${CYAN}%s${RST}" "$MODEL"
printf "  "
printf "${CTX_CLR}ctx:%d%%${RST}" "$CTX_PCT"
printf "  "
printf "${SESS_CLR}5h:[%s] %d%% %dh%02dm${RST}" "$SESS_BAR" "$SESS_PCT" "$REMAIN_H" "$REMAIN_M"
printf "  "
printf "${WK_CLR}7d:[%s] %d%% %dh%02dm${RST}" "$WEEK_BAR" "$WEEK_PCT" "$WK_REM_H" "$WK_REM_M"
printf "  "
printf "${MAGENTA}%d tokens${RST}" "$TOTAL_TOKENS"
echo

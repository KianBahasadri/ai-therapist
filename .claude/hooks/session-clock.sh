#!/usr/bin/env bash
# UserPromptSubmit hook: stamp every patient message with a session clock so the
# therapist can judge (A) how long the session has run, and (B) how long the
# patient took to respond. The stamp is injected into the therapist's context
# only — the patient never sees it. This is the equivalent of a therapist
# glancing at the clock on the wall.
#
# Session start is anchored to the patient's first message of the session.
# Per-session state is kept in a temp file (never in the repo), keyed by the
# Claude Code session id so parallel sessions don't collide.
set -euo pipefail

# --- read the hook payload (JSON on stdin) -------------------------------
input="$(cat)"

extract() { # extract <key> — pull a top-level string value out of the JSON
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$input" | jq -r --arg k "$1" '.[$k] // empty' || true
  else
    printf '%s' "$input" \
      | grep -o "\"$1\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" \
      | head -n1 | sed 's/.*:[[:space:]]*"\(.*\)"/\1/' || true
  fi
}

session_id="$(extract session_id)"
[ -n "$session_id" ] || session_id="default"
# sanitize so it is safe as a filename
session_id="$(printf '%s' "$session_id" | tr -c 'A-Za-z0-9._-' '_')"

state_dir="${TMPDIR:-/tmp}/ai-therapist-clock"
mkdir -p "$state_dir"
state_file="$state_dir/$session_id.clock"

# tidy stale clocks (>1 day old) so the temp dir does not accumulate
find "$state_dir" -maxdepth 1 -name '*.clock' -mtime +1 -delete 2>/dev/null || true

now="$(date +%s)"

if [ -f "$state_file" ]; then
  # shellcheck disable=SC1090
  . "$state_file"
else
  start="$now"; last="$now"; turn="0"
fi
# defend against a missing/partial state file
: "${start:=$now}"; : "${last:=$now}"; : "${turn:=0}"

turn=$((turn + 1))
elapsed=$((now - start))
gap=$((now - last))

# persist updated state
{
  echo "start=$start"
  echo "last=$now"
  echo "turn=$turn"
} > "$state_file"

fmt() { # fmt <seconds> -> compact "Hh MMm SSs" (trims leading zero units)
  local s="$1" h m
  h=$((s / 3600)); m=$(((s % 3600) / 60)); s=$((s % 60))
  if   [ "$h" -gt 0 ]; then printf '%dh%02dm%02ds' "$h" "$m" "$s"
  elif [ "$m" -gt 0 ]; then printf '%dm%02ds' "$m" "$s"
  else                      printf '%ds' "$s"; fi
}

clock="$(date +%H:%M)"
if [ "$turn" -eq 1 ]; then
  reply="first message of the session"
else
  reply="patient took $(fmt "$gap") to reply since your last message"
fi

echo "[session-clock] turn $turn | time $clock | session length $(fmt "$elapsed") | $reply"

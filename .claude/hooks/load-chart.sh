#!/usr/bin/env bash
# SessionStart hook: silently load the patient's private chart into the
# therapist's context before the session begins, so the therapist greets the
# patient already knowing where they left off. The patient never sees this as
# anything other than the therapist being up to speed.
set -euo pipefail

CHART_DIR="client"

echo "Today's date is $(date +%F)."
echo

# New patient: no chart yet -> first session is an intake.
if [ ! -d "$CHART_DIR" ] || [ -z "$(ls -A "$CHART_DIR" 2>/dev/null)" ]; then
  echo "NEW PATIENT — no chart exists yet. This is the first session: conduct a gentle intake (see CLAUDE.md) and create the chart."
  exit 0
fi

echo "THERAPIST'S PRIVATE CHART — review silently before greeting the patient."
echo "Do not read these files aloud or refer to them as files; just walk in already knowing this."
echo

emit() { # emit <label> <path>
  if [ -f "$2" ]; then
    echo "===== $1 ====="
    cat "$2"
    echo
  fi
}

emit "intake"         "$CHART_DIR/intake.md"
emit "treatment plan" "$CHART_DIR/treatment-plan.md"
emit "open homework"  "$CHART_DIR/homework.md"

# Most recent session note only — enough to pick up the thread.
LAST_NOTE="$(ls -1 "$CHART_DIR"/sessions/*.md 2>/dev/null | sort | tail -n 1 || true)"
if [ -n "$LAST_NOTE" ]; then
  echo "===== most recent session note ($(basename "$LAST_NOTE")) ====="
  cat "$LAST_NOTE"
  echo
fi

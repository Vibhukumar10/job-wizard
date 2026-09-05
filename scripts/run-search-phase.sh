#!/bin/bash
# Runs the job-hunt search phase unattended, invoked by the LaunchAgent.
#
# Fires on wake, not on the clock. launchd's StartCalendarInterval catches up a
# missed firing when the machine wakes ("Unlike cron which skips job invocations
# when the computer is asleep, launchd will start the job the next time the
# computer wakes up" — man launchd.plist), coalescing multiple missed intervals
# into one. So on a laptop that sleeps with the lid shut, this runs the moment
# the lid opens rather than at 07:00.
#
# See .scratch/job-hunt-speedup/issues/07-choose-unattended-trigger.md.

set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$REPO/state/logs"
LOG="$LOG_DIR/search-phase.log"
TODAY="$(date +%F)"

mkdir -p "$LOG_DIR"
exec >>"$LOG" 2>&1
echo "=== $(date '+%F %T') search phase starting ==="

# The once-per-day guard. jobs.json exists only when a search completed, so its
# presence is both "already ran today" and "safe to tailor" — one mechanism, not
# a separate stamp file that could disagree with reality.
STATUS="$(cd "$REPO" && uv run python -m pipeline.cli run-status "runs/$TODAY" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' 2>/dev/null || echo missing)"
if [ "$STATUS" = "complete" ]; then
  echo "already ran today ($TODAY); nothing to do"
  exit 0
fi
if [ "$STATUS" = "in_flight" ]; then
  echo "a search is already running; refusing to start a second against the same browser profile"
  exit 0
fi

# The MCP server drives a persistent Chromium profile and takes an exclusive lock
# on it. A Chromium already open on that profile makes launch_persistent_context
# fail, which is likely here specifically: this fires on wake, and Chromium may
# have restored on login. Fail loudly with the real reason rather than letting it
# surface as an opaque MCP error 14 minutes in. Never kill the user's browser.
if pgrep -f "Chromium.*user-data-dir.*Application Support/Chromium" >/dev/null 2>&1; then
  echo "ERROR: Chromium is running on the profile the LinkedIn MCP server needs."
  echo "       Quit it and re-run, or invoke /job-hunt by hand once it's closed."
  exit 1
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "ERROR: the claude CLI is not on PATH for this LaunchAgent."
  exit 1
fi

# caffeinate -i prevents an idle sleep mid-run. The search phase makes ~50-60
# LinkedIn calls at roughly one per 15 seconds, all serialized by the MCP
# server's profile lease — losing it to an idle sleep would waste the lot.
cd "$REPO" || exit 1
caffeinate -i claude -p "/job-hunt" --permission-mode acceptEdits
STATUS_CODE=$?

echo "=== $(date '+%F %T') search phase finished (exit $STATUS_CODE) ==="
exit $STATUS_CODE

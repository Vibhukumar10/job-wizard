#!/bin/bash
# Runs the whole job-hunt unattended, invoked by the LaunchAgent: search, score,
# Notion push, and a tailored resume for every shortlisted job (see
# docs/adr/0009-single-phase-run.md).
#
# The filename still says "search-phase" because an installed LaunchAgent plist
# points at this exact path — renaming it would silently break every already-
# installed agent until it was reinstalled. The name is historical; the
# behaviour is the full run.
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
LOG="$LOG_DIR/job-hunt.log"
TODAY="$(date +%F)"

mkdir -p "$LOG_DIR"
exec >>"$LOG" 2>&1
echo "=== $(date '+%F %T') job-hunt run starting ==="

# jobs.json exists only when a search completed, so its presence means "already
# searched today" — one mechanism, not a separate stamp file that could disagree
# with reality.
#
# A completed search is deliberately NOT an early exit any more. Now that one
# run also tailors every shortlisted job, a run killed midway leaves a complete
# jobs.json and missing resumes. /job-hunt handles exactly that: it refuses to
# re-search, then finishes the jobs still missing resumes, and no-ops when there
# are none. Exiting here would strand a half-tailored run until the user noticed.
STATUS="$(cd "$REPO" && uv run python -m pipeline.cli run-status "runs/$TODAY" 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])' 2>/dev/null || echo missing)"
if [ "$STATUS" = "in_flight" ]; then
  echo "a run is already in flight; refusing to start a second against the same browser profile"
  exit 0
fi
if [ "$STATUS" = "complete" ]; then
  echo "search already completed today ($TODAY); running /job-hunt anyway so it can finish"
  echo "tailoring any jobs still missing resumes (it exits quickly if none are pending)"
fi

# The MCP server drives a persistent Chromium profile and takes an exclusive lock
# on it. A Chromium already open on that profile makes launch_persistent_context
# fail, which is likely here specifically: this fires on wake, and Chromium may
# have restored on login. Fail loudly with the real reason rather than letting it
# surface as an opaque MCP error 14 minutes in. Never kill the user's browser.
#
# Skipped when the search is already done: the remaining work is tailoring, which
# touches neither LinkedIn nor the browser profile.
if [ "$STATUS" != "complete" ] && pgrep -f "Chromium.*user-data-dir.*Application Support/Chromium" >/dev/null 2>&1; then
  echo "ERROR: Chromium is running on the profile the LinkedIn MCP server needs."
  echo "       Quit it and re-run, or invoke /job-hunt by hand once it's closed."
  exit 1
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "ERROR: the claude CLI is not on PATH for this LaunchAgent."
  exit 1
fi

# pdflatex is checked by the skill itself before the search, but check here too:
# a LaunchAgent has its own PATH, and failing now costs seconds where failing
# inside the run costs the whole search. /Library/TeX/texbin is on the plist's
# PATH for exactly this reason.
if ! command -v pdflatex >/dev/null 2>&1; then
  echo "ERROR: pdflatex is not on PATH for this LaunchAgent."
  echo "       Install it (brew install --cask basictex) — the run tailors and"
  echo "       compiles a resume PDF for every shortlisted job."
  exit 1
fi

# caffeinate -i prevents an idle sleep mid-run. The search makes ~50-60 LinkedIn
# calls at roughly one per 15 seconds, all serialized by the MCP server's profile
# lease, and tailoring every shortlisted job runs well beyond that — losing
# either half to an idle sleep would waste the lot.
cd "$REPO" || exit 1
caffeinate -i claude -p "/job-hunt" --permission-mode acceptEdits
STATUS_CODE=$?

echo "=== $(date '+%F %T') job-hunt run finished (exit $STATUS_CODE) ==="
exit $STATUS_CODE

#!/bin/bash
# Installs the job-hunt search-phase LaunchAgent into ~/Library/LaunchAgents.
#
# The agent runs in the user's Aqua GUI session, which matters: the LinkedIn MCP
# server drives a headed Chromium and a LaunchDaemon could not do that at all
# (per Apple TN2083, a daemon "is not allowed to connect to the window server").
# A *locked* screen is fine — screen lock does not tear down the GUI session — so
# this works without you being present. Logging out kills it.

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.jobwizard.search"
TARGET="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$HOME/Library/LaunchAgents" "$REPO/state/logs"
sed "s|__REPO__|$REPO|g" "$REPO/scripts/$LABEL.plist" > "$TARGET"

launchctl bootout "gui/$UID/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$UID" "$TARGET"

echo "Installed $TARGET"
echo
echo "Scheduled for 07:00 daily. On a laptop that sleeps with the lid closed it will"
echo "instead run the first time you open the lid that day — launchd coalesces the"
echo "missed firing into a single catch-up run. That is the intended behaviour, not a"
echo "fallback: see .scratch/job-hunt-speedup/issues/07-choose-unattended-trigger.md."
echo
echo "Check status:  launchctl print gui/$UID/$LABEL | head -20"
echo "Run it now:    launchctl kickstart -p gui/$UID/$LABEL"
echo "Logs:          $REPO/state/logs/search-phase.log"
echo "Uninstall:     launchctl bootout gui/$UID/$LABEL && rm $TARGET"

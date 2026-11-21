#!/bin/bash
# Wait until no node.exe with "regen-isnad-graph" in its commandline remains,
# then run mode=test exactly once.
echo "[supervisor v2] watching for regen-isnad-graph processes to exit"
while true; do
    # PowerShell-based check: count node.exe processes still running regen-isnad-graph
    n=$(powershell.exe -NoProfile -Command "(@(Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | Where-Object { \$_.CommandLine -like '*regen-isnad-graph*' -and \$_.CommandLine -notlike '*mode=test*' })).Count" 2>/dev/null | tr -d '\r\n ')
    if [ -z "$n" ]; then n=0; fi
    if [ "$n" -eq 0 ]; then
        break
    fi
    sleep 60
done
echo "[supervisor v2] all regen-isnad-graph processes have exited at $(date -u)"
ts=$(date -u +%Y%m%dT%H%M%SZ)
TEST_LOG="logs/regen-test-stdout-${ts}.log"
echo "[supervisor v2] launching mode=test, log=$TEST_LOG"
# Give the DB a moment to settle
sleep 5
npm run db:regen -- --mode=test > "$TEST_LOG" 2>&1
TEST_EXIT=$?
echo "[supervisor v2] mode=test exited with code=$TEST_EXIT at $(date -u)"
echo "$TEST_EXIT" > logs/last-test-exit-code.txt
echo "$TEST_LOG" > logs/last-test-log-path.txt

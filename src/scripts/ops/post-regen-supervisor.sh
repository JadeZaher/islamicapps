#!/bin/bash
# Wait for v2 fullregen (PID $1) to exit, then run mode=test.
REGEN_PID="$1"
REGEN_LOG="$2"
echo "[supervisor] watching regen pid=$REGEN_PID log=$REGEN_LOG"
# Poll every 60s. tasklist via cmd.exe works on Windows where kill -0 may not.
while tasklist /fi "PID eq $REGEN_PID" 2>/dev/null | grep -q "$REGEN_PID"; do
    sleep 60
done
echo "[supervisor] regen pid $REGEN_PID has exited at $(date -u)"
ts=$(date -u +%Y%m%dT%H%M%SZ)
TEST_LOG="logs/regen-test-stdout-${ts}.log"
echo "[supervisor] launching mode=test, log=$TEST_LOG"
npm run db:regen -- --mode=test > "$TEST_LOG" 2>&1
TEST_EXIT=$?
echo "[supervisor] mode=test exited with code=$TEST_EXIT at $(date -u)"
echo "$TEST_EXIT" > logs/last-test-exit-code.txt
echo "$TEST_LOG" > logs/last-test-log-path.txt

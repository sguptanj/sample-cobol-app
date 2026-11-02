#!/bin/bash

set -e

echo "Starting Phase 2 COBOL tests..."

REPORT="build/transaction-report.txt"
ACCOUNTS="build/accounts-updated.dat"
AUDIT="logs/audit.log"

for FILE in "$REPORT" "$ACCOUNTS" "$AUDIT"; do
    if [ ! -f "$FILE" ]; then
        echo "FAIL: Missing file $FILE"
        exit 1
    fi
done

APPROVED=$(grep -c "APPROVED" "$REPORT")
REJECTED=$(grep -c "REJECTED" "$REPORT")

if [ "$APPROVED" -ne 2 ]; then
    echo "FAIL: Expected 2 approved transactions"
    exit 1
fi

if [ "$REJECTED" -ne 4 ]; then
    echo "FAIL: Expected 4 rejected transactions"
    exit 1
fi

if ! grep -q "ERR-004" "$REPORT"; then
    echo "FAIL: Transaction limit validation missing"
    exit 1
fi

if ! grep -q "ERR-003" "$REPORT"; then
    echo "FAIL: Account validation missing"
    exit 1
fi

if ! grep -q "ERR-005" "$REPORT"; then
    echo "FAIL: Minimum balance validation missing"
    exit 1
fi

echo "PASS: Transaction processing"
echo "PASS: Account validation"
echo "PASS: Transaction limit validation"
echo "PASS: Minimum balance validation"
echo "PASS: Audit log generation"

echo "All Phase 2 tests passed!"

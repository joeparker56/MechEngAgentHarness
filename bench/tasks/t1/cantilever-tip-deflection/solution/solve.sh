#!/bin/bash
# Oracle solution. SOLUTION=wrong runs a deliberately flawed variant (grader must reject it):
#   harbor run -p <task> -a oracle --ae SOLUTION=wrong
set -euo pipefail
if [ "${SOLUTION:-}" = "wrong" ]; then
    python3 /solution/solve.py --wrong-units
else
    python3 /solution/solve.py
fi

#!/bin/bash
# Always (re)writes the reward; never trusts files the agent may have left in /logs/verifier.
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.json /logs/verifier/reward.txt
python3 /tests/grade.py || echo '{"reward": 0}' > /logs/verifier/reward.json

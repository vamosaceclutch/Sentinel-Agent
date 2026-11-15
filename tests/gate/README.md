# AuditGate tests (local EVM, no network, no gas)

These tests deploy `SentinelRegistry`, `AuditGate` and `GuardedLaunchpad` on an
in-memory EVM and check every verdict: not audited, score too low, safe,
expired, only-agent writes, and invalid constructor arguments.

```
cd tests/gate
npm install
python -m pip install "eth-tester[py-evm]"
node compile.js shanghai
python test_gate.py shanghai
```

Expected last line: `ALL PASS`.

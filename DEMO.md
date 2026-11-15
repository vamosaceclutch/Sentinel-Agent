# Demo script (3 minutes) and pre-flight checklist

Story: **blocked, patched, allowed.** A launchpad refuses a vulnerable vault because the on-chain audit is low,
then accepts the fixed vault because the new audit is high. No human decides, the chain does.

## Before recording (do all of this once, then rehearse)

1. Backend running (`python -m uvicorn app:app --reload`) and web page open at `http://127.0.0.1:5500/UI.html`.
2. Agent wallet has test AVAX; `.env` is filled in; `.env` is NOT in `git status`.
3. Deployed on Fuji and verified on Routescan/Sourcify (compiler 0.8.24, EVM shanghai, optimization off):
   `VulnerableVault`, `FixedVault` (both in `samples/`), `AuditGate(registry, 70, 2592000)`,
   `GuardedLaunchpad(gate)`.
4. `const GATE = "0x..."` in `UI.html` set to the AuditGate address.
5. Both vaults already audited with "stamp on chain" checked, so you have two stamps ready as a fallback.
6. Remix tab open on `GuardedLaunchpad` with the two vault addresses copied.
7. Rehearse twice with a timer. Record only after one clean run.

## Script

| Time | Do | Say |
|---|---|---|
| 0:00 | Title slide | "AI audit reports are PDFs. Nobody's smart contract can read a PDF. SentinelAgent puts the verdict on Avalanche, where contracts can read it." |
| 0:20 | UI: paste `VulnerableVault`, tick stamp, Audit | "The agent fetches the verified source, the AI reviews it, a fixed formula gives the score." |
| 0:50 | Point at score, findings, then the stamp line | "A high-severity reentrancy and an open `setOwner`. The stamp took {confirm_seconds} seconds and cost {fee_avax} AVAX." (read the real numbers on screen) |
| 1:10 | Click the Snowtrace link; back to the badge | "The page reads the chain directly and re-hashes the report: Match. Nobody can edit this score." |
| 1:30 | Remix: `GuardedLaunchpad.listProject(VulnerableVault)` | "A launchpad tries to list it. The call reverts with `NotSafe`. No human involved." |
| 1:50 | UI: click "Đề xuất bản vá bằng AI" (suggest a patch) | "The AI proposes a fix and audits it again: score before, score after. It is a suggestion, we review before deploying." |
| 2:10 | UI: audit `FixedVault` (already deployed), stamp; badge shows "Qua cổng" | "The fixed vault gets its own audit on chain." |
| 2:30 | Remix: `listProject(FixedVault)` succeeds | "Now the same launchpad accepts it." |
| 2:45 | Limits slide | "One agent key signs scores today, the AI can be wrong, tested on small contracts. Next: several auditors, Slither cross-check." |

## If something goes wrong on camera

- Gemini busy (503): the backend retries and falls back to the second model by itself; wait up to 40 seconds,
  or show the already stamped audit instead.
- Patch looks wrong: say so. "AI patches need review" is part of the message. Use the hand-written `FixedVault`.
- Never show `.env` or a private key on screen.

# DEBT.md — Known breaks we have chosen not to fix yet

Standing rule (BREAK.md): never ship an unlogged known break. Every row
has a repay trigger and an owner. Close a row by deleting it in the same
commit that repays it.

| Item | Found | Repay trigger | Owner |
|------|-------|---------------|-------|
| **No accounts.** A learner is a typed name, so anyone can read anyone's record by guessing it, and the instructor builder is open to anyone who can reach the app. A run is protected (a named run refuses another name) but the name proves nothing. This is the single thing blocking hosting. | 2026-09-17 | Before the app is reachable by anyone outside the room | Rume |
| **No licence.** The repository is public with no LICENSE file, which means all rights reserved by default: nobody may legally reuse or contribute. That is a business decision, not an engineering one, so it is flagged rather than chosen. | 2026-09-18, infrastructure review | Before inviting a contributor, a pilot institution, or a funder to look | Rume |
| Locales still have no authoring surface. Adding a country is a hand-written YAML file: fine for an engineer, impossible for a procurement officer who wants their own country in the demo. | 2026-09-17 | When a prospect asks for a country we do not ship | Rume |
| The stateless `POST /decisions/score` still scores one decision alone and writes the legacy counters. Nothing in the product calls it; it is kept so anything built against v0.4 keeps working. | 2026-09-18 | Remove at the next breaking API version, once no client uses it | Rume |
| The frontend loads fonts and icons from two CDNs. The page works without them, but a locked-down network or an offline demo loses the typography and the icons, and the CDNs see the request. | 2026-09-18, infrastructure review | Before a pilot on a managed institutional network, or self-host the four files | Rume |
| The in-process write limiter and body cap protect a single process only. Two processes behind a load balancer each get their own allowance. | 2026-09-18, infrastructure review | When the app runs as more than one process, move both to the gateway | Rume |
| No backups and no restore drill. The migrations are tested, but nothing has ever been restored from a copy. | 2026-09-18, infrastructure review | Before the first cohort's data matters | Rume |
| Abandoned sittings accumulate. `scripts/prune_runs.sh` removes them and never touches finished ones, but nothing runs it on a schedule. | 2026-09-18 | Put it on a timer when the app is hosted | Rume |

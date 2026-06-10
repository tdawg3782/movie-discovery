---
description: (audit) Generic, profile-aware code audit. Reads .omp/project-profile.md + CLAUDE.md to learn the stack and documented landmines, runs universal dimensions plus 1-3 project-specific ones via a parallel fan-out of the dedicated `auditor` agent (capable model, not cheap scouts), verifies every high/critical against the code, and writes a prioritized checkbox report to docs/audits/<date>-audit.md. READ-ONLY - never edits code.
argument-hint: "[optional: a path or area to scope the audit to]"
---

You are running a CODE AUDIT of this project. This is READ-ONLY: your ONLY write is the audit report file. Do NOT edit code, run builds, or commit.

## 1. Learn the project FIRST
Read, in order:
- `.omp/project-profile.md` — the auto-generated stack/convention profile (if present).
- `CLAUDE.md` / `AGENTS.md` — the authoritative engineering contract: conventions, banned APIs, documented gotchas, domain formulas.
- `README.md` and any `docs/` design notes.

These tell you the stack, the conventions, and the **documented landmines** — which is where the highest-value bugs hide. A documented formula or invariant tells you EXACTLY what to verify in the code. Generic-but-blind audits miss these; you will not, because you read the contract first.

## 2. Choose the dimensions
Run these UNIVERSAL dimensions (skip any that genuinely don't apply to the stack):
1. Correctness & logic bugs
2. Concurrency / async / race conditions
3. Data integrity & persistence (transactions, migrations, mappers, loss-on-crash)
4. Error handling & resilience (failure paths, swallowed errors, unsurfaced failures)
5. Security & privacy (injection, data leakage, unsafe handling, secrets)
6. Type safety & contracts (unsafe casts, nullability, exhaustiveness)
7. Performance hot paths
8. Test coverage GAPS (what is NOT tested, over-mocking that hides bugs, brittle/tautological assertions)
9. Dead / unused code & state

Then DERIVE 1-3 PROJECT-SPECIFIC dimensions from what you read in step 1 — the domain's real risk surface. Name each and state what drove it. Examples (adapt to THIS project, don't copy): a web API → auth boundaries + input validation + N+1 queries; an external-API client layer (TMDB/Radarr/Sonarr via a base client) → error/timeout/retry handling + response-shape assumptions + the "show"->"tv" convention; a frontend → state/data-fetch races + unhandled error states.

## 3. Include any specialized audit agent
If `.omp/agents/` contains a domain checker/auditor agent, run it as one of the dimensions on its relevant surface — it encodes project discipline the universal lenses don't.

## 4. Run it — fan out the `auditor` agent (parallel + strong)
Dispatch ONE `auditor` subagent per dimension (every universal one that applies + the project-specific ones you derived), **in a single parallel batch**. This is the whole point of the design: **parallel breadth** — a dedicated agent per dimension so security / concurrency / data-integrity each get full attention instead of being diluted — AND **per-agent depth** (the `auditor` is pinned to a capable model, not the cheap scouts).

**Exception — route the Security & Privacy dimension to `security-auditor`, NOT `auditor`.** When `auditor` is pinned to a cyber-safeguarded model (e.g. Claude Fable), a security audit trips the safeguard and that agent FAILS (burning retries before OMP limps over to the orchestrator). Send the **Security & Privacy** dimension to the **`security-auditor`** agent — pinned to a safeguard-free capable model (Opus) — and every other dimension to `auditor`.

Each `auditor` assignment MUST be fully self-contained (subagents share no context). Give it:
- the **dimension** it owns and exactly what to hunt for;
- the **project context** from step 1: stack, conventions, and the documented landmines / invariants / formulas to verify against;
- the **files/areas** to start from (from the profile + your own `search` / `find`);
- the standing rule: real bugs only, `file:line` + severity + concrete fix, precision over volume.

Fire them as one parallel batch and collect the findings. (Fallback: if `.omp/agents/auditor.md` is missing, audit each dimension yourself on THIS session's model — never on the cheap `explore` / `quick_task` scouts.)

If `$ARGUMENTS` names a path/area, restrict every dimension to that scope.

## 5. Verify the high/criticals
Before writing the report, re-read the cited code for every CRITICAL and HIGH finding and confirm it is real (not a hallucination, not already handled elsewhere, not a style nit). Drop or downgrade anything you cannot confirm in the actual code. Precision over volume.

## 6. Write the report
Write to `docs/audits/<YYYY-MM-DD>-audit.md` (create the folder; if today's already exists, suffix `-2`, `-3`). Structure:
- **Header:** date, stack (from the profile), and the dimensions you ran (universal + the project-specific ones you derived).
- **Findings grouped by severity** (Critical → High → Medium → Low), each a `- [ ]` checkbox with `file:line`, the bug + how it triggers + impact, and a concrete **Fix:**.
- A one-line **fix-first** recommendation at the very top.

Then summarize in chat: counts by severity + the single highest-value fix. Do NOT start fixing — that is a separate slice (`/omp-slice` off the report).
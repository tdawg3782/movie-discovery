// plan-contract.ts — pure validator: does a plan carry the orchestrator-native execution contract?
// No omp imports — unit-testable in isolation.
export interface ContractVerdict {
  ok: boolean;
  missing: string[];
}

const SENTINEL = /orchestrator-native-plan:\s*v\d+/i;
const CONTRACT_HEADING = /orchestrator execution contract/i;
const HAS_VERIFY = /\*\*Verify\b|Verify \(run as the task gate\)/i;
const BARRIER_COMMIT = /\bbarrier commit\b/i;
// Old-convention residue that means the plan was NOT rewritten for the orchestrator:
const PER_TASK_COMMIT_RESIDUE = /one task = one green commit|regen[^\n]*in this commit|per-task commit/i;

export function checkPlanContract(planText: string): ContractVerdict {
  const missing: string[] = [];
  if (!SENTINEL.test(planText)) missing.push("sentinel (<!-- orchestrator-native-plan: v1 -->)");
  if (!CONTRACT_HEADING.test(planText)) missing.push("an 'Orchestrator execution contract' section");
  if (!HAS_VERIFY.test(planText)) missing.push("per-task Verify command(s)");
  if (!BARRIER_COMMIT.test(planText)) missing.push("a barrier-commit statement");
  if (PER_TASK_COMMIT_RESIDUE.test(planText)) missing.push("REMOVE per-task-commit residue (old-convention)");
  return { ok: missing.length === 0, missing };
}

import { test } from "node:test";
import assert from "node:assert/strict";
import { checkPlanContract } from "./plan-contract.ts";

const GOOD = [
  "<!-- orchestrator-native-plan: v1 -->",
  "## Orchestrator execution contract",
  "- ONE barrier commit for the whole slice.",
  "### T1",
  "- **Verify (run as the task gate):** pwsh scripts/test-full.ps1",
].join("\n");

test("contract-clean plan passes", () => {
  const v = checkPlanContract(GOOD);
  assert.equal(v.ok, true);
  assert.deepEqual(v.missing, []);
});

test("missing sentinel fails", () => {
  const v = checkPlanContract(GOOD.replace(/<!--[\s\S]*?-->/, ""));
  assert.equal(v.ok, false);
  assert.ok(v.missing.some(m => m.includes("sentinel")));
});

test("missing Verify fails", () => {
  const v = checkPlanContract(GOOD.replace(/- \*\*Verify[^\n]*/, ""));
  assert.equal(v.ok, false);
  assert.ok(v.missing.some(m => m.includes("Verify")));
});

test("missing barrier-commit statement fails", () => {
  const v = checkPlanContract(GOOD.replace(/- ONE barrier commit[^\n]*/, ""));
  assert.equal(v.ok, false);
  assert.ok(v.missing.some(m => m.includes("barrier")));
});

test("per-task-commit residue is flagged", () => {
  const v = checkPlanContract(GOOD + "\n- one task = one green commit");
  assert.equal(v.ok, false);
  assert.ok(v.missing.some(m => m.includes("residue")));
});

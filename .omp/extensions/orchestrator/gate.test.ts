import { test } from "node:test";
import assert from "node:assert/strict";
import {
  emptyState, beginRun, reportTask, barrierReady, decideGate, needsEscalation,
} from "./gate.ts";

test("emptyState is inactive with no tasks", () => {
  const s = emptyState();
  assert.equal(s.active, false);
  assert.equal(Object.keys(s.tasks).length, 0);
  assert.equal(barrierReady(s), false);
});

test("beginRun activates and seeds pending tasks", () => {
  const s = beginRun(emptyState(), ["t1", "t2"]);
  assert.equal(s.active, true);
  assert.equal(s.tasks.t1.status, "pending");
  assert.equal(s.tasks.t2.status, "pending");
  assert.equal(barrierReady(s), false);
});

test("barrierReady requires all done AND testsGreen", () => {
  let s = beginRun(emptyState(), ["t1", "t2"]);
  s = reportTask(s, "t1", "done");
  s = reportTask(s, "t2", "done");
  assert.equal(barrierReady(s), false);
  s = reportTask(s, "t2", "done", true);
  assert.equal(barrierReady(s), true);
});

test("a failed task keeps the barrier closed", () => {
  let s = beginRun(emptyState(), ["t1"]);
  s = reportTask(s, "t1", "failed", true);
  assert.equal(barrierReady(s), false);
});

test("reportTask increments fixCount on each failure", () => {
  let s = beginRun(emptyState(), ["t1"]);
  s = reportTask(s, "t1", "failed");
  s = reportTask(s, "t1", "failed");
  assert.equal(s.tasks.t1.fixCount, 2);
});

test("git push is always blocked", () => {
  let s = beginRun(emptyState(), ["t1"]);
  s = reportTask(s, "t1", "done", true);
  const d = decideGate(s, "bash", { command: "git push origin main" });
  assert.equal(d.block, true);
  assert.match(d.reason ?? "", /push/);
});

test("git commit blocked until barrier ready, then allowed", () => {
  let s = beginRun(emptyState(), ["t1"]);
  const blocked = decideGate(s, "bash", { command: "git commit -m x" });
  assert.equal(blocked.block, true);
  assert.match(blocked.reason ?? "", /0\/1/);
  s = reportTask(s, "t1", "done", true);
  const allowed = decideGate(s, "bash", { command: "git commit -m x" });
  assert.equal(allowed.block, false);
});

test("non-git and non-bash calls pass through", () => {
  const s = beginRun(emptyState(), ["t1"]);
  assert.equal(decideGate(s, "bash", { command: "dotnet test" }).block, false);
  assert.equal(decideGate(s, "edit", {}).block, false);
});

test("gates are inert when no run is active", () => {
  const s = emptyState();
  assert.equal(decideGate(s, "bash", { command: "git commit -m x" }).block, false);
  assert.equal(decideGate(s, "bash", { command: "git push" }).block, false);
});

test("needsEscalation fires when fixCount reaches N", () => {
  let s = beginRun(emptyState(), ["t1"]);
  s = reportTask(s, "t1", "failed");
  assert.equal(needsEscalation(s, "t1", 3), false);
  s = reportTask(s, "t1", "failed");
  s = reportTask(s, "t1", "failed");
  assert.equal(needsEscalation(s, "t1", 3), true);
});

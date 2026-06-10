export type TaskStatus = "pending" | "done" | "failed";

export interface RunState {
  active: boolean;
  testsGreen: boolean;
  tasks: Record<string, { status: TaskStatus; fixCount: number }>;
}

export function emptyState(): RunState {
  return { active: false, testsGreen: false, tasks: {} };
}

export function beginRun(_prev: RunState, ids: string[]): RunState {
  const tasks: RunState["tasks"] = {};
  for (const id of ids) tasks[id] = { status: "pending", fixCount: 0 };
  return { active: true, testsGreen: false, tasks };
}

export function reportTask(
  state: RunState,
  id: string,
  status: TaskStatus,
  testsGreen?: boolean,
): RunState {
  const prev = state.tasks[id] ?? { status: "pending" as TaskStatus, fixCount: 0 };
  const fixCount = status === "failed" ? prev.fixCount + 1 : prev.fixCount;
  return {
    ...state,
    testsGreen: testsGreen ?? state.testsGreen,
    tasks: { ...state.tasks, [id]: { status, fixCount } },
  };
}

export function barrierReady(state: RunState): boolean {
  if (!state.active || !state.testsGreen) return false;
  const ids = Object.keys(state.tasks);
  if (ids.length === 0) return false;
  return ids.every(id => state.tasks[id].status === "done");
}

export interface GateDecision {
  block: boolean;
  reason?: string;
}

const GIT_COMMIT = /\bgit\s+commit\b/;
const GIT_PUSH = /\bgit\s+push\b/;

export function decideGate(
  state: RunState,
  toolName: string,
  input: { command?: string } | undefined,
): GateDecision {
  if (!state.active) return { block: false };
  if (toolName !== "bash") return { block: false };
  const cmd = String(input?.command ?? "");
  if (GIT_PUSH.test(cmd)) {
    return { block: true, reason: "stop-before-push gate - review and push manually" };
  }
  if (GIT_COMMIT.test(cmd)) {
    if (barrierReady(state)) return { block: false };
    const ids = Object.keys(state.tasks);
    const done = ids.filter(id => state.tasks[id].status === "done").length;
    const tests = state.testsGreen ? "green" : "red";
    return { block: true, reason: `commit barrier: ${done}/${ids.length} tasks done, tests ${tests}` };
  }
  return { block: false };
}

export function needsEscalation(state: RunState, id: string, maxFixes: number): boolean {
  const t = state.tasks[id];
  return !!t && t.status === "failed" && t.fixCount >= maxFixes;
}

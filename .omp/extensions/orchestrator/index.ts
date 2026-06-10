// orchestrator — gate engine (commit/push barrier).
// Thin wiring over the unit-tested pure logic in ./gate.ts.
// Loaded by omp via the subdirectory-with-index discovery rule.
import {
  emptyState, beginRun, reportTask, decideGate, needsEscalation,
  type RunState, type TaskStatus,
} from "./gate.ts";

const MAX_FIXES = 3; // self-fix iterations before escalate
let state: RunState = emptyState();

// `pi` is the ExtensionAPI, injected by omp at load time.
export default function (pi: any): void {
  const { z } = pi.zod;

  const trace = (event: string, detail: Record<string, unknown>) =>
    pi.logger.info(`[orchestrator] ${event}`, detail);

  // 1) Model declares the run + its task ids.
  pi.registerTool({
    name: "orchestrator_begin",
    label: "Orchestrator: Begin Run",
    description:
      "Start a gated execution run. Pass the plan's task ids. Until every task is " +
      "reported done AND tests are green, git commit is blocked; git push is always blocked.",
    parameters: z.object({ tasks: z.array(z.string()).min(1) }),
    async execute(_id: string, params: { tasks: string[] }) {
      state = beginRun(state, params.tasks);
      trace("begin", { tasks: params.tasks });
      return { content: [{ type: "text", text: `Run started with ${params.tasks.length} task(s). Commit gate is now ARMED.` }] };
    },
  });

  // 2) Model reports each task outcome; escalation lives here (ctx.ui is safe in execute).
  pi.registerTool({
    name: "orchestrator_report",
    label: "Orchestrator: Report Task",
    description:
      "Report a task's outcome. status: done | failed. Set testsGreen=true only when " +
      "the FULL test gate passes.",
    parameters: z.object({
      task: z.string(),
      status: z.enum(["done", "failed"]),
      testsGreen: z.boolean().optional(),
    }),
    async execute(
      _id: string,
      params: { task: string; status: TaskStatus; testsGreen?: boolean },
      _signal: unknown,
      _onUpdate: unknown,
      ctx: any,
    ) {
      state = reportTask(state, params.task, params.status, params.testsGreen);
      trace("report", { task: params.task, status: params.status, testsGreen: params.testsGreen });

      if (needsEscalation(state, params.task, MAX_FIXES)) {
        let choice: string | undefined;
        if (ctx?.ui?.select) {
          choice = await ctx.ui.select(
            `Task "${params.task}" failed after ${MAX_FIXES} self-fix attempts`,
            ["retry", "skip", "abort"],
          );
        }
        trace("escalation", { task: params.task, choice });
        const verdict = choice ?? "needs your decision (retry / skip / abort)";
        return { content: [{ type: "text", text: `ESCALATED - ${verdict}. Honor this before continuing.` }] };
      }
      return { content: [{ type: "text", text: `Recorded ${params.task}=${params.status}.` }] };
    },
  });

  // 3) The hard gate: block git commit/push as code, before execution.
  pi.on("tool_call", async (event: { toolName: string; input?: { command?: string } }) => {
    const decision = decideGate(state, event.toolName, event.input);
    if (decision.block) {
      trace("blocked", { tool: event.toolName, reason: decision.reason });
      return { block: true, reason: decision.reason };
    }
    return undefined;
  });

  pi.logger.info("[orchestrator] gate engine loaded");
}

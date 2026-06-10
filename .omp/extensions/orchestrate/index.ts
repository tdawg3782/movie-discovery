// orchestrate — /omp-slice (plan) + /omp-go (execute) front end (Phase 2).
// /omp-slice seeds a planning prompt in the CURRENT session. /omp-go spawns a
// FRESH clean-context session seeded with the execute-plan orchestrator prompt.
//
// Why /omp-go is a COMMAND, not a tool: only command handlers expose
// `newSession`/`waitForIdle` (ExtensionCommandContext). A tool's execute gets the
// base ExtensionContext and CANNOT spawn a session (it would deadlock the agent
// loop). So the agent can't auto-spawn; the human runs /omp-go after approval.
import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { isAbsolute, join, relative, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { checkPlanContract } from "./plan-contract.ts";

const HERE = dirname(fileURLToPath(import.meta.url));
const PLANNING_PROMPT = join(HERE, "planning-prompt.md");

/** Newest `.md` in docs/superpowers/plans/ (ignoring active.md), or undefined. */
function newestPlan(plansDir: string): string | undefined {
  let entries: string[];
  try {
    entries = readdirSync(plansDir);
  } catch {
    return undefined;
  }
  let best: { path: string; mtime: number } | undefined;
  for (const name of entries) {
    if (!name.endsWith(".md") || name === "active.md") continue;
    const path = join(plansDir, name);
    let mtime: number;
    try {
      mtime = statSync(path).mtimeMs;
    } catch {
      continue;
    }
    if (!best || mtime > best.mtime) best = { path, mtime };
  }
  return best?.path;
}

export default function orchestrate(pi: ExtensionAPI): void {
  // 1) /omp-slice <phase> — seed the planning prompt into THIS session.
  pi.registerCommand("omp-slice", {
    description:
      "Plan a slice interactively; when you approve, run /omp-go to execute it in a fresh session.",
    handler: async (args: string, ctx: any) => {
      if (!existsSync(PLANNING_PROMPT)) {
        ctx.ui.notify(`Missing planning prompt at ${PLANNING_PROMPT}`, "error");
        return;
      }
      const prompt = readFileSync(PLANNING_PROMPT, "utf8").replace(/\$ARGUMENTS/g, args.trim());
      pi.sendUserMessage(prompt);
    },
  });

  // 2) /omp-go [planPath] — validate the approved plan and spawn a fresh
  //    clean-context session that runs the orchestrator on it.
  pi.registerCommand("omp-go", {
    description:
      "Execute the most recently approved orchestrator-native plan in a fresh session (or pass a plan path). Validates the plan first.",
    handler: async (args: string, ctx: any) => {
      const arg = args.trim();
      const planAbs = arg
        ? (isAbsolute(arg) ? arg : join(ctx.cwd, arg))
        : newestPlan(join(ctx.cwd, "docs/superpowers/plans"));
      if (!planAbs || !existsSync(planAbs)) {
        ctx.ui.notify("No plan found to execute — run /omp-slice first (or pass a plan path).", "error");
        return;
      }
      const verdict = checkPlanContract(readFileSync(planAbs, "utf8"));
      if (!verdict.ok) {
        ctx.ui.notify(`Plan is not orchestrator-native (missing: ${verdict.missing.join("; ")}). Not executing.`, "error");
        return;
      }
      // Build the execution seed from the execute-plan command's own prompt body
      // (frontmatter stripped, $ARGUMENTS -> plan path). sendUserMessage delivers
      // this as the fresh session's first prompt — the proven /implement pattern.
      const execCmd = join(ctx.cwd, ".omp/commands/execute-plan.md");
      if (!existsSync(execCmd)) {
        ctx.ui.notify("Missing .omp/commands/execute-plan.md — cannot execute.", "error");
        return;
      }
      const relPlan = relative(ctx.cwd, planAbs).split("\\").join("/");
      const seed = readFileSync(execCmd, "utf8")
        .replace(/^---[\s\S]*?---\s*/, "")
        .replace(/\$ARGUMENTS/g, relPlan)
        .trim();
      await ctx.waitForIdle();
      const parentSession = ctx.sessionManager?.getSessionFile?.();
      await ctx.newSession(parentSession ? { parentSession } : undefined);
      pi.sendUserMessage(seed);
      ctx.ui.notify(`Executing ${relPlan} in a fresh session.`, "info");
    },
  });

  // 3) /omp-push — YOUR explicit push. The orchestrator NEVER pushes on its own
  //    (the gate hard-blocks the agent's `git push`). This command shells out
  //    git directly (outside the agent loop / gate), so only a human running it
  //    can push. Confirms branch -> remote first because a push is irreversible.
  pi.registerCommand("omp-push", {
    description:
      "Push the current branch to its remote. The orchestrator never pushes itself — this is your explicit push.",
    handler: async (_args: string, ctx: any) => {
      const cwd = ctx.cwd;
      const git = (gitArgs: string[]) => spawnSync("git", ["-C", cwd, ...gitArgs], { encoding: "utf8" });
      let branch = "HEAD";
      const b = git(["rev-parse", "--abbrev-ref", "HEAD"]);
      if (b.status === 0) branch = b.stdout.trim() || branch;
      let remote = "origin";
      const r = git(["remote"]);
      if (r.status === 0) {
        const remotes = r.stdout.trim().split(/\s+/).filter(Boolean);
        if (remotes.length) remote = remotes.includes("origin") ? "origin" : remotes[0];
        else { ctx.ui.notify("No git remote configured — nothing to push to.", "error"); return; }
      }
      const ok = await ctx.ui.confirm("Push to remote?", `Push branch '${branch}' to '${remote}'?`);
      if (!ok) { ctx.ui.notify("Push cancelled.", "info"); return; }
      const p = git(["push"]);
      if (p.status === 0) {
        const detail = (p.stderr || p.stdout || "").trim().split("\n").filter(Boolean).pop() ?? "";
        ctx.ui.notify(`Pushed '${branch}' to '${remote}'.${detail ? " " + detail : ""}`, "info");
      } else {
        const msg = (p.stderr || p.stdout || `git push exited ${p.status}`).trim().split("\n").slice(-3).join(" ");
        ctx.ui.notify(`Push failed: ${msg}`, "error");
      }
    },
  });

  pi.logger.info("[orchestrate] /omp-slice + /omp-go + /omp-push loaded");
}

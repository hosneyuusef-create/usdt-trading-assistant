#!/usr/bin/env node
/**
 * Spins up backend + frontend dev servers, waits for health checks,
 * then shuts everything down. Intended for `npm run dev:smoke`.
 */
const { spawn } = require("node:child_process");
const { once } = require("node:events");
const path = require("node:path");

const BACKEND_HEALTH_URL = process.env.DEV_SMOKE_BACKEND ?? "http://127.0.0.1:9090/health";
const FRONTEND_URL = process.env.DEV_SMOKE_FRONTEND ?? "http://127.0.0.1:5173";
const MAX_ATTEMPTS = Number(process.env.DEV_SMOKE_MAX_ATTEMPTS ?? 30);
const DELAY_MS = Number(process.env.DEV_SMOKE_DELAY_MS ?? 1000);
const isWin = process.platform === "win32";

function spawnProcess(label, args, cwd) {
  const proc = spawn("npm", args, {
    cwd,
    stdio: "inherit",
    shell: isWin,
  });
  proc.on("exit", (code) => {
    if (code !== 0) {
      console.warn(`[dev:smoke] ${label} process exited with code ${code}`);
    }
  });
  return proc;
}

async function waitFor(url, label) {
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt += 1) {
    try {
      const res = await fetch(url, { redirect: "manual" });
      if (res.ok || res.status === 200) {
        console.log(`[dev:smoke] ${label} healthy (attempt ${attempt})`);
        return;
      }
      console.log(
        `[dev:smoke] ${label} responded with ${res.status}; retrying in ${DELAY_MS}ms`
      );
    } catch (error) {
      console.log(
        `[dev:smoke] ${label} not ready (attempt ${attempt}): ${error.message}`
      );
    }
    await new Promise((resolve) => setTimeout(resolve, DELAY_MS));
  }
  throw new Error(`${label} did not become healthy after ${MAX_ATTEMPTS} attempts`);
}

async function main() {
  console.log("[dev:smoke] Starting backend and frontend dev servers…");
  const backend = spawnProcess("backend", ["run", "dev"], path.join(__dirname, "..", "backend"));
  const frontend = spawnProcess(
    "frontend",
    ["run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"],
    path.join(__dirname, "..", "frontend")
  );

  const processes = [backend, frontend];
  const shutdown = async () => {
    for (const proc of processes) {
      if (!proc.killed) {
        proc.kill("SIGINT");
      }
    }
    await Promise.all(processes.map((proc) => once(proc, "exit").catch(() => {})));
  };

  const handleSignal = async (signal) => {
    console.log(`[dev:smoke] Received ${signal}, shutting down…`);
    await shutdown();
    process.exit(1);
  };

  process.on("SIGINT", handleSignal);
  process.on("SIGTERM", handleSignal);

  try {
    await waitFor(BACKEND_HEALTH_URL, "backend");
    await waitFor(FRONTEND_URL, "frontend");
    console.log("[dev:smoke] SUCCESS: backend and frontend responded as expected.");
  } catch (error) {
    console.error("[dev:smoke] ERROR:", error.message);
    await shutdown();
    process.exit(1);
  }

  await shutdown();
  console.log("[dev:smoke] Completed smoke test and stopped dev servers.");
}

main();

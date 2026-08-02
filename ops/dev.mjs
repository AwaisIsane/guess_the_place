#!/usr/bin/env node

import { readdir, rm } from "node:fs/promises";
import { spawn } from "node:child_process";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const composeFiles = ["-f", "compose.yaml", "-f", "compose.dev.yaml"];
const cleanBuild = process.argv.includes("--clean");

process.chdir(projectRoot);

function run(command, args) {
  return new Promise((resolve, reject) => {
    console.log(`[dev] $ ${command} ${args.join(" ")}`);
    const child = spawn(command, args, {
      cwd: projectRoot,
      env: process.env,
      stdio: "inherit",
    });

    child.once("error", reject);
    child.once("exit", (code, signal) => {
      if (code === 0 || signal === "SIGINT" || signal === "SIGTERM") {
        resolve();
        return;
      }
      reject(new Error(`${command} exited with code ${code}`));
    });
  });
}

async function removePythonCaches(directory) {
  let entries;
  try {
    entries = await readdir(directory, { withFileTypes: true });
  } catch (error) {
    if (error.code === "ENOENT") return;
    throw error;
  }

  await Promise.all(
    entries.map(async (entry) => {
      const entryPath = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        if (["__pycache__", ".pytest_cache", ".ruff_cache"].includes(entry.name)) {
          await rm(entryPath, { recursive: true, force: true });
        } else if (entry.name !== ".venv") {
          await removePythonCaches(entryPath);
        }
      } else if (/\.py[co]$/.test(entry.name)) {
        await rm(entryPath, { force: true });
      }
    }),
  );
}

async function clearProjectCaches() {
  console.log("[dev] clearing project-local generated caches");
  await Promise.all([
    rm(path.join(projectRoot, "frontend", "dist"), { recursive: true, force: true }),
    rm(path.join(projectRoot, "frontend", "node_modules", ".vite"), {
      recursive: true,
      force: true,
    }),
    rm(path.join(projectRoot, ".volumes", "frontend-node-modules"), {
      recursive: true,
      force: true,
    }),
    removePythonCaches(path.join(projectRoot, "backend")),
  ]);
}

async function main() {
  if (cleanBuild) {
    await clearProjectCaches();
    await run("podman", [
      "compose",
      ...composeFiles,
      "down",
      "--remove-orphans",
      "--rmi",
      "local",
      "--volumes",
    ]);
    await run("podman", ["compose", ...composeFiles, "build", "--pull", "--no-cache"]);
  }

  console.log("[dev] serving at http://localhost:3000 with source hot reload");
  await run("podman", ["compose", ...composeFiles, "up", "--build"]);
}

main().catch((error) => {
  console.error(`[dev] ${error.message}`);
  process.exitCode = 1;
});

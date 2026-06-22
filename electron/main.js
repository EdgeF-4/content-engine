"use strict";

const { app, BrowserWindow, ipcMain, dialog, shell } = require("electron");
const { spawn, spawnSync } = require("child_process");
const path = require("path");
const fs = require("fs");

// The pipeline lives one level up from this shell.
const REPO_ROOT = path.resolve(__dirname, "..");
const OUT_DIR = path.join(REPO_ROOT, "out");

let mainWindow = null;
let running = null; // the active child process, if any

/** Pick a usable Python command for this platform. */
function pythonCommand() {
  const candidates =
    process.platform === "win32" ? ["python", "py", "python3"] : ["python3", "python"];
  for (const cmd of candidates) {
    try {
      const r = spawnSync(cmd, ["--version"], { stdio: "ignore" });
      if (r.status === 0) return cmd;
    } catch (_) {
      /* try next */
    }
  }
  return candidates[0];
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1040,
    height: 760,
    minWidth: 820,
    minHeight: 600,
    backgroundColor: "#0b0f17",
    title: "Content Engine",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.removeMenu();
  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));

  // Headless boot check used by `npm run smoke`.
  if (process.env.CE_SMOKE === "1") {
    mainWindow.webContents.once("did-finish-load", () => {
      console.log("CE_SMOKE: window created and renderer loaded");
      setTimeout(() => app.quit(), 600);
    });
  }
}

function send(channel, payload) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send(channel, payload);
  }
}

ipcMain.handle("dialog:openScript", async () => {
  const r = await dialog.showOpenDialog(mainWindow, {
    title: "Choose a script",
    properties: ["openFile"],
    filters: [{ name: "Script", extensions: ["txt", "md"] }],
  });
  return r.canceled ? null : r.filePaths[0];
});

ipcMain.handle("dialog:openVoiceover", async () => {
  const r = await dialog.showOpenDialog(mainWindow, {
    title: "Choose a voiceover",
    properties: ["openFile"],
    filters: [{ name: "Audio", extensions: ["wav", "mp3", "m4a", "aac", "ogg"] }],
  });
  return r.canceled ? null : r.filePaths[0];
});

ipcMain.on("pipeline:run", (_event, opts) => {
  if (running) return; // one job at a time
  const { script, voiceover, test, offline, noLlm } = opts || {};
  if (!script || !voiceover) {
    send("pipeline:error", "Pick both a script and a voiceover first.");
    return;
  }
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  const base = path.basename(script).replace(/\.[^.]+$/, "");
  const outPath = path.join(OUT_DIR, `${base}-${stamp}.mp4`);

  const args = [
    "-m", "content_engine", "run",
    "--script", script,
    "--voiceover", voiceover,
    "--out", outPath,
  ];
  if (test) args.push("--test");
  if (offline) args.push("--offline");
  if (noLlm) args.push("--no-llm");

  send("pipeline:log", `> ${pythonCommand()} ${args.join(" ")}\n`);
  running = spawn(pythonCommand(), args, { cwd: REPO_ROOT });

  const onData = (buf) => send("pipeline:log", buf.toString());
  running.stdout.on("data", onData);
  running.stderr.on("data", onData);
  running.on("close", (code) => {
    running = null;
    if (code === 0 && fs.existsSync(outPath)) {
      send("pipeline:done", outPath);
    } else {
      send("pipeline:error", `Pipeline exited with code ${code}.`);
    }
  });
  running.on("error", (err) => {
    running = null;
    send("pipeline:error", `Could not start the pipeline: ${err.message}`);
  });
});

ipcMain.handle("shell:openPath", async (_e, p) => shell.openPath(p));
ipcMain.handle("shell:showItem", async (_e, p) => shell.showItemInFolder(p));

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

"use strict";

const { contextBridge, ipcRenderer } = require("electron");

// A small, explicit surface. The renderer never touches Node or IPC directly.
contextBridge.exposeInMainWorld("engine", {
  selectScript: () => ipcRenderer.invoke("dialog:openScript"),
  selectVoiceover: () => ipcRenderer.invoke("dialog:openVoiceover"),
  run: (opts) => ipcRenderer.send("pipeline:run", opts),
  openPath: (p) => ipcRenderer.invoke("shell:openPath", p),
  showItem: (p) => ipcRenderer.invoke("shell:showItem", p),
  onLog: (cb) => ipcRenderer.on("pipeline:log", (_e, line) => cb(line)),
  onDone: (cb) => ipcRenderer.on("pipeline:done", (_e, out) => cb(out)),
  onError: (cb) => ipcRenderer.on("pipeline:error", (_e, msg) => cb(msg)),
});

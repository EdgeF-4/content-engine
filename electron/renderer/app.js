"use strict";

const state = { script: null, voiceover: null, output: null };

const el = (id) => document.getElementById(id);
const scriptBtn = el("pick-script");
const voBtn = el("pick-vo");
const goBtn = el("go");
const statusEl = el("status");
const logEl = el("log");
const resultEl = el("result");
const previewEl = el("preview");

function refreshGo() {
  goBtn.disabled = !(state.script && state.voiceover);
}

function setName(targetId, btn, value, fallback) {
  el(targetId).textContent = value ? value.split(/[\\/]/).pop() : fallback;
  btn.classList.toggle("chosen", Boolean(value));
}

scriptBtn.addEventListener("click", async () => {
  const p = await window.engine.selectScript();
  if (p) state.script = p;
  setName("script-name", scriptBtn, state.script, "Choose a .txt file");
  refreshGo();
});

voBtn.addEventListener("click", async () => {
  const p = await window.engine.selectVoiceover();
  if (p) state.voiceover = p;
  setName("vo-name", voBtn, state.voiceover, "Choose an audio file");
  refreshGo();
});

goBtn.addEventListener("click", () => {
  if (!state.script || !state.voiceover) return;
  logEl.textContent = "";
  resultEl.classList.add("hidden");
  statusEl.classList.remove("error");
  statusEl.textContent = "Working...";
  goBtn.disabled = true;
  goBtn.classList.add("busy");
  goBtn.textContent = "Working...";
  window.engine.run({
    script: state.script,
    voiceover: state.voiceover,
    test: el("opt-test").checked,
    offline: el("opt-offline").checked,
    noLlm: el("opt-nollm").checked,
  });
});

function resetGo() {
  goBtn.classList.remove("busy");
  goBtn.textContent = "Make video";
  refreshGo();
}

function appendLog(text) {
  logEl.textContent += text;
  logEl.scrollTop = logEl.scrollHeight;
}

window.engine.onLog((line) => appendLog(line));

window.engine.onDone((output) => {
  state.output = output;
  statusEl.textContent = "Done";
  resetGo();
  previewEl.src = "file://" + output;
  resultEl.classList.remove("hidden");
});

window.engine.onError((msg) => {
  statusEl.textContent = msg;
  statusEl.classList.add("error");
  appendLog("\n" + msg + "\n");
  resetGo();
});

el("open").addEventListener("click", () => {
  if (state.output) window.engine.openPath(state.output);
});
el("reveal").addEventListener("click", () => {
  if (state.output) window.engine.showItem(state.output);
});

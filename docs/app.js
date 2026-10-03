// Clockwork playtest page. All game rules run in Python (the same simulator used for AI
// playtesting) through Pyodide; this file only draws the state and forwards clicks.
"use strict";

const PYODIDE_DEFAULT = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";
const REPO = "2023techacc/clockwork";
const COLORS = {
  Striker: "#e8a87c", Plate: "#9cc3d5", Spring: "#c5e1a5", Mirror: "#d1c4e9", Amplifier: "#ffe082",
  Coupler: "#b39ddb", Loader: "#a5d6a7", Coolant: "#80deea", Hammer: "#ef9a9a", Magnet: "#bcaaa4",
  Primer: "#f48fb1", Assembly: "#ffcc80", Slider: "#90caf9",
};

const $ = (id) => document.getElementById(id);
let play, opts, view, version = "";
let selected = null;          // index of the selected hand part
let logHistory = [];          // [{text, fresh}]

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src;
    s.onload = resolve;
    s.onerror = () => reject(new Error("Could not load " + src));
    document.head.appendChild(s);
  });
}

async function boot() {
  const params = new URLSearchParams(location.search);
  const indexURL = params.get("pyodide") || PYODIDE_DEFAULT;
  try {
    await loadScript(indexURL + "pyodide.js");
    const py = await loadPyodide({ indexURL });
    const manifest = await (await fetch("py/manifest.json", { cache: "no-cache" })).json();
    version = manifest.version;
    py.FS.mkdirTree("/home/pyodide/clockwork");
    for (const f of manifest.files) {
      const text = await (await fetch(`py/${f}?v=${version}`)).text();
      py.FS.writeFile(`/home/pyodide/${f}`, text);
    }
    py.FS.writeFile("/home/pyodide/play.py", await (await fetch(`play.py?v=${version}`)).text());
    py.runPython("import sys; sys.path.insert(0, '/home/pyodide')");
    play = py.pyimport("play");
    opts = JSON.parse(play.options());
  } catch (err) {
    $("loading-text").textContent = "Could not load the game engine: " + err.message;
    throw err;
  }
  $("version").textContent = version;
  setupScreen();
  $("loading").hidden = true;
  $("setup").hidden = false;
}

function setupScreen() {
  for (const name of Object.keys(opts.decks)) $("deck").add(new Option(name, name));
  for (const [name, e] of Object.entries(opts.enemies)) {
    const extra = e.chime_every ? `, strikes for ${e.chime_damage} every ${e.chime_every} cranks`
      : e.crank_limit ? `, ${e.crank_limit} cranks max` : "";
    $("enemy").add(new Option(`${name} (${e.hp}±${opts.rules.hp_jitter} HP${extra})`, name));
  }
  document.querySelectorAll("[data-rule]").forEach((el) => { el.textContent = opts.rules[el.dataset.rule]; });
  const dl = $("parts");
  for (const [name, text] of Object.entries(opts.parts)) {
    const dt = document.createElement("dt");
    dt.innerHTML = COLORS[name] ? `<span class="swatch" style="background:${COLORS[name]}"></span>${name}` : name;
    const dd = document.createElement("dd");
    dd.textContent = text;
    dl.append(dt, dd);
  }
  const showDeck = () => {
    const counts = {};
    for (const p of opts.decks[$("deck").value]) counts[p] = (counts[p] || 0) + 1;
    $("deck-list").textContent = "Deck: " + Object.entries(counts).map(([k, n]) => `${n}× ${k}`).join(", ");
  };
  $("deck").onchange = showDeck;
  showDeck();
  randomSeed();
  $("random-seed").onclick = randomSeed;
  $("start").onclick = () => startFight($("deck").value, $("enemy").value, Number($("seed").value) || 0);
}

function randomSeed() { $("seed").value = Math.floor(Math.random() * 1e6); }

function startFight(deck, enemy, seed) {
  logHistory = [];
  selected = null;
  $("setup").hidden = true;
  $("result").hidden = true;
  $("game").hidden = false;
  buildGear(6);
  update(play.start(deck, enemy, seed));
}

function call(fn, ...args) {
  try {
    update(fn(...args));
  } catch (err) {
    $("status").textContent = "Error: " + err.message.split("\n").slice(-2).join(" ");
    console.error(err);
  }
}

// ---------------------------------------------------------------- gear drawing
const CX = 160, CY = 175, R = 108;
const NS = "http://www.w3.org/2000/svg";
function el(tag, attrs, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}
function polar(angleDeg, radius) {
  const a = (angleDeg * Math.PI) / 180;
  return [CX + radius * Math.sin(a), CY - radius * Math.cos(a)];
}

let rotation = 0, prevTop = null;   // accumulated gear rotation (degrees), so it turns the short way

function buildGear(n) {
  const svg = $("gear");
  svg.innerHTML = "";
  rotation = 0;
  prevTop = null;
  el("circle", { cx: CX, cy: CY, r: R, class: "rim" }, svg);
  el("path", { d: `M${CX - 10} 18 L${CX + 10} 18 L${CX} 34 Z`, class: "pointer" }, svg);
  const tp = el("text", { x: CX, y: 12, "text-anchor": "middle", "font-size": 11, fill: "currentColor" }, svg);
  tp.textContent = "Trigger Point";
  const hints = el("g", { class: "hint" }, svg);
  const [lx, ly] = polar(-360 / n, R + 58);
  const [rx, ry] = polar(360 / n, R + 58);
  el("text", { x: lx, y: ly }, hints).textContent = "next ↻";
  el("text", { x: rx, y: ry }, hints).textContent = "↺ next";
  const rotor = el("g", { id: "rotor" }, svg);
  for (let i = 0; i < n; i++) {
    const [x, y] = polar((i * 360) / n, R);       // fixed place on the gear body
    const g = el("g", { class: "slot", id: `slot-${i}`, transform: `translate(${x} ${y})` }, rotor);
    const face = el("g", { class: "face" }, g);   // counter-rotated so labels stay upright
    el("circle", { r: 33, class: "body" }, face);
    el("text", { y: -2, class: "name" }, face);
    el("text", { y: 12, class: "mod" }, face);
    g.addEventListener("click", () => onSlot(i));
  }
}

function drawGear(v) {
  const n = v.gear.length;
  if (prevTop === null) {
    rotation = (-v.top * 360) / n;
  } else if (v.top !== prevTop) {
    let d = (v.top - prevTop + n) % n;
    if (d > n / 2) d -= n;
    rotation -= (d * 360) / n;
  }
  prevTop = v.top;
  $("rotor").style.transform = `rotate(${rotation}deg)`;
  v.gear.forEach((p, i) => {
    const g = $(`slot-${i}`);
    const k = (i - v.top + n) % n;
    g.querySelector(".face").style.transform = `rotate(${-rotation}deg)`;
    g.setAttribute("class", "slot" + (p ? "" : " empty") + (k === 0 ? " top" : "") +
      (p && p.jammed ? " jammed" : "") + (selected !== null && v.can_install ? " clickable" : ""));
    g.querySelector("circle").setAttribute("fill", p ? COLORS[p.kind] || "#ddd" : "var(--slot-empty)");
    g.querySelector(".name").textContent = p ? p.kind : "empty";
    g.querySelector(".mod").textContent = p ? (p.mod ? "+" + p.mod : "") + (p.jammed ? " JAMMED" : "") : "";
    const title = g.querySelector("title") || el("title", {}, g);
    title.textContent = p ? `${p.kind}${p.mod ? " +" + p.mod : ""}: ${opts.parts[p.kind]}` : "Empty slot";
  });
}

// ---------------------------------------------------------------- rendering
function partCard(p, i, clickable) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "card" + (i !== null && i === selected ? " selected" : "");
  b.style.borderLeft = `6px solid ${COLORS[p.kind] || "#ccc"}`;
  const mod = p.mod ? ` +${p.mod}` : "";
  b.innerHTML = `<b>${p.kind}${mod}</b><small>${opts.parts[p.kind]}${p.mod ? " " + opts.parts["+" + p.mod] : ""}</small>`;
  if (clickable) b.onclick = () => { selected = selected === i ? null : i; render(); };
  else { b.classList.add("static"); b.tabIndex = -1; }
  return b;
}

function update(json) {
  view = JSON.parse(json);
  for (const line of logHistory) line.fresh = false;
  for (const text of view.new_log) logHistory.push({ text, fresh: true });
  logHistory = logHistory.slice(-300);
  if (!view.can_install || (selected !== null && selected >= view.hand.length)) selected = null;
  render();
  if (view.result) showResult();
}

function render() {
  const v = view;
  drawGear(v);
  const hand = $("hand");
  hand.innerHTML = "";
  v.hand.forEach((p, i) => hand.appendChild(partCard(p, i, v.can_install)));
  if (!v.hand.length) hand.textContent = "—";
  $("installs-left").textContent = v.phase === "install" ? `(${v.installs_left} installs left)` : "";
  const next = $("next");
  next.innerHTML = "";
  v.next.forEach((p) => next.appendChild(partCard(p, null, false)));
  if (!v.next.length) next.textContent = "—";
  $("queue-info").textContent = `(${v.queue_size} in queue, ${v.discard_size} discarded)`;

  $("turn").textContent = v.turn;
  $("hp").textContent = `${Math.max(0, v.hp)}/${v.max_hp}`;
  $("block").textContent = v.block;
  $("cp").textContent = v.crank_power;
  $("heat").textContent = `${v.heat}/${v.overheat_at}`;
  $("heat-bar").style.width = `${Math.min(100, (100 * v.heat) / v.overheat_at)}%`;
  $("enemy-name").textContent = v.enemy.name;
  $("enemy-hp").textContent = `${v.enemy.hp}/${v.enemy.max_hp} HP`;
  $("enemy-bar").style.width = `${(100 * v.enemy.hp) / v.enemy.max_hp}%`;
  $("intent").textContent = "Intent: " + (v.enemy.intent.join(", ") || (v.enemy.chime_every ? "no attack (strikes on cranks)" : "nothing"));
  const e = v.enemy;
  if (e.chime_every) {
    const left = e.chime_every - (e.cranks_used % e.chime_every);
    $("crank-limit").textContent = `Clock Tower strikes for ${e.chime_damage} on every ${e.chime_every}th crank, ` +
      `after the part that comes up. Next strike in ${left} crank${left === 1 ? "" : "s"} (Springs count).`;
  } else {
    $("crank-limit").textContent = e.crank_limit
      ? `Clock Tower: ${e.cranks_used}/${e.crank_limit} cranks used (every crank counts, Springs too)` : "";
  }

  let status = "";
  if (v.phase === "install") {
    status = v.dead_turn ? "Overheated: install if you like, then end installing (no cranks this turn)."
      : selected !== null ? "Click a gear slot to install it there." : "Pick a part to install, or choose a direction to start cranking.";
  } else if (v.phase === "crank") {
    const dir = v.turn_direction === "cw" ? "clockwise" : "counter-clockwise";
    status = v.locked ? "No more cranks this turn." : v.crank_power ? `Cranking ${dir}.` : "Out of Crank Power.";
  }
  $("status").textContent = status;
  $("go-cw").hidden = $("go-ccw").hidden = !v.can_pick_direction;
  $("go-dead").hidden = !(v.can_end_install && !v.can_pick_direction);
  $("crank").hidden = v.phase !== "crank";
  $("crank").disabled = !v.can_crank;
  $("crank").textContent = `Crank again ${v.turn_direction === "cw" ? "↻" : "↺"} (1 CP)`;
  $("end-turn").hidden = v.phase !== "crank";
  $("end-turn").disabled = !v.can_end_turn;

  const log = $("log");
  log.innerHTML = "";
  for (const line of logHistory) {
    const d = document.createElement("div");
    d.textContent = prettyLog(line.text);
    d.className = /^T\d+ /.test(line.text) ? "turn" : line.fresh ? "fresh" : "old";
    if (/^T\d+ /.test(line.text)) d.textContent = "— Turn " + line.text.match(/^T(\d+)/)[1] + " —";
    log.appendChild(d);
  }
  log.scrollTop = log.scrollHeight;
}

function prettyLog(text) {
  let m;
  if ((m = text.match(/^enemy: \('attack', (\d+)\)/))) return `Enemy attacks for ${m[1]}.`;
  if ((m = text.match(/^enemy: \('jam', (\d+), (\d+)\)/))) return `Enemy jams slot ${m[1]} for ${m[2]} turns.`;
  if (/^enemy: \('wind_back',\)/.test(text)) return "Enemy winds the gear back one step.";
  if ((m = text.match(/^enemy: \('unscrew', (\d+)\)/))) return `Enemy unscrews the part in slot ${m[1]}.`;
  return text
    .replace(/(\w)#\d+/g, "$1")
    .replace(/slot (\d+): empty, nothing happens/, "empty slot: nothing happens")
    .replace(/^recycle #(\d+) this turn: (\d+) parts, \+(\d+) Heat/, (_, k, n, h) =>
      `Queue ran low: ${n} discarded parts shuffled back in (+${h} Heat)`)
    .replace(/^free crank (cw|ccw)/, (_, d) => `Free crank ${d === "cw" ? "↻" : "↺"}`)
    .replace(/^crank (cw|ccw)/, (_, d) => `Crank ${d === "cw" ? "↻" : "↺"}`)
    .replace(/ \((cw|ccw)\)/, "")
    .replace(/ \(\+(\d+)\)/, (_, k) => k === "0" ? " (at the top)" : ` (${k} cranks away)`);
}

function onSlot(i) {
  if (selected === null || !view.can_install) return;
  const hand = selected;
  selected = null;
  call(play.install, hand, i);
}

// ---------------------------------------------------------------- results
function report() {
  return {
    version, setup: view.setup, result: view.result, reason: view.reason, summary: view.summary,
    notes: $("notes").value.trim(), actions: view.actions,
  };
}

function showResult() {
  const v = view;
  $("result").hidden = false;
  const win = v.result === "win";
  $("result-title").textContent = win ? "Victory" : "Defeat";
  $("result-title").className = v.result;
  const reasons = { hp: "Your HP reached 0.", timeout: "The fight ran too long.", "clock tower struck": "The Clock Tower struck: out of cranks." };
  $("result-text").textContent = win
    ? `You won on turn ${v.turn} with ${v.hp} HP left.`
    : `${reasons[v.reason] || v.reason} The enemy had ${v.enemy.hp} HP left (turn ${v.turn}).`;
  updateIssueLink();
  $("result").scrollIntoView({ behavior: "smooth" });
}

function updateIssueLink() {
  const r = report();
  const title = `Playtest: ${r.setup.deck} vs ${r.setup.enemy}: ${r.result}`;
  let body = (r.notes || "(no notes)") + "\n\n```json\n" + JSON.stringify(r) + "\n```";
  if (body.length > 6000) {
    const short = { ...r, actions: "(omitted, too long; paste the copied report instead)" };
    body = (r.notes || "(no notes)") + "\n\n```json\n" + JSON.stringify(short) + "\n```";
  }
  $("issue-link").href = `https://github.com/${REPO}/issues/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
}

$("notes").addEventListener("input", () => view && view.result && updateIssueLink());
$("copy-report").onclick = async () => {
  const text = JSON.stringify(report(), null, 1);
  try { await navigator.clipboard.writeText(text); } catch { window.prompt("Copy this report:", text); }
  $("copied").hidden = false;
  setTimeout(() => { $("copied").hidden = true; }, 2000);
};
$("again").onclick = () => startFight(view.setup.deck, view.setup.enemy, view.setup.seed);
$("new-fight").onclick = () => { $("result").hidden = true; $("game").hidden = true; $("setup").hidden = false; randomSeed(); };
$("abandon").onclick = () => { $("game").hidden = true; $("setup").hidden = false; };
$("go-cw").onclick = () => call(play.end_install, "cw");
$("go-ccw").onclick = () => call(play.end_install, "ccw");
$("go-dead").onclick = () => call(play.end_install, "cw");
$("crank").onclick = () => call(play.crank);
$("end-turn").onclick = () => call(play.end_turn);

boot();

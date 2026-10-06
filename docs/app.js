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
const RARITY_COLOR = { common: "#9e9e9e", uncommon: "#3f8fd2", rare: "#c9822b" };
const NODE_ICON = { fight: "⚔", elite: "☠", workshop: "⚙", rest: "☕", boss: "🕛" };

const $ = (id) => document.getElementById(id);
let play, opts, view, version = "";
let selected = null;          // index of the selected hand part
let logHistory = [];          // [{text, fresh}]
let pickedAttachment = null;  // elite reward: chosen attachment
// Fun survey, shown when a run or a single fight ends; answers go into the report (playtests/README.md).
const SURVEY = [
  ["fun", "How fun was it?"],
  ["tension", "How tense were the fights?"],
  ["agency", "Did your choices matter?"],
  ["clarity", "Was it clear what happened and why?"],
  ["variety", "Did it feel different from your earlier runs?"],
  ["again", "How much do you want to play again right now?"],
];
let ratings = {};
let startedAt = Date.now();
let decisions = 0;
let attachItem = null;        // inventory index being attached
let gearSize = 0;

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
    window.clockworkDebug = { py, play };   // for automated tests and the browser console
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
      : e.crank_limit ? `, ${e.crank_limit} cranks max` : e.armor ? `, armor ${e.armor}` : e.swing ? ", swing" : "";
    const group = e.elite ? "Elite: " : e.boss ? "Boss: " : "";
    $("enemy").add(new Option(`${group}${name} (${e.hp}±${opts.rules.hp_jitter} HP${extra})`, name));
  }
  $("boss").add(new Option("random (shown at the start)", ""));
  for (const name of opts.act_bosses[0]) $("boss").add(new Option(name, name));
  document.querySelectorAll("[data-rule]").forEach((el) => { el.textContent = opts.rules[el.dataset.rule]; });
  const dl = $("parts");
  for (const [name, text] of Object.entries(opts.parts)) {
    const dt = document.createElement("dt");
    const rarity = opts.rarity[name.replace(/^\+/, "")];
    dt.innerHTML = COLORS[name] ? `<span class="swatch" style="background:${COLORS[name]}"></span>${name}`
      : `${name}${rarity ? ` <span class="rarity" style="color:${RARITY_COLOR[rarity]}">${rarity}</span>` : ""}`;
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
  const syncMode = () => {
    const run = mode() === "run";
    $("enemy-label").hidden = run;
    $("boss-label").hidden = !run;
    $("mode-text").textContent = run
      ? `${opts.acts} acts, each ${opts.rules.stops} stops of door choices (fight, elite, Workshop, rest) and a boss. ` +
        `HP carries over; heal ${opts.rules.heal} after each win.` : "One fight at full HP.";
  };
  document.querySelectorAll("input[name=mode]").forEach((r) => { r.onchange = syncMode; });
  syncMode();
  $("start").onclick = () => {
    const seed = Number($("seed").value) || 0;
    logHistory = [];
    ratings = {}; startedAt = Date.now(); decisions = 0;
    if (mode() === "run") update(play.start_run($("deck").value, seed, $("boss").value));
    else update(play.start($("deck").value, $("enemy").value, seed));
  };
}

function mode() { return document.querySelector("input[name=mode]:checked").value; }
function randomSeed() { $("seed").value = Math.floor(Math.random() * 1e6); }

function call(fn, ...args) {
  decisions += 1;
  try {
    update(fn(...args));
  } catch (err) {
    const msg = err.message.split("\n").filter(Boolean).slice(-1)[0] || err.message;
    alert(msg.replace(/^.*Error: /, ""));
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
  gearSize = n;
  rotation = 0;
  prevTop = null;
  const slotR = n > 6 ? 27 : 33;
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
    el("circle", { r: slotR, class: "body" }, face);
    el("text", { y: -2, class: "name" }, face);
    el("text", { y: 12, class: "mod" }, face);
    g.addEventListener("click", () => onSlot(i));
  }
}

function modText(p) { return (p.mods || []).map((m) => "+" + m).join(" "); }

function drawGear(f) {
  const n = f.gear.length;
  if (n !== gearSize) buildGear(n);
  if (prevTop === null) {
    rotation = (-f.top * 360) / n;
  } else if (f.top !== prevTop) {
    let d = (f.top - prevTop + n) % n;
    if (d > n / 2) d -= n;
    rotation -= (d * 360) / n;
  }
  prevTop = f.top;
  $("rotor").style.transform = `rotate(${rotation}deg)`;
  f.gear.forEach((p, i) => {
    const g = $(`slot-${i}`);
    const k = (i - f.top + n) % n;
    g.querySelector(".face").style.transform = `rotate(${-rotation}deg)`;
    g.setAttribute("class", "slot" + (p ? "" : " empty") + (k === 0 ? " top" : "") +
      (p && p.jammed ? " jammed" : "") + (selected !== null && f.can_install ? " clickable" : ""));
    g.querySelector("circle").setAttribute("fill", p ? COLORS[p.kind] || "#ddd" : "var(--slot-empty)");
    g.querySelector(".name").textContent = p ? p.kind : "empty";
    const extra = p ? [modText(p), p.jammed ? "JAMMED" : "", p.rust ? `rust −${p.rust}` : ""].filter(Boolean).join(" ") : "";
    g.querySelector(".mod").textContent = extra;
    const title = g.querySelector("title") || el("title", {}, g);
    title.textContent = p ? `${p.kind} ${modText(p)}: ${opts.parts[p.kind]}` : "Empty slot";
  });
}

// ---------------------------------------------------------------- cards
function partCard(p, i, clickable, compact) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "card" + (i !== null && i === selected ? " selected" : "") + (compact ? " chip" : "");
  b.style.borderLeft = `6px solid ${COLORS[p.kind] || "#ccc"}`;
  const mods = p.mods || [];
  const modDesc = mods.map((m) => opts.parts["+" + m] || "").join(" ");
  const desc = `${opts.parts[p.kind]}${modDesc ? " " + modDesc : ""}`;
  b.innerHTML = compact
    ? `<b>${p.kind}</b>${mods.length ? `<small class="mods">${modText(p)}</small>` : ""}`
    : `<b>${p.kind}${mods.length ? " " + modText(p) : ""}</b><small>${desc}</small>`;
  if (compact) b.title = desc;
  if (clickable) b.onclick = () => { selected = selected === i ? null : i; render(); };
  else { b.classList.add("static"); b.tabIndex = -1; }
  return b;
}

function itemCard(mod, extra, onclick, chosen) {
  const b = document.createElement("button");
  b.type = "button";
  const rarity = opts.rarity[mod];
  b.className = "card" + (chosen ? " selected" : "");
  b.style.borderLeft = `6px solid ${RARITY_COLOR[rarity] || "#ccc"}`;
  b.innerHTML = `<b>${mod} <span class="rarity" style="color:${RARITY_COLOR[rarity]}">${rarity}</span></b>` +
    `<small>${opts.parts["+" + mod] || ""}${extra ? "<br>" + extra : ""}</small>`;
  if (onclick) b.onclick = onclick; else { b.classList.add("static"); b.tabIndex = -1; }
  return b;
}

function shopCard(inner, price, sold, onclick, color) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = "card";
  b.style.borderLeft = `6px solid ${color}`;
  b.innerHTML = inner + `<small class="price">${sold ? "sold" : price + " cogs"}</small>`;
  b.disabled = sold || view.run.cogs < price;
  b.onclick = onclick;
  return b;
}

// ---------------------------------------------------------------- update / render
function update(json) {
  const prevScreen = view && view.screen;
  view = JSON.parse(json);
  const f = view.fight;
  if (f) {
    for (const line of logHistory) line.fresh = false;
    for (const text of f.new_log) logHistory.push({ text, fresh: true });
    logHistory = logHistory.slice(-300);
    if (!f.can_install || (selected !== null && selected >= f.hand.length)) selected = null;
    if (f.turn === 1 && f.new_log.length && f.new_log[0].startsWith("T1 ")) {
      logHistory = f.new_log.map((text) => ({ text, fresh: true }));
      buildGear(f.gear.length);
    }
  }
  if (view.screen !== prevScreen) { pickedAttachment = null; attachItem = null; }
  render();
}

function show(id, on) { $(id).hidden = !on; }

function render() {
  const v = view, r = v.run, f = v.fight, screen = v.screen;
  show("setup", false);
  const fightOnScreen = f && (screen === "fight" || screen === "reward" || screen === "lost" || screen === "won");
  show("game", !!fightOnScreen);
  show("map", screen === "doors");
  show("machine-choice", screen === "start" || screen === "boss_reward");
  show("rest", screen === "rest");
  show("shop", screen === "workshop");
  show("deck-panel", !!r && screen !== "fight");
  show("result", (v.mode === "fight" && !!(f && f.result)) || ["reward", "won", "lost"].includes(screen));
  drawBanner();
  if (fightOnScreen) renderFight(f);
  if (screen === "doors") renderDoors();
  if (screen === "start" || screen === "boss_reward") renderMachineChoice();
  if (screen === "rest") renderRest();
  if (screen === "workshop") renderShop();
  if (r && screen !== "fight") renderDeck();
  if (!$("result").hidden) renderResult();
}

function drawBanner() {
  const r = view.run;
  show("run-banner", !!r);
  if (!r) return;
  const steps = [];
  for (let i = 0; i <= r.stops; i++) {
    const cls = i < r.stop ? "done" : i === r.stop ? "now" : "";
    steps.push(`<span class="step ${cls}">${i === r.stops ? "Boss" : i + 1}</span>`);
  }
  const mach = r.machine.map((m) => machineName(m.key, m.level)).join(", ");
  const bosses = r.bosses.map((b, i) => (i === r.act ? `<b>${b}</b>` : b)).join(" → ");
  b_html(`<b>Act ${r.act + 1}/${r.acts}</b><span class="steps">${steps.join("")}</span>` +
    `<span><b>HP</b> ${r.hp}/${r.max_hp}</span><span><b>Cogs</b> ${r.cogs}</span>` +
    `<span><b>Deck</b> ${r.cards.length} parts</span>` + (mach ? `<span><b>Machine</b> ${mach}</span>` : "") +
    `<span title="${opts.enemies[r.boss].pattern}"><b>Boss</b> ${r.boss}: ${opts.enemies[r.boss].note}</span>` +
    `<span class="muted"><b>Bosses</b> ${bosses}</span>`);
}
function b_html(html) { $("run-banner").innerHTML = html; }

const ROMAN = ["", "", " II", " III", " IV"];
function machineName(key, level) { return view.machine_all[key].name + (ROMAN[level] || ""); }

function renderMachineChoice() {
  const r = view.run, start = view.screen === "start";
  const last = r.history.filter((h) => h.enemy).slice(-1)[0];
  $("machine-choice-title").textContent = start ? "Choose your machine's first upgrade" : `You beat the ${last.enemy}! Choose its reward`;
  $("machine-choice-text").textContent = start
    ? "Machine upgrades only come from here and from bosses; Workshops sell level-ups for the ones you have."
    : `A machine upgrade, only from bosses. Then half your missing HP heals (now ${r.hp}/${r.max_hp}) and act ${r.act + 2} begins.`;
  const box = $("machine-choice-cards");
  box.innerHTML = "";
  for (const key of r.offer.machines) {
    const m = view.machine_all[key];
    const b = document.createElement("button");
    b.type = "button";
    b.className = "card";
    b.style.borderLeft = "6px solid #795548";
    b.innerHTML = `<b>${m.name}</b><small>${m.text}${m.max > 1 ? ` (up to level ${m.max} in Workshops)` : ""}</small>`;
    b.onclick = () => { logHistory = []; call(start ? play.choose_start : play.choose_boss_reward, key); };
    box.appendChild(b);
  }
  $("machine-choice-skip").onclick = () => call(start ? play.choose_start : play.choose_boss_reward, "");
}

function renderDoors() {
  const r = view.run;
  $("map-title").textContent = r.stop >= r.stops ? `The ${r.boss} awaits` : `Stop ${r.stop + 1} of ${r.stops}: choose a door`;
  const box = $("doors");
  box.innerHTML = "";
  r.doors.forEach((d, i) => {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "card door";
    b.innerHTML = `<span class="icon">${NODE_ICON[d] || "?"}</span><b>${d[0].toUpperCase() + d.slice(1)}</b><small>${opts.nodes[d]}</small>`;
    b.onclick = () => { logHistory = []; call(play.choose_door, i); };
    box.appendChild(b);
  });
}

function renderRest() {
  const r = view.run;
  $("rest-heal").textContent = `Heal +${r.rest_heal} HP (now ${r.hp}/${r.max_hp})`;
  $("rest-heal").onclick = () => call(play.rest, "heal", "");
  const box = $("rest-attachments");
  box.innerHTML = "";
  for (const m of r.offer.attachments) box.appendChild(itemCard(m, "", null));
  $("rest-tinker").textContent = `Tinker: take ${r.offer.attachments.join(" + ")}`;
  $("rest-tinker").onclick = () => call(play.rest, "tinker", "");
}

function renderShop() {
  const r = view.run, o = r.offer;
  $("shop-cogs").textContent = `(${r.cogs} cogs)`;
  const parts = $("shop-parts");
  parts.innerHTML = "";
  o.parts.forEach((it, i) => parts.appendChild(shopCard(`<b>${it.kind}</b><small>${opts.parts[it.kind]}</small>`,
    it.price, it.sold, () => call(play.buy, "part", i), COLORS[it.kind] || "#ccc")));
  const atts = $("shop-attachments");
  atts.innerHTML = "";
  o.attachments.forEach((it, i) => {
    const rar = opts.rarity[it.mod];
    atts.appendChild(shopCard(`<b>${it.mod} <span class="rarity" style="color:${RARITY_COLOR[rar]}">${rar}</span></b>` +
      `<small>${opts.parts["+" + it.mod]}</small>`, it.price, it.sold, () => call(play.buy, "attachment", i), RARITY_COLOR[rar]));
  });
  show("shop-machine-wrap", o.machines.length > 0);
  const mach = $("shop-machine");
  mach.innerHTML = "";
  o.machines.forEach((it, i) => mach.appendChild(shopCard(`<b>${machineName(it.key, it.level)}</b>` +
    `<small>Level ${it.level}: ${it.text} more</small>`, it.price, it.sold, () => call(play.buy, "machine", i), "#795548")));
  $("shop-repair").textContent = `Repair +${r.repair.hp} HP (${r.repair.price} cogs)`;
  $("shop-repair").disabled = r.cogs < r.repair.price || r.hp >= r.max_hp;
  $("shop-repair").onclick = () => call(play.buy, "repair", 0);
  $("remove-hint").textContent = `Remove a part for ${r.remove_price} cogs, or sell an unattached attachment: use the buttons in "Your deck" below.`;
  $("shop-leave").onclick = () => call(play.leave_workshop);
}

function renderDeck() {
  const r = view.run, inWorkshop = view.screen === "workshop";
  $("deck-count").textContent = `(${r.cards.length} parts, ${r.inventory.length} attachments in inventory)`;
  const fits = attachItem !== null ? r.inventory[attachItem].fits : [];
  $("attach-hint").textContent = attachItem !== null
    ? `Attach ${r.inventory[attachItem].mod}: click a highlighted part (permanent). Click the attachment again to cancel.`
    : r.inventory.length ? "Click an attachment in your inventory to attach it to a part." : "";
  const deck = $("deck-cards");
  deck.innerHTML = "";
  for (const c of r.cards) {
    const card = partCard({ kind: c.kind, mods: c.mods }, null, false, true);
    if (attachItem !== null && fits.includes(c.id)) {
      card.classList.remove("static");
      card.classList.add("fits");
      card.tabIndex = 0;
      card.onclick = () => {
        const mod = r.inventory[attachItem].mod;
        if (confirm(`Attach ${mod} to this ${c.kind}? It can't be removed.`)) {
          const idx = attachItem;
          attachItem = null;
          call(play.attach, idx, c.id);
        }
      };
    }
    if (inWorkshop && !c.mods.length) {
      const wrap = document.createElement("div");
      wrap.className = "with-action";
      const rm = document.createElement("button");
      rm.type = "button";
      rm.className = "link";
      rm.textContent = `remove (${r.remove_price})`;
      rm.disabled = r.cogs < r.remove_price || r.cards.length <= 6;
      rm.onclick = () => call(play.remove, c.id);
      wrap.append(card, rm);
      deck.appendChild(wrap);
    } else {
      deck.appendChild(card);
    }
  }
  const inv = $("inventory");
  inv.innerHTML = "";
  if (!r.inventory.length) inv.textContent = "—";
  r.inventory.forEach((it, i) => {
    const extra = it.fits.length ? "" : "No part it fits";
    const card = itemCard(it.mod, extra, it.fits.length ? () => { attachItem = attachItem === i ? null : i; render(); } : null,
      attachItem === i);
    if (inWorkshop) {
      const wrap = document.createElement("div");
      wrap.className = "with-action";
      const sell = document.createElement("button");
      sell.type = "button";
      sell.className = "link";
      sell.textContent = "sell";
      sell.onclick = () => call(play.sell, i);
      wrap.append(card, sell);
      inv.appendChild(wrap);
    } else {
      inv.appendChild(card);
    }
  });
}

function renderFight(f) {
  drawGear(f);
  const hand = $("hand");
  hand.innerHTML = "";
  f.hand.forEach((p, i) => hand.appendChild(partCard(p, i, f.can_install)));
  if (!f.hand.length) hand.textContent = "—";
  $("installs-left").textContent = f.phase === "install" ? `(${f.installs_left} installs left)` : "";
  const next = $("next");
  next.innerHTML = "";
  f.next.forEach((p) => next.appendChild(partCard(p, null, false)));
  if (!f.next.length) next.textContent = "—";
  $("queue-info").textContent = `(${f.queue_size} in queue, ${f.discard_size} discarded)`;

  $("turn").textContent = f.turn;
  $("hp").textContent = `${Math.max(0, f.hp)}/${f.max_hp}`;
  $("block").textContent = f.block;
  $("cp").textContent = f.crank_power;
  $("heat").textContent = `${f.heat}/${f.overheat_at}`;
  $("heat-bar").style.width = `${Math.min(100, (100 * f.heat) / f.overheat_at)}%`;
  $("enemy-name").textContent = (f.enemy.elite ? "Elite: " : "") + f.enemy.name;
  $("enemy-hp").textContent = `${f.enemy.hp}/${f.enemy.max_hp} HP`;
  $("enemy-bar").style.width = `${(100 * f.enemy.hp) / f.enemy.max_hp}%`;
  $("intent").textContent = "Intent: " + (f.enemy.intent.join(", ") || (f.enemy.chime_every ? "no attack (strikes on cranks)" : "nothing"));
  const e = f.enemy;
  if (e.chime_every) {
    const left = e.chime_every - (e.cranks_used % e.chime_every);
    $("crank-limit").textContent = `Clock Tower strikes for ${e.chime_damage} on every ${e.chime_every}th crank, ` +
      `after the part that comes up. Next strike in ${left} crank${left === 1 ? "" : "s"} (Springs count).`;
  } else {
    $("crank-limit").textContent = e.crank_limit
      ? `Clock Tower: ${e.cranks_used}/${e.crank_limit} cranks used (every crank counts, Springs too)`
      : e.armor ? `Armor ${e.armor}: every hit on it deals ${e.armor} less.`
      : e.swing ? `Swing: this turn must crank ${f.turn % 2 ? "clockwise ↻" : "counter-clockwise ↺"} (odd turns clockwise, even counter-clockwise).` : "";
  }

  let status = "";
  if (f.phase === "install") {
    status = f.dead_turn ? "Overheated: install if you like, then end installing (no cranks this turn)."
      : selected !== null ? "Click a gear slot to install it there." : "Pick a part to install, or choose a direction to start cranking.";
  } else if (f.phase === "crank") {
    const dir = f.turn_direction === "cw" ? "clockwise" : "counter-clockwise";
    status = f.locked ? "No more cranks this turn." : f.crank_power ? `Cranking ${dir}.` : "Out of Crank Power.";
  }
  $("status").textContent = status;
  $("go-cw").hidden = !f.can_cw;
  $("go-ccw").hidden = !f.can_ccw;
  $("go-dead").hidden = !(f.can_end_install && !f.can_pick_direction);
  $("crank").hidden = f.phase !== "crank";
  $("crank").disabled = !f.can_crank;
  $("crank").textContent = `Crank again ${f.turn_direction === "cw" ? "↻" : "↺"} (1 CP)`;
  $("end-turn").hidden = f.phase !== "crank";
  $("end-turn").disabled = !f.can_end_turn;
  $("abandon").hidden = !!f.result;

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
  if ((m = text.match(/^enemy: \('overclock', (\d+)\)/))) return `Enemy overclocks your machine: +${m[1]} Heat.`;
  if ((m = text.match(/^enemy: \('rust', (\d+)\)/))) return `Enemy rusts the part at the top: −${m[1]} damage/Block this fight.`;
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
  const f = view.fight;
  if (selected === null || !f || !f.can_install) return;
  const hand = selected;
  selected = null;
  call(play.install, hand, i);
}

// ---------------------------------------------------------------- results
function renderResult() {
  const v = view, f = v.fight, r = v.run, screen = v.screen;
  const reasons = { hp: "Your HP reached 0.", timeout: "The fight ran too long.", "clock tower struck": "The Clock Tower struck: out of cranks." };
  let title = "", text = "";
  if (f && f.result === "win") {
    title = "Victory";
    text = `You won on turn ${f.turn} with ${f.hp} HP left.`;
  } else if (f && f.result) {
    title = "Defeat";
    text = `${reasons[f.reason] || f.reason} The enemy had ${f.enemy.hp} HP left (turn ${f.turn}).`;
  }
  if (r) {
    const last = r.history.filter((h) => h.enemy).slice(-1)[0];
    if (screen === "reward") text += ` Looted ${last.cogs} cogs. Healed ${r.heal_after_fight}: now ${r.hp} HP.`;
    if (screen === "won") { title = "Run cleared!"; text += ` Looted ${last ? last.cogs : 0} cogs.`; }
    if (screen === "lost") title = `Run over in act ${r.act + 1}, stop ${Math.min(r.stop + 1, r.stops)} (${last ? last.enemy : ""})`;
  }
  $("result-title").textContent = title;
  $("result-title").className = screen === "lost" || (f && f.result === "loss") ? "loss" : "win";
  $("result-text").textContent = text;

  const rewarding = r && screen === "reward";
  show("reward", rewarding);
  $("again").hidden = !!r;
  if (rewarding) {
    const atts = r.offer.attachments || [];

    show("reward-att-wrap", atts.length > 0);
    if (atts.length && pickedAttachment === null) pickedAttachment = atts[0];
    const ab = $("reward-attachments");
    ab.innerHTML = "";
    for (const m of atts) ab.appendChild(itemCard(m, "", () => { pickedAttachment = m; render(); }, pickedAttachment === m));
    const cards = $("reward-cards");
    cards.innerHTML = "";
    for (const kind of r.offer.parts) {
      const c = partCard({ kind, mods: [] }, null, false);
      c.classList.remove("static");
      c.tabIndex = 0;
      c.onclick = () => call(play.take_reward, kind, pickedAttachment || "", false);
      cards.appendChild(c);
    }
    $("scrap-reward").textContent = `Scrap the part for ${r.scrap} cogs`;
    $("scrap-reward").onclick = () => call(play.take_reward, "", pickedAttachment || "", true);
    $("skip-reward").onclick = () => call(play.take_reward, "", pickedAttachment || "", false);
  }
  renderSurvey(screen === "won" || screen === "lost" || (!r && !!(f && f.result)));
  $("run-history").textContent = r ? r.history.map((h) => h.enemy
    ? `${(h.act || 0) + 1}-${h.stop >= r.stops ? "Boss" : h.stop + 1}. ${h.enemy}: ${h.result === "win" ? "won" : "lost"}, HP ${h.hp_start} → ${h.hp_end}` +
      (h.cogs ? `, +${h.cogs} cogs` : "") + (h.reward ? `, ${h.reward === "scrapped" ? "scrapped" : "took " + h.reward}` : "") +
      (h.attachment ? `, +${h.attachment}` : "") + (h.boss_reward ? `, boss reward ${v.machine_all[h.boss_reward].name}` : "")
    : `${h.stop + 1}. ${h.node}${h.choice ? ": " + h.choice : ""}`).join("  ·  ") : "";
  updateIssueLink();
}

function report() {
  const notes = $("notes").value.trim(), r = view.run, f = view.fight;
  const extra = { ratings: { ...ratings }, minutes: Math.round((Date.now() - startedAt) / 6000) / 10, decisions };
  if (r) {
    return { version, mode: "run", setup: view.setup, status: r.phase, stop: r.stop, hp: r.hp, cogs: r.cogs,
      deck: r.cards.map((c) => c.kind + c.mods.map((m) => "+" + m).join("")),
      inventory: r.inventory.map((i) => i.mod), machine: r.machine.map((m) => m.key), history: r.history,
      notes, ...extra };
  }
  return { version, mode: "fight", setup: view.setup, result: f.result, reason: f.reason, summary: f.summary,
    notes, actions: f.actions, ...extra };
}

function renderSurvey(ended) {
  show("survey", ended);
  if (!ended) return;
  const box = $("survey-questions");
  box.innerHTML = "";
  for (const [key, question] of SURVEY) {
    const label = document.createElement("span");
    label.textContent = question;
    const scale = document.createElement("span");
    scale.className = "scale";
    for (let v = 1; v <= 5; v++) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = v;
      b.className = ratings[key] === v ? "chosen" : "";
      b.setAttribute("aria-label", `${question} ${v} of 5`);
      b.onclick = () => { ratings[key] = v; renderSurvey(true); updateIssueLink(); };
      scale.appendChild(b);
    }
    box.append(label, scale);
  }
}

function updateIssueLink() {
  const r = report();
  const title = r.mode === "run"
    ? `Playtest run: ${r.setup.deck}: ${r.status === "won" ? "cleared" : r.status === "lost" ? `lost at stop ${r.stop + 1}` : `stop ${r.stop + 1}`}`
    : `Playtest: ${r.setup.deck} vs ${r.setup.enemy}: ${r.result}`;
  let body = (r.notes || "(no notes)") + "\n\n```json\n" + JSON.stringify(r) + "\n```";
  if (body.length > 6000) {
    const short = r.mode === "run"
      ? { ...r, history: r.history.map(({ actions, ...h }) => h), note: "actions omitted; paste the copied report" }
      : { ...r, actions: "(omitted, too long; paste the copied report instead)" };
    body = (r.notes || "(no notes)") + "\n\n```json\n" + JSON.stringify(short) + "\n```";
  }
  $("issue-link").href = `https://github.com/${REPO}/issues/new?title=${encodeURIComponent(title)}&body=${encodeURIComponent(body)}`;
}

function newGame() {
  ratings = {};
  for (const id of ["result", "game", "run-banner", "map", "rest", "shop", "deck-panel"]) show(id, false);
  show("setup", true);
  randomSeed();
}

$("notes").addEventListener("input", () => view && updateIssueLink());
$("copy-report").onclick = async () => {
  const text = JSON.stringify(report(), null, 1);
  try { await navigator.clipboard.writeText(text); } catch { window.prompt("Copy this report:", text); }
  $("copied").hidden = false;
  setTimeout(() => { $("copied").hidden = true; }, 2000);
};
$("again").onclick = () => { logHistory = []; ratings = {}; startedAt = Date.now(); decisions = 0; update(play.start(view.setup.deck, view.setup.enemy, view.setup.seed)); };
$("new-fight").onclick = newGame;
$("abandon").onclick = () => { if (confirm("Abandon this game?")) newGame(); };
$("go-cw").onclick = () => call(play.end_install, "cw");
$("go-ccw").onclick = () => call(play.end_install, "ccw");
$("go-dead").onclick = () => call(play.end_install, "cw");
$("crank").onclick = () => call(play.crank);
$("end-turn").onclick = () => call(play.end_turn);

boot();

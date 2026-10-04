# Clockwork: Run Structure Options

Design options for everything around the fights: the map, money, the Workshop (shop), part upgrades, attachments and elite fights. Each topic has 3–4 options with trade-offs, a recommendation, and what the simulator can measure before anyone playtests it.

**Facts from the simulator that shape these choices** (see AI-Playtesting-Roadmap.md):
- **Parts stay on the gear once installed.** A bigger deck barely dilutes a key part. Removing parts matters less than in Slay the Spire, and adding parts costs less.
- **A single strong part swings a fight.** One Hammer was once worth +56 win-rate points, and attachments are worth about one good part pick (Coil on the starter Spring +21, Polish +15). Strong items should be rare, and offered as choices.
- **HP carries over.** Normal fights currently cost a casual player about 15 HP and almost never kill, so a run has no real danger before the boss. **Elites are needed.**
- **Clockwork's identity is timing and position:** which part comes up when, and the per-turn direction choice. Options that echo this score better than generic ones.

---

## 1. Map

| Option | How it works | Good | Bad |
|---|---|---|---|
| **A. Branching map (Slay the Spire)** | Rows of nodes; pick a path upward. Node types: fight, elite, Workshop, rest, event, treasure. | Proven and readable; long-term route planning ("reach the Workshop before the elite"). | Generic; players will call it a clone. |
| **B. Clock-ring district** | The district is a ring of 12 nodes like a clock face. Each step you advance 1 or 2 nodes clockwise. Every 3 steps the outer ring turns one notch, changing which nodes line up ahead. | Mirrors the core mechanic: plan around a rotating board. Distinctive. | Harder to read; needs good visuals; more design risk. |
| **C. Door choices (Hades style)** | A corridor of ~10 stops. At each stop, pick 1 of 2–3 doors, each showing the node type and its reward. | Simplest to build and simulate; a meaningful choice every step; works on the playtest page now. | Little long-term planning. |
| **D. Twelve hours to midnight** | A free-roam district graph. Each node costs 1–3 "hours" (a fight 2, an elite 3, the Workshop 1, rest 2), and the boss strikes at midnight (12 hours). You choose how many fights versus Workshops versus rests to fit in. | Echoes the Clock Tower; turns "how greedy am I?" into one clear budget. | Players can skip fights entirely, so the budget needs tuning; less of a path-shape puzzle. |

**Recommendation:** start with **C** for the playtest prototype. It's cheap, every step is a decision, and the simulator can play it. If you want a signature feature later, prototype **B** or **D**. Both make the map feel like Clockwork rather than a Slay the Spire map with gears drawn on it. A on its own is safe but forgettable.

**Simulator check:** run length, HP at the boss and how often each node type gets picked, using the agents plus a simple route policy (take an elite when HP > X).

---

## 2. Money ("cogs")

| Option | How it works | Good | Bad |
|---|---|---|---|
| **A. Flat income** | Normal fight 15, elite 35, boss 70 cogs (plus a little random variance). | Predictable; easy to balance. | No decisions involved. |
| **B. Performance income** | Bonus cogs for a quick win (≤ N turns) or finishing without an Overheat. | Rewards skill; adds a reason to play efficiently. | Rich get richer; punishes slower, safer play, which casual players need. |
| **C. Scrap** | After a fight you may **scrap** the part reward for cogs instead of taking a part (skip = 10 cogs). At the Workshop you can scrap deck parts for a little money. | Ties deck-building to the economy; makes skipping a real choice. | Slightly more to explain. |
| **D. No money: pay with HP** | Workshops take HP instead of cogs ("Blood oil": 8 HP for a part). | Makes HP carry-over the single resource; very tense. | Hard to balance with healing; feels punishing. |

**Recommendation:** **A + C.** Flat income keeps balance simple, and scrapping makes "skip" worth something. B could come back later as a small bonus.

---

## 3. Workshop (shop)

| Option | How it works | Good | Bad |
|---|---|---|---|
| **A. Classic shop** | Buy 3–4 parts (40–80 cogs), 1 attachment (90), part removal (50, rising), repair 15 HP (30). | Familiar; covers every need. | Generic; many prices to balance. |
| **B. Services only** | No parts for sale (parts come from rewards). Services: remove, upgrade (part+), fit an attachment, repair. | Focused; makes rewards matter more. | Less exciting to visit. |
| **C. Trade bench** | Swap one deck part for 1 of 3 random parts; the first swap is free and each one after costs more. Plus paid repair. | Cheap on money; helps reshape a deck; fits a tinkerer theme. | Random; weaker for targeting a strategy. |
| **D. Commission** | Order a specific part type now; it's delivered after your next fight, for a deposit. | Rewards planning; gets you the exact part you need. | Delay feels bad if you die; one more system. |

The Workshop is also the natural home for the **machine upgrades** in Rules.md §6 (Bigger Gear, Second Gear, Flywheel): 1 offered per Workshop, expensive (150+).

**Recommendation:** **A, trimmed:** 3 parts, 1 attachment, 1 machine upgrade, plus remove and repair. Removal should probably be cheaper than in Slay the Spire, because dilution matters less in Clockwork. Let the simulator say how much a removal is actually worth.

---

## 4. Part upgrades

| Option | How it works | Good | Bad |
|---|---|---|---|
| **A. Part+ versions** | Each part has an upgraded version: Striker+ 9 damage, Plate+ 9 Block, Spring+ 1 less Heat, Hammer+ 12 damage, Coolant+ removes 5, and so on. Upgrade at a rest site ("rest **or** tune up") or at the Workshop. | Simple; easy to sweep in the simulator; the rest-site choice is a proven tension. | Numbers only; not exciting. |
| **B. Upgrades are attachments** | No separate upgrade system: "upgrading" means fitting an attachment. Add generic attachments so every part has some. | One system instead of two; easier to learn. | Loses the cheap "small boost" choice; needs many attachments. |
| **C. Machine upgrades** | Upgrade the machine, not parts: +1 Crank Power, +2 Heat capacity, +1 install per turn, a second Trigger Point (Double Pointer), Bigger Gear. Rare: boss rewards and expensive Workshop items. | Big, run-defining moments; very Clockwork. | Each one is a large balance swing; must be rare. |
| **D. Wear-in** | Parts improve with use: after triggering 8 times across a run, a part upgrades itself to its + version. | Rewards your core parts; no menus. | Invisible unless shown well; snowballs toward one strategy. |

**Recommendation:** **A for parts** (rest site: heal **or** upgrade one part), plus **C as rare boss rewards** (pick 1 of 3 machine upgrades after each district boss). Attachments stay their own, rarer system (below). Rest sites can then replace the flat 10-HP heal after every fight.

---

## 5. Attachments in a run

Current attachments: Coil (Spring), Polish (Mirror), Clamp (Magnet) and Feeder (Loader). For attachments to show up often, more types are needed, including **generic** ones that fit any part. Examples:
- **Heat Sink:** this part's triggers cost 1 less Heat.
- **Bracing:** immune to Jam, Rust and Unscrew.
- **Counterweight:** +2 Block whenever it triggers.

| Option | How you get one | Good | Bad |
|---|---|---|---|
| **A. Elite drops** | Beating an elite offers 1 of 2–3 attachments; fit it to a part in your deck right away. | Makes elites worth the risk; attachments feel earned. | Players who avoid elites never see attachments. |
| **B. Workshop item** | Each Workshop sells 1 attachment and fits it for you. | Player control; money gets a premium use. | Competes with parts and removal for money. |
| **C. Workbench node** | A map node (like treasure) where you choose 1 of 3 attachments, or take a free part upgrade instead. | Reliable access; easy to place on any map type. | Less exciting than earning it. |
| **D. Mastery** | A part that triggers 10 times in a run unlocks a choice of attachments for it. | Ties attachments to how you actually play; organic. | Hard to follow; favours parts you already use. |

**Rules to decide either way:**
- an attachment stays with that part copy, including when it's replaced into the discard and reinstalled later;
- one attachment per part;
- whether a part can lose its attachment (for example, Rust strips it).

**Recommendation:** **A + B.** Elites drop a choice of 2, and each Workshop sells 1. Aim for about **2–4 attachments per run**: they're worth about a whole good part pick, so more than that would flatten deck choices. Add 3–4 generic attachments so drops are never dead.

---

## 6. Elite fights

Elites are needed because normal fights almost never kill (a casual player reaches the boss 98–100% of the time in the mini-run). Target for a casual player: win about 85%, losing about 25 HP. Reward: an attachment choice, a part reward and more cogs.

| Option | Concept | Good | Bad |
|---|---|---|---|
| **A. Machine attackers** | Normal enemy shapes, plus abilities that hit your gear: Rust, Overclock, double Jam, Unscrew. | Uses existing systems; tests machine resilience. Only Rust needs a definition. | Can feel unfair if the gear gets wrecked; needs counterplay parts (Bracing). |
| **B. Rule benders** | Each elite changes one rule, like a mini-boss: the gear spins opposite on odd turns (Reverse Engine), parts shift one slot each turn, or only the 2nd crank each turn triggers. | Tests adaptability; the most memorable. | Each needs its own code and its own balance pass. |
| **C. Wagers** | Before an elite fight, choose a condition ("win within 6 turns", "never overheat", "no Block") for a bigger reward. | Player-driven risk; teaches skill expression. | Optional difficulty can be ignored; more UI. |
| **D. Two enemies** | Elites come as a pair, for example a Shield Drone protecting a Cannon. Damage hits the front enemy unless a part says otherwise. | Adds targeting decisions; new part design space (pierce, splash). | Needs targeting rules throughout the engine; the biggest change. |

**Example elites for A** (first-guess numbers, to be tuned in the simulator):
- **Overclocker** (70 HP, attack 6): every 2nd turn, *Overclock* adds +3 Heat to your machine, pushing you toward Overheat.
- **Rust Golem** (80 HP, attack 8): *Rust*, the part at the Trigger Point deals and blocks 2 less for the rest of the fight. That also defines the open "Rust" term.
- **Pickpocket** (55 HP, attack 5): *Unscrew* every turn. The parts it takes go back to your discard pile, so you're forced to reinstall.
- **Jammer Prime** (75 HP, attack 7): jams 2 parts every other turn.

**Recommendation:** **A first**, since it's cheap and fills the danger gap now. Add **B** as the second wave of elites for variety. Keep D for later; it's a big engine change.

---

## Recommended prototype package

1. **Map:** door choices (C), about 10 stops per district, then the boss. Node types: fight, elite, Workshop, rest, Workbench.
2. **Money:** cogs, flat income plus scrapping instead of skipping.
3. **Workshop:** 3 parts, 1 attachment, 1 machine upgrade, remove, repair.
4. **Upgrades:** part+ versions at rest sites (heal **or** upgrade); machine upgrades as boss rewards.
5. **Attachments:** elite drops (choose 1 of 2) and 1 per Workshop; add 3–4 generic attachments.
6. **Elites:** machine attackers (Overclocker, Rust Golem, Pickpocket, Jammer Prime).
7. **Healing:** replace the flat 10 HP after every fight with rest sites, or keep a smaller heal (5).

**What the simulator can check before playtesting:**
- each elite against the 25-HP / 85% target;
- the value of each part+ upgrade, and of removal, with partial-deck runs;
- cogs per run against Workshop prices;
- whole-district runs with a simple route policy, compared with the current 74% casual clear rate.

---

## Decisions (designer, 2026-10-04)

### Map
- **Real game: D, "twelve hours to midnight."** A free-roam district graph. Each node costs hours (draft costs: fight 2, elite 3, Workshop 1, rest 2, event 1), and the district boss strikes at midnight (12 hours). You choose how much to fit in before then: more fights for more loot, or more rests for safety. Open questions:
  - what happens if the hours run out mid-route: the boss arrives early, so plan for it;
  - whether some nodes can be seen but are locked behind others;
  - whether parts or attachments can buy time.
- **Playtest prototype: C, door choices.** About 9 stops per district, then the boss. Each stop offers 2–3 doors, each showing its node type.

### Money: cogs, looted from enemies
- **Each enemy carries a set amount of cogs that fits its design.** Harder enemies carry more, and enemies of the same level stay close to each other (small variance).
- **Scrapping:** a part reward can be scrapped for cogs instead of taken.

### Workshop
- **Real game: D + A.** *Commissions:* order a specific part or attachment, delivered after your next fight, for a deposit. *Shop shelf:* cheap, ready-made items.
- **Playtest prototype: A.** Parts for sale, attachments for sale, 1 machine upgrade, part removal and repair. Unattached attachments can be sold.

### Upgrades
- **Upgrades are attachments (B).** The content is roughly what "+" versions would have been (+damage, +Block, less Heat), but delivered as things you bolt onto a part, which suits a tinkering game.
- **Machine upgrades (C) exist in the game.** They improve the machine: +1 Crank Power, +2 Heat capacity, +1 install per turn, Bigger Gear. In the prototype they're a rare, expensive Workshop item; later they're also boss rewards between districts.

### Attachments
- **Attachments are items with a rarity:** common, uncommon or rare.
- **Sources:** a rest site gives a **common** one; elites and the Workshop give **uncommon or rare** ones.
- **Unattached attachments sit in your inventory** and can be sold at a Workshop.
- **Once attached, an attachment can't normally be removed,** and it stays with that part copy, including through the discard and reinstalls.
- **A part can hold several attachments, up to a limit** (prototype: 2, no duplicates on one part).

### Elites
- **Now: machine attackers (A).**
- **Later: rule-benders (B) and enemy pairs (D)** will probably be added.

### Prototype numbers (simulator / playtest page)
- **District:** 9 stops; stops 1–2 are fights; stops 3–8 offer 3 doors weighted fight 4 / elite 2 / Workshop 1.5 / rest 1.5; stop 9 offers a rest site or a Workshop; then the boss.
- **Enemy growth:** HP and attacks × (1 + 0.11 × stop/9). Heal 5 HP after each win.
- **Cogs:** normal 12–16, elite 30–36, boss 60 (±10%). Scrapping a part reward pays 10.
- **Part rewards:** pick 1 of 3. Tiers: common (Spring, Coolant, Mirror), uncommon (Amplifier, Coupler, Loader, Magnet, Slider, Primer, Assembly), rare (Hammer).
- **Rest site:** heal 15, or 1 of 2 common attachments.
- **Elite loot:** a part reward, plus 1 of 2 uncommon or rare attachments.
- **Workshop prices:** parts 30/45/65 by tier; attachments 30/55/90 by rarity; repair 15 HP for 25; removal 40, then +15 each time; selling an attachment pays half its price.
- **Machine upgrades** (sometimes in the Workshop):
  - Flywheel (+1 Crank Power), 120;
  - Heat Housing (+2 Heat capacity), 110;
  - Extra Hands (+1 install per turn), 130;
  - Bigger Gear (8 slots), 120.
- **Attachments:**
  - common: Sharpened (+2 damage), Counterweight (+2 Block), Bracing (immune to Jam/Rust/Unscrew);
  - uncommon: Heat Sink (−1 Heat), Coil, Polish, Clamp, Feeder;
  - rare: Governor (no Heat), Echo (triggers twice, once per turn).

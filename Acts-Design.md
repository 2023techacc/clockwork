# Clockwork: Acts 2 and 3 Options

Design options for turning the one-district run into a three-act run (called "acts" here; the name is open). Each question has 3–4 options with trade-offs, a recommendation, and what the simulator can check. Prices for parts, attachments and machine upgrades are left until the acts exist, since they depend on total income.

**Facts that shape these choices** (AI-Playtesting-Roadmap.md, Results v10–v16):
- **One district today:** 9 door stops, then 1 of 5 bosses. A casual player clears about 65%, a careless one about 43%, an expert about 87%.
- **What a district gives:** about 7 parts, 2 attachments, about 1 machine upgrade and ~110 cogs. A deck ends act 1 with about 14 parts.
- **Parts stay on the gear once installed.** A bigger deck only slows down how soon key parts are installed; it doesn't push them off the gear. Deck growth hurts less than in Slay the Spire, but the effect hasn't been measured on 25-part decks.
- **Enemies grow through the district** (×1 to ×1.3 HP and attacks). A second and third act need their own growth, or new enemies, or both.
- **Mechanics already built:** jam, wind back, unscrew, rust, overclock (Heat), chime, armor and swing. New enemies can mix these without new code.

---

## 1. Difficulty targets for the whole run

If every act stayed as hard as act 1 is now, only about 1 casual run in 4 would finish (0.65³). So the act-1 tuning will be redone against new targets.

| Option | Casual player per act | Whole run (casual) | Good | Bad |
|---|---|---|---|---|
| **A. Rising curve** | act 1 ~90%, act 2 ~75%, act 3 ~55% | ~37% | Act 1 teaches; act 3 is the real test. The usual roguelike shape. | Act 1 may feel easy to experts. |
| **B. Flat** | each act ~80% | ~50% | Every act matters equally; simple to tune. | No sense of rising stakes; the final act doesn't feel like a climax. |
| **C. Hard and short-lived** | act 1 ~85%, act 2 ~60%, act 3 ~50% | ~25% | Wins feel earned (Slay the Spire's ~20–30% for good players). | Casual players rarely see act 3, so act-3 content is wasted on them. |
| **D. Set by skill, not by act** | whole run: careless ~10%, casual ~35%, expert ~70%; per-act numbers fall out of tuning | ~35% | Targets what players feel (how often *I* win); keeps a wide skill gap. | Per-act difficulty can come out lumpy unless it's checked separately. |

**Recommendation:** **A**, checked with **D**'s skill targets. Act 1 at ~90% gives new players a full first act and makes act 3 the climax. Whole-run targets of careless ~10%, casual ~35% and expert ~70% keep skill mattering.

**Simulator check:** per-act clear rates and HP at each boss for all three player strengths, with the act-aware automated player.

---

## 2. What carries over between acts

Parts, attachments and machine upgrades carry over in every option. The question is HP, cogs, and what happens in between.

| Option | How it works | Good | Bad |
|---|---|---|---|
| **A. Full heal** | HP back to max at each act start; cogs carry. | Each act starts clean; easy to tune each act alone. | HP management only matters within an act; the boss fight's cost is erased. |
| **B. Partial heal** | Heal half of the missing HP at each act start; cogs carry. | Damage still matters across acts, but a bad act doesn't doom the run. | Harder to tune: act 2's difficulty depends on act 1's leftovers. |
| **C. No heal** | HP is one resource for the whole run; more rest sites in later acts. | Every point of damage matters; strongest tension. | One bad fight early can end a run long after; rest choices dominate. |
| **D. Workshop break** | Full heal plus one free "overhaul" choice between acts: a machine upgrade, removing 2 parts, or a rare attachment. Cogs carry. | A reward moment between acts; a chance to steer the build. | Another source of power to balance; slightly longer runs. |

**Recommendation:** **B**, or **D** if you want a ceremony between acts. B keeps HP meaningful without the swingy "doomed run" of C. D adds a strong, readable decision point.

**Simulator check:** HP at act starts and how often runs die in act 2 or 3 because of act-1 damage (B, C), versus act-start HP being irrelevant (A, D).

---

## 3. New content for acts 2 and 3

Today there are 4 normal enemies, 4 elites and 5 bosses.

| Option | How it works | Good | Bad |
|---|---|---|---|
| **A. Themed districts** | Each act has its own pool: about 4 normal enemies, 3–4 elites and 1–2 bosses, built around a theme (e.g. act 2 a foundry: Heat and armor; act 3 the clockworks: swing, chimes, time). | Each act feels different; themes guide which builds shine. | The most content to design, about 8 new normal enemies and 6 new elites. |
| **B. Veterans** | The same enemies, stronger, with an added trait in later acts (e.g. "armored", "swinging", "overclocking" on top of their pattern). | Little new content; reuses tuned enemies. | Acts feel alike; the variety comes from traits only. |
| **C. Pairs** | Act 2 adds a new pool; act 3 sends enemies in pairs (two weaker enemies at once, each with its own intent). | Act 3 asks a new question (whom to block, whom to kill first) without many new enemies. | Fights with two enemies need new engine and page support. |
| **D. Bosses by act** | Split the 5 bosses across acts: act 1 Clock Tower or Pendulum, act 2 Furnace or Dismantler, act 3 Iron Colossus or a new final boss. | Uses existing work; each act still ends on a choice of 2. | Act-1 players see only 2 bosses; boss numbers need retuning per act. |

**Rarity across acts** (for any option): reward and Workshop part weights shift toward uncommon and rare in later acts, e.g. common 5 / uncommon 4 / rare 1 in act 1, then 3/4/2, then 2/4/3.

**Recommendation:** **A**, with **D** for the bosses. Themed districts are the most work but make each act memorable, and the existing mechanics cover most themes. Start with B (veterans) as a quick placeholder so the simulator can tune economy and difficulty before the new enemies exist. Pairs (C) are a good later addition for act 3.

**Simulator check:** each new enemy tuned to an HP-cost target for its act (as with act 1's ~15 HP normals and ~25 HP elites), and each boss to the act's boss target.

---

## 4. Deck growth

At today's pace, a deck holds about 14 parts after act 1 and about 25 after act 3. With 3 parts offered per turn from the queue, key parts arrive less often in a big deck, but once installed they stay.

| Option | How it works | Good | Bad |
|---|---|---|---|
| **A. Do nothing (measure first)** | Keep the current rules; let deck size be the player's choice. | No new rules; skipping parts is already a choice (scrap for cogs). | If dilution turns out to matter, act 3 decks feel sluggish. |
| **B. Cheaper thinning** | Removal gets cheaper, rest sites can remove a part instead of healing, and scrapping a reward also lets you remove a part. | Players control deck size; familiar to deckbuilder players. | More decisions at every node; removing basics may become an auto-pick. |
| **C. Deck limit** | A cap (e.g. 20 parts). Taking a part beyond it means scrapping one. | Every pick in late acts becomes a trade-off; deck size stays tunable. | A hard rule that can feel restrictive; less of a "big machine" fantasy. |
| **D. Bigger offer later** | Parts offered per turn go from 3 to 4 in act 2 (or as a machine upgrade, the tested "Wide Hopper"). | Fits the machine theme (a bigger hopper); dilution solved by throughput. | Changes fight pacing; act-2 fights need retuning around more choice per turn. |

**Recommendation:** **A first, then B if needed.** Parts staying on the gear means dilution may already be mild. The simulator can measure it directly: the same key parts in a 14-part deck versus a 25-part deck. If it hurts, cheaper thinning (B) is the gentlest fix.

**Simulator check:** win rate of a fixed set of key parts as the deck grows from 14 to 25 parts, and how often a policy that removes basics beats one that doesn't.

---

## 5. Machine upgrades in a longer run

There are 4 upgrades today, and a run gets about 1. Over three acts, most players would own all four.

| Option | How it works | Good | Bad |
|---|---|---|---|
| **A. A bigger pool** | 8–10 upgrades (Reinforced Frame and Wide Hopper are already tested; more can be designed), so no run gets them all. | Every run's machine differs; more build variety. | More content to balance; some upgrades will be strictly better. |
| **B. Levels** | Each upgrade has levels I–III (Flywheel I: +1 Crank Power, II: +2...) at rising prices. | Few new ideas needed; clear long-term goals to save for. | Stacking levels can break the Heat and crank limits; less variety. |
| **C. Act-themed upgrades** | Each act's Workshop offers its own set (act 2: Heat upgrades, act 3: gear upgrades). | Ties upgrades to the act's theme and enemies. | Players can't plan across acts; content tied to acts. |
| **D. Limited slots** | The machine has 3 upgrade slots (more slots could be an upgrade). A new upgrade can replace an old one. | Forces a choice between upgrades; caps total power. | Swapping can feel like losing progress; needs a clear interface. |

**Recommendation:** **A + D:** a pool of about 8 with 3 slots. The pool keeps runs varied, the slots keep act 3 from snowballing, and choosing what to keep is a good decision.

**Simulator check:** run clear rate for each upgrade (as in Results v16), and for each 3-upgrade combination, to catch combos that dominate.

---

## 6. Which map the acts use

The playtest uses door choices (C in Run-Design.md); the real game is planned as "twelve hours to midnight" (D).

| Option | How it works | Good | Bad |
|---|---|---|---|
| **A. Doors for every act** | Each act is a corridor of door stops, as today. | Cheapest; everything built and tuned keeps working. | Economy tuned on doors may not carry over to the real map. |
| **B. Doors with a twist per act** | Act 2 has longer corridors, act 3 more elite doors or doors that hide their contents. | Acts feel different with little work. | Still doors; the same transfer problem as A. |
| **C. Build "twelve hours" now** | Each act is one "day": nodes cost hours, and the boss strikes at midnight. | The economy is tuned on the real structure from the start. | The biggest build; the page needs a new map screen. |
| **D. Doors on the page, "twelve hours" in the simulator** | The playtest keeps doors; the simulator gets the hours map to compare income, HP and route choices. | Tests the real map's economy without the page work; easy to switch later. | Two maps to maintain for a while. |

**Recommendation:** **A now, D next.** Acts are mostly about difficulty and economy, which doors measure well enough to start. Once acts work, adding the hours map to the simulator (D) shows how much the economy shifts before committing to it on the page.

**Simulator check:** cogs earned, fights taken and HP at each boss on doors versus the hours map.

---

## Recommended package

- **Difficulty:** a rising curve (act 1 ~90%, act 3 ~55%), with whole-run targets careless ~10%, casual ~35%, expert ~70%.
- **Between acts:** heal half the missing HP (or a full heal plus an overhaul choice).
- **Content:** themed districts with bosses split by act. Start with "veteran" placeholder enemies so tuning can begin before new enemies are designed.
- **Deck growth:** no new rule until the simulator measures dilution; cheaper thinning if it matters.
- **Machine upgrades:** a pool of about 8 with 3 slots.
- **Map:** doors for now; the hours map in the simulator next.
- **Prices:** set last, from measured income across all three acts.

---

## Decisions (designer, 2026-10-06)

1. **Difficulty targets:** A (rising curve) checked with D (skill targets). Starting numbers: casual act 1 ~90%, act 2 ~75%, act 3 ~55% (whole run ~35%); whole run careless ~10%, expert ~70%. The exact numbers can change.
2. **Between acts:** B, heal half the missing HP, plus an **exclusive boss reward**. Later, ascension-style difficulty levels may change what carries over.
3. **New content:** A (themed districts) for the final game. For testing, B (veteran placeholder enemies). D for bosses (split by act), with more bosses added later.
4. **Deck growth:** A (no new rule), unless the simulator finds a problem.
5. **Machine upgrades:** A (a bigger pool), plus levels (B) bought in the Workshop. New upgrades come **only from bosses and the start of the run** (choose 1 of n; n open), so a run gets few.
6. **Map:** C ("twelve hours to midnight") is the final map. For now acts use door choices (A), and the hours map comes to the simulator next (D).

**Elites (same decision round):** elites no longer give machine upgrades. They give rarer attachments and parts instead; their risk and return get re-tuned, and new rare content is added where needed.

### What was built (v18)
- **3 acts.** Bosses by act: act 1 Clock Tower or Pendulum, act 2 Furnace or Dismantler, act 3 Iron Colossus. All three are rolled and shown at the start.
- **Veterans** in acts 2 and 3: the act-1 normal enemies and elites at act strength (×1.3, ×1.5; tuned in v18) with +1 / +2 armor. Bosses have their own act strength table (same values for now). Enemies grow 20% within each act.
- **Between acts:** the boss's exclusive reward is 1 of 3 machine upgrades you don't have; then half the missing HP heals.
- **Machine upgrades:** a pool of 7 with levels: Flywheel (2 levels), Heat Housing (2), Extra Hands (2), Bigger Gear (1), Reinforced Frame (+8 max HP, 3), Wide Hopper (+1 part offered, 2) and the new **Cooling Fins** (1 Heat drains each turn, 2). Start: choose 1 of 3. Workshops sell level-ups only (placeholder prices 90 / 130).
- **Rarity across acts:** part reward weights common/uncommon/rare go 5/4/1, 3/4/2, 2/4/3.
- **Elite loot:** a part from the uncommon/rare tiers with rares twice as likely, and 1 of 3 uncommon/rare attachments. No machine upgrades.
- **New rare content:** **Overdrive** (attachment: damage and Block +75%), **Kickback** (attachment: after it triggers, the next 2 parts that would come up this turn trigger too, without turning the gear) and **Boiler** (part: 5 damage, +2 per point of Heat, +1 Heat). The **Hammer** (rare) becomes 12 damage, +1 Heat (was 10, +3). Measured values are in AI-Playtesting-Roadmap.md, Results v18.
- **Elite risk:** elites are at 105% strength (was 90%), so they cost about 26 HP; fighting them when healthy still pays, hunting them when hurt costs runs.

### What was built (v19)
- **Expert run planning:** the expert forecasts fight costs and keeps enough HP for the act's boss (`sim/clockwork/planner.py`). The expert clears 73% (target ~70%).
- **Hours map in the simulator** (decision 6, step D): `Run(map="hours")`, rules in Run-Design.md. With today's enemies it is much harder than doors (casual 9–15% vs 38%), mainly from fewer rests; results and options are in AI-Playtesting-Roadmap.md, Results v19.

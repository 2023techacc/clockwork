# Clockwork — AI Playtesting Roadmap

Four agent tiers, each meant to be a little smarter than the last, run against the same headless simulator and the same fixed encounter(s). The point isn't just automated playtesting — the *shape* of the improvement curve across tiers is itself a balance signal. A well-balanced fight should show smooth, explainable gains as agents get smarter. A sudden jump at any one tier usually means that tier found something qualitatively different (an exploit, a broken loop, a design assumption that doesn't hold under real pressure) rather than just "playing better." Watch for the jump, not just the final numbers.

Prerequisite for all four: a rules-accurate headless simulator (trigger order, Heat curve, reshuffle curve, Mirror/Coupler restrictions, etc. — see Rules-Decisions.md for the current test-baseline ruleset). Building that is the bulk of the work; each agent tier below is cheap by comparison.


**Simulator:** `sim/` (Python, standard library only). Rules defaults: "Simulator defaults v1" in Rules-Decisions.md. See `sim/README.md`.

---

## Experiment setup v1

Tunable starting numbers so every tier runs the same experiment.

**Test decks** (starter bag + 4 parts, roughly a deck a few fights into a run):

| Deck | Contents |
|---|---|
| starter | 4 Striker, 3 Plate, 1 Spring |
| spring_chain | starter + 2 Spring, 1 Coolant, 1 Hammer |
| copy_loop | starter + 2 Coupler, 2 Mirror |
| big_hit | starter + 2 Hammer, 2 Amplifier |
| sustain | starter + 2 Coolant, 1 Coupler, 1 Spring |
| utility | starter + 2 Loader, 2 Magnet |

**Test enemies** (v2: retuned by `clockwork.tune` until greedy wins about 60–70% averaged over the six decks; v1 values in brackets):

| Enemy | HP | Script | Tests |
|---|---|---|---|
| dummy | 82 [60] | Attack 11 [8] every turn (§8b baseline) | floor |
| spiker | 89 [70] | Attack 5, 5, 23 [4, 4, 18], repeat | Block timing |
| enrager | 81 [75] | Attack 4, +2 every turn | burst / race |
| saboteur | 91 [65] | Attack 11 → Jam 1 part 2 turns + Attack 8 → Wind Back + Attack 11 → Unscrew + Attack 8, repeat [8/6/8/6] | machine attacks |
| clock_tower | 54 [50] | Attack 6, 12 total cranks in the fight | each crank counts |

**Runs:** 1000 fights per (deck, enemy, agent) for Random and Greedy, and 200 for MCTS. Fight *i* uses seed *i* for every agent, so tiers face identical queues. Report win rate with a 95% Wilson interval.

**Metrics per fight:** win/loss, turns, HP left, total damage, best single-turn damage, most triggers in one turn, Overheats, Heat at each turn end, recycles, and damage taken.

**Flags:**
- **Burst:** "normal" turn damage is 18 (the best starter turn: 3 Striker triggers), so any turn of 54+ damage within the first 5 turns is a 3×-normal combo (§8b test plan).
- **Would-hit-cap:** turns with more than 8 triggers (§8b #2) and turns where one part triggered more than twice (§8b #1). These are tracked while both rules are on hold, to show how often they would have mattered.
- **Runaway:** a turn reaching 200 triggers is stopped by the simulator and flagged. Any runaway is an unbounded loop.
- **Timeout:** a fight still going at turn 40 counts as a loss.

**Loop finder** (before MCTS): every 6-slot layout that can be built from each test deck's parts, starting at Heat 0 and Heat 5, with 2 Crank Power. Report the top 20 layouts by triggers and by damage in a single turn.

**MCTS:** 100 / 300 / 1000 / 3000 rollouts per decision, 8 sampled worlds (determinizations) per decision. If results still climb at 3000, search deeper before running Stage 3.

**Loop finder** and **greedy** are built (`python -m clockwork.loopfinder`, `python -m clockwork.experiment`). Results below.

---

## Results v1 (Simulator defaults v1, v1 enemies)

**Win rate, 1000 fights per cell** (random → greedy):

| Deck | dummy | spiker | enrager | saboteur | clock_tower |
|---|---|---|---|---|---|
| starter | 23% → 100% | 2% → 100% | 0% → 51% | 12% → 100% | 0% → 31% |
| spring_chain | 22% → 100% | 6% → 100% | 2% → 100% | 14% → 100% | 6% → 100% |
| copy_loop | 12% → 100% | 2% → 100% | 0% → 80% | 5% → 100% | 2% → 91% |
| big_hit | 55% → 100% | 30% → 100% | 9% → 100% | 42% → 100% | 26% → 100% |
| sustain | 6% → 100% | 0% → 100% | 0% → 84% | 2% → 100% | 0% → 66% |
| utility | 2% → 100% | 0% → 100% | 0% → 41% | 1% → 100% | 0% → 36% |

**Loop finder** (every layout of each deck, best single turn, 2 Crank Power):

| Deck | Most triggers (Heat 0 / 5) | Most damage (Heat 0 / 5) |
|---|---|---|
| starter | 6 / 4 | 18 / 18 |
| spring_chain | 7 / 5 | 36 / 36 |
| copy_loop | 8 / 5 | 30 / 24 |
| big_hit | 6 / 4 | **66** / **60** |
| sustain | **12** / **11** (0 damage) | 30 / 24 |
| utility | 6 / 4 | 18 / 18 |

**Reading:**
- **Base difficulty is too low.** Greedy wins nearly every fight against dummy, spiker and saboteur with every deck. That is the Stage 1 red flag ("greedy trivially wins"). Only enrager and clock_tower separate the decks. Random wins 23% with the starter deck against dummy, which is the Stage 0 red flag too.
- **No cheap infinite loops.** Heat caps every layout at about 12 triggers in a turn, and no fight hit the runaway cap. The current brakes (Heat, Spring curve, the no-copy-loop rule #4) hold for these decks without §8b #1/#2.
- **The back-and-forth crank is the dominant technique.** Crank forward onto a part, back, forward again. A Spring between two Strikers fires on every crank, because Spring Heat resets with each chain. Greedy did this in about 6,300 of its 30,000 fights, mostly with copy_loop and sustain: some part triggered more than twice in a turn, which §8b #1 would have stopped.
- **big_hit breaks the 3×-normal guideline.** Two Hammers, each next to an Amplifier, alternated with back-and-forth cranks do 66 damage in one turn (normal is 18). Random play wins 55% with that deck.
- **Coolant loops trigger a lot but do nothing.** sustain's 12-trigger turns are Springs, Coupler and Coolants cycling with 0 damage.

---

## Stage 0 — Random

**What it is:** picks a uniformly random legal move each decision (which slot to install into, whether to crank extra, etc.). No evaluation of outcomes at all.

**Why it's worth having:** establishes the floor. Clockwork is designed around removing hidden-info luck (fully knowable machine, transparent queue) — which means, unlike a lot of card games, random play *shouldn't* get lucky wins very often. If it does, that's informative on its own.

**Good sign:** low, consistent win rate against the baseline enemy; low variance (it loses the same boring way most of the time, not "sometimes stumbles into a great line").

**Red flag:** random play wins at a meaningfully non-trivial rate, or wins with high variance. Either means base numbers are carrying fights without any actual engine-building — the floor is too high and there's not much room left to reward planning.

---

## Stage 1 — Greedy / heuristic

**What it is:** one-step lookahead. Score each legal move with a hand-written heuristic (expected damage/Block this turn, weighted against Heat risk, etc.) and take the best-scoring option. No search beyond the immediate consequence.

**Why it's worth having:** cheap way to find "obviously good" lines and stumble into unintended exploits the same way a careless human playtester would — often enough to catch a broken interaction without needing real search.

**Good sign:** a clear, moderate jump over random (proves near-term decisions are evaluable and matter) but it still loses to a well-tuned fight (proves the game needs more than turn-by-turn value-grabbing — there's real depth past "biggest number now").

**Red flag:** greedy already near-optimal, matching what smarter tiers achieve later — suggests the game doesn't actually reward planning beyond immediate value, which undercuts the whole timing-puzzle pitch. Or: greedy trivially wins every fight — base difficulty is too low.

---

## Stage 2 — Determinized MCTS

**What it is:** for each decision, sample the currently-hidden information (unseen queue tail, reshuffle order) into one concrete world, run standard MCTS rollouts inside that sampled world, repeat with fresh samples, aggregate. This gets the practical benefit of full Information-Set MCTS without its bookkeeping — appropriate here because the hidden information is environment RNG, not an adversarial hidden state (enemies are scripted, not adaptive).

**Why it's worth having:** this is the main tool for the actual question we've been reasoning about by hand — how much restraint the loop-brakes (Heat curve, reshuffle-Heat, no-copy-loop rules) actually need. A search-based agent will find the best multi-turn plan it can within its simulation budget, so it's the right tool to answer "does a cheap loop survive under real optimization pressure" and "does a hard, well-built loop still require real investment to sustain."

**Good sign:** a clear jump over greedy specifically in scenarios requiring delayed payoff or setup (holding a part near the top for a few turns, timing a chain around Heat headroom) — this validates that planning depth is actually being rewarded, not just found by accident.

**Red flag:** MCTS reliably finds a way to make Heat irrelevant or triggers effectively unbounded using only a handful of common parts — concrete evidence the current loop-brake stack (the §8b subset in the test baseline, plus the reshuffle curve) is still too permissive and needs another pass before content design continues. Conversely, if MCTS only ever finds sustainable "infinites" that cost heavy setup and dedicated Heat-mitigation parts, that's evidence the "cheap loops blocked, hard loops allowed" goal is actually working.

**Effort:** small-to-moderate — branching factor and horizon per fight are both small, this is a weekend-scale build once the simulator exists.

---

## Stage 3 — RL / DL self-play

**What it is:** train a policy (optionally + value) network via self-play against the fixed enemy scripts — PPO/DQN-scale, nothing requiring serious compute given the state space here. Learn from many simulated fights rather than searching fresh at every decision.

**Why it's worth having:** can surface non-obvious strategies a bounded per-move search budget might under-explore, and once trained it's fast at decision time (useful for running thousands of fights quickly, or sitting inside a live tuning loop).

**Caveat:** expensive to retrain every time a rule or number changes — a poor fit for right now, while the ruleset is still shifting weekly. Best used once the design is closer to settled, as a confirmation/scale tool rather than an exploration tool.

**Good sign:** matches or slightly exceeds MCTS's ceiling, and reaches it faster at inference time — confirms the ceiling MCTS found is a real property of the game, not an artifact of that particular search.

**Red flag:** RL finds a substantially higher ceiling than MCTS ever reached. Two possible causes worth distinguishing: MCTS's simulation budget in Stage 2 was too shallow (fixable — just search deeper), or there's a strategy so deep/counterintuitive that even directed search missed it. The second case is itself a design concern — an optimal line that's effectively undiscoverable by anyone (human or search) doesn't add real play depth, it's just a landmine. If RL surfaces one, that's a case for simplifying or removing that interaction rather than leaving it in as "hidden depth."

---

## Reading the overall curve

Random → Greedy → MCTS → RL should each step up by a comparable, explainable amount. Save the specific numbers each tier produces (win rate, avg damage/turn, avg Heat at fight end, turns survived) so the *shape* of the curve is visible, not just each tier's final score — the shape is what tells you whether the game has real, learnable depth or a single dominant line that any sufficiently careful search finds immediately.

---

## Results v2 (v2 enemies, MCTS added)

**MCTS setup:** determinized MCTS over whole-turn plans (`clockwork/agents/mcts_agent.py`). It samples 8 worlds per decision, reshuffling the unseen queue and reseeding random events. In each world it grows a tree whose moves are complete turn plans, added in greedy-heuristic order (progressive widening) and picked with UCB1. Leaves are valued by playing the fight out with a fast sampled-greedy policy, and root visit counts are summed across worlds. It never sees hidden information. 200 simulations per decision take about 1.3 s per fight.

**Win rate** (random / greedy at 1000 fights per cell → MCTS@200 at 100 fights per cell):

| Deck | dummy | spiker | enrager | saboteur | clock_tower |
|---|---|---|---|---|---|
| starter | 0 / 40 → 90% | 0 / 49 → 99% | 0 / 16 → 78% | 0 / 29 → 92% | 0 / 30 → 99% |
| spring_chain | 0 / 97 → 100% | 0 / 96 → 100% | 0 / 100 → 100% | 0 / 98 → 100% | 4 / 98 → 100% |
| copy_loop | 0 / 62 → 98% | 0 / 64 → 91% | 0 / 59 → 98% | 0 / 34 → 85% | 2 / 90 → 100% |
| big_hit | 2 / 100 → 100% | 2 / 100 → 100% | 7 / 100 → 100% | 2 / 100 → 100% | 23 / 100 → 100% |
| sustain | 0 / 80 → 98% | 0 / 75 → 97% | 0 / 73 → 100% | 0 / 73 → 96% | 0 / 64 → 97% |
| utility | 0 / 16 → 77% | 0 / 29 → 85% | 0 / 15 → 75% | 0 / 15 → 72% | 0 / 34 → 92% |

**MCTS budget sweep** (50 fights per cell):

| Cell | 100 | 300 | 1000 | 3000 |
|---|---|---|---|---|
| starter vs enrager | 80% | 86% | 100% | 100% |
| starter vs saboteur | 88% | 96% | 98% | 100% |
| utility vs enrager | 58% | 62% | 84% | 90% |
| utility vs saboteur | 50% | 70% | 82% | 94% |

**Behaviour** (averages over all v2 fights):

| Agent | Overheats | Heat at end | Damage taken | HP left | Fights with a part triggered >2× in a turn |
|---|---|---|---|---|---|
| random | 0.65 | 3.3 | 52.8 | 2.2 | 7% |
| greedy | 1.08 | 5.3 | 40.1 | 14.9 | 24% |
| MCTS@200 | 0.85 | 7.9 | 34.9 | 20.1 | 25% |

**Reading:**
- **The curve is healthy in shape:** random is about 0%, greedy about 60%, MCTS about 95%. Every step is a clear, explainable gain, and no tier finds a qualitatively different exploit. MCTS's edge is Heat management: it runs closer to the limit while overheating less, and it takes less damage. Turns to win are about the same, so it isn't finding a faster kill.
- **Planning is rewarded heavily**, which is the timing-puzzle pitch working. The jump from greedy to MCTS is largest with the starter deck (40% → 90% against dummy, 30% → 99% against clock_tower), where careful placement is the only lever.
- **Difficulty depends on who it's calibrated against.** Tuned to greedy, the enemies are close to trivial for a strong planner. Calibrate against human playtests (or against MCTS at a low budget, as a stand-in for a casual player) before using these numbers for content.
- **The MCTS ceiling isn't reached for harder cells.** utility-deck fights still climb at 3000 simulations, so by the roadmap's own rule, search deeper before trusting Stage 3 comparisons. Starter-deck fights saturate around 1000.
- **Decks are badly unbalanced.** big_hit and spring_chain win nearly everything even for greedy. utility (Loader/Magnet) is the weakest: those parts cost triggers and Heat without dealing damage or Block.
- **Back-and-forth cranking is used equally by greedy and MCTS** (about 25% of fights), so a planner treats it as a real technique, not a greedy artifact. Whether §8b #1 or a backward-crank cost should rein it in is still a design call.
- **Still no loops:** no runaway turns, and at most 7 triggers in a turn for greedy and MCTS.

---

## Results v3 (crank direction locked per turn, enemies tuned to MCTS@50)

**Changes since v2:** the crank direction is locked per turn (no back-and-forth cranking). Enemies are retuned so that MCTS with 50 simulations per decision, a stand-in for a casual player, wins about 60–67% averaged over the six test decks: dummy 82 HP / attack 11, spiker 90 HP / 5-5-23, enrager 85 HP / 4 +2 per turn, saboteur 91 HP, clock_tower 57 HP. The lock alone dropped greedy's starter-deck win rate against dummy from 40% to 10%. It also cut big_hit's best single turn from 66 to 52 damage, under the 3×-normal line of 54.

**Can the strong decks be drafted?** A player forcing a deck from "pick 1 of 3 random parts" rewards (all 10 part types in the pool) completes it with these odds:

| Target | 4 picks | 6 | 8 | 12 |
|---|---|---|---|---|
| big_hit (2 Hammer, 2 Amp) | 4% | 23% | 46% | 80% |
| spring_chain (2 Spring, Coolant, Hammer) | 6% | 32% | 57% | 87% |
| copy_loop (2 Coupler, 2 Mirror) | 4% | 23% | 47% | 80% |
| 1 Hammer + 1 Amp | 51% | 74% | 87% | 97% |

Without the three starter parts in the pool, big_hit reaches 79% by 8 picks. Parts stay on the gear once installed, so a bigger deck barely dilutes a key part. These decks will be common by mid-run.

**What one pick is worth** (win rate averaged over the 5 enemies; MCTS@50 at 100 fights per cell, greedy at 300):

| Deck | MCTS@50 | vs starter | greedy | Best turn (damage) |
|---|---|---|---|---|
| starter | 43% | — | 15% | 18 |
| + Hammer | **100%** | +56 | 92% | 27 |
| + Amplifier | 85% | +42 | 60% | 21 |
| + Coolant | 56% | +13 | 38% | 18 |
| + Coupler | 56% | +13 | 28% | 24 |
| + Mirror | 41% | −2 | 13% | 18 |
| + Loader | 36% | −7 | 14% | 18 |
| + Spring | 33% | −10 | 14% | 18 |
| + Magnet | 30% | −13 | 13% | 18 |
| + Hammer + Amp | 100% | +57 | 97% | 34 |
| + 2 Hammer | 100% | +57 | 99% | 36 |
| + Hammer + Coolant | 98% | +55 | 90% | 27 |
| big_hit | 100% | +57 | 99% | 52 |
| spring_chain | 96% | +52 | 83% | 27 |

**Reading:**
- **A single Hammer decides the fight.** One Hammer takes the casual stand-in from 43% to 100% against every enemy, and greedy from 15% to 92%. It is not a combo problem: the limit that binds is triggers per turn (about 3 from Crank Power), not Heat, so damage per trigger is what counts. 15 damage for 3 Heat beats a Striker's 6 for 1. The "big numbers on slow parts" guideline (§8b #5) isn't met, because Hammer isn't slow.
- **Amplifier is the second strongest single pick** (+42), even with nothing big to amplify.
- **Four parts make the deck worse than taking nothing:** Mirror, Loader, Magnet and Spring all score at or below the starter deck. A pick-1-of-3 reward should never be a trap, so they need buffs or a skip option. Spring is negative because its extra Heat costs more than the free crank gains now that cranks can't go back and forth.
- **Full archetypes add almost nothing over their core:** big_hit and spring_chain are no better than "starter + Hammer". The archetype identity isn't doing work yet.
- **Next balance step:** sweep Hammer's damage and Heat (and/or give it a real set-up cost), then re-run these probes until no single part is worth more than about +20–25 points.

### Results v3b: Hammer sweep

"Starter + 1 Hammer" against the starter deck, MCTS@50, 100 fights per enemy across all 5 enemies (starter: 43%, 8.8 damage/turn). Win-rate points gained:

| Hammer damage | +2 Heat | +3 Heat | +4 Heat |
|---|---|---|---|
| 7 | +14 | +12 | +14 |
| 8 | +18 | +20 | +18 |
| 9 | +16 | +22 | **+26** |
| 10 | +31 | +12 | +38 |
| 11 | +48 | +23 | +40 |
| 12 | +49 | +31 | +46 |
| 15 (original) | +56 | | |

**Chosen: 9 damage, +4 Heat (+26).**

**Heat isn't monotonic.** A Hammer that costs more Heat can be stronger. Greedy shows the same thing at damage 10: 3 / 4 / 5 / 6 total Heat give 89% / 44% / 25% / 56% / 61% win against dummy (2–6 total Heat in order). The cause is the Overheat reset discarding Heat above 10. With a 6-Heat Hammer, the Hammer is the trigger that tips the machine over in 71% of Overheats, with 3.6 Heat discarded each time on average (0.4 for a 2-Heat Hammer). High-Heat parts get a hidden discount, so this sweep should be redone after the Heat rework.

---

## Results v4 (new parts and attachments; greedy heuristic fix; enemies v4)

**Agent fix first.** In the first v4 run, the Coil attachment (pure upside) made decks *lose more*, for greedy and MCTS alike. The greedy heuristic, which MCTS also uses to order moves and play rollouts, charged 1 point per Heat. That underpriced Heat, so the agents chased immediate damage into Overheats. Raising the weight to 2 fixed it: Coil became an upgrade, and MCTS@50 with the starter deck went from 30% to 85% against dummy. Every v3 number was measured with the weaker agent and is shifted. Enemies were retuned (v4): dummy 85 HP, spiker 91, enrager 87, saboteur 96 (attacks 12/8), clock_tower 55.

**What one pick is worth** (MCTS@50, 100 fights per enemy across all 5 enemies; starter 49%, 9.4 damage/turn):

| Deck | Win | vs starter | Damage/turn |
|---|---|---|---|
| + Primer | 98% | **+49** | 13.2 |
| + Assembly | 97% | **+48** | 12.4 |
| + Loader + Primer / + Loader + Assembly | 97% | +48 | 12.8 / 12.4 |
| + Feeder Loader + Primer | 97% | +48 | 12.9 |
| + Coupler | 90% | +41 | 11.1 |
| + Polish Mirror | 88% | +39 | 10.9 |
| + Amplifier | 87% | +38 | 10.5 |
| starter with its Spring Coiled | 83% | +34 | 10.2 |
| + Coil Spring | 66% | +17 | 9.7 |
| + Hammer (9 dmg, +4 Heat) | 65% | +16 | 9.8 |
| + Clamp Magnet + Slider | 58% | +9 | 10.0 |
| + Slider | 57% | +8 | 9.7 |
| + Coolant | 52% | +3 | 9.3 |
| + Mirror | 48% | −1 | 9.4 |
| + Magnet + Slider | 45% | −4 | 9.5 |
| + Clamp Magnet | 40% | −9 | 9.3 |
| + Loader | 39% | −10 | 9.1 |
| + Magnet | 37% | −12 | 9.1 |
| + Spring | 36% | −13 | 9.0 |

**Reading:**
- **Primer and Assembly are too strong and don't need their enabler.** A Loader adds nothing on top of them. Primer's 18 always lands, because every part is freshly installed on an empty gear. Assembly is about 10–12 damage for 1 Heat on a normal gear.
- **Coil works as an attachment should:** it turns the weakest part (Spring, −13) into one of the best (+34 when it upgrades the starter's own Spring).
- **Polish turns Mirror from −1 into +39.** Like Coil, it's a strong fix, probably too strong.
- **Magnet is still a trap.** It only pulls into empty slots, so Slider and Clamp rarely get to fire. Even the full Clamp Magnet + Slider set is only +9.
- **With the better agent, Coupler (+41) and Amplifier (+38) are now above Hammer (+16).** The Hammer value chosen in v3b was measured with the weaker agent and is now too low.
- **Next step:** a balance pass that sweeps each outlier (Primer, Assembly, Polish, Coil, Coupler, Amplifier, Hammer) into a band of about +10 to +25. Then design changes so the payoffs need their enabler, and so Magnet can pull into occupied slots.

---

## Results v5 (balance pass)

**Design changes:**
- Primer's bonus only lands if it triggers on the turn it was installed.
- Assembly counts parts installed this turn.
- Magnet pulls into occupied slots by swapping.

**Values chosen by the sweep** (`clockwork/balance.py`, MCTS@50, 100 fights per enemy, target about +18, band +10 to +25):

| Part | Was | Now |
|---|---|---|
| Primer | 4, 18 when fresh | 2, 8 when it triggers on its install turn |
| Assembly | 2 per occupied slot | 3 per part installed this turn |
| Coupler | +0 Heat | +2 Heat |
| Amplifier | +50% | +30% |
| Polish | +50% | +20% |
| Clamp | triggers every pulled part | triggers 1 pulled part |
| Hammer | 9 damage, +4 Heat | unchanged |
| Coil | 4 damage | unchanged (with MCTS@200, 3 → +6 and 4 → +14) |

**Validation** (all probes, final values; starter 50%):

| Deck | vs starter | | Deck | vs starter |
|---|---|---|---|---|
| Clamp Magnet + Slider | **+39** | | + Slider | +7 |
| starter with its Spring Coiled | **+34** | | + Assembly | +6 |
| + Primer | **+27** | | + Clamp Magnet | +5 |
| + Polish Mirror | +20 | | + Coolant | +3 |
| + Feeder Loader + Primer | +18 | | + Loader + Assembly | 0 |
| + Coupler | +17 | | + Mirror | −1 |
| + Coil Spring | +16 | | + Magnet + Slider | −2 |
| + Hammer | +15 | | + Loader | −11 |
| + Loader + Primer | +13 | | + Spring | −13 |
| + Amplifier | +13 | | + Magnet | −17 |

**Reading:**
- **Seven picks now sit in the band:** Polish, Coupler, Coil Spring, Hammer, Amplifier, and Loader + Primer with or without Feeder. The old +40–55 outliers are gone.
- **The win-rate scale is steep.** A part is either barely used (about +5) or, once it beats a plain Striker, built around (+30 or more). A one-point change often jumps over the whole band. At this difficulty, "+10 to +25" means "a little better than a Striker".
- **Payoffs still don't need their enablers.** Primer alone (+27) beats Loader + Primer (+13). Assembly alone (+6) beats Loader + Assembly (0). The enablers themselves are the problem: Loader (−11), Magnet (−17) and Spring (−13) cost a gear slot and a trigger without doing anything on their own, so pairing them drags the payoff down.
- **Clamp Magnet + Slider (+39) is the one remaining combo outlier.** The swap made Magnet reliable, and Slider's moved bonus then applies to almost every Clamp trigger.
- **Next:**
  - give the enablers some value of their own: for example, a Loader that loads two parts, a Magnet that deals a little damage, or a Spring with less Heat;
  - lower Slider's moved bonus, or have Clamp skip the moved bonus;
  - retune the enemies, since the main decks' strength changed;
  - re-run the tier comparison after the Heat rework.

---

## Results v6 (two-part Loader, Slider moved bonus 3, enemy HP ±3, enemies v6)

**Enemy HP jitter.** Without it, win rate falls in steps at multiples of 6 HP, because starter damage comes in chunks of 6. One HP (84 vs 85) decided whether the starter deck won 78% or 38% against dummy. Each fight now rolls enemy HP within ±3 of the base, like Slay the Spire's HP ranges, and greedy's win-rate curve becomes smooth (59/48/37/33/29/20/14% from 78 to 90 HP). This probably also caused much of the jumpiness in the v5 part sweeps. Enemies v6: dummy 82 HP, spiker 89 (5/5/22), enrager 82, saboteur 92, clock_tower 52.

**Validation** (MCTS@50, 100 fights per enemy across all 5 enemies; starter 71%):

| Deck | vs starter | | Deck | vs starter |
|---|---|---|---|---|
| starter with its Spring Coiled | +21 | | + Loader + Primer | +5 |
| + Primer | +17 | | + Assembly | +2 |
| + Polish Mirror | +15 | | + Slider | +2 |
| + Clamp Magnet + Slider | +13 | | + Coolant | −1 |
| + Coil Spring | +11 | | + Loader + Assembly | −6 |
| + Hammer | +9 | | + Mirror | −7 |
| + Feeder Loader + Primer | +8 | | + Magnet + Slider | −8 |
| + Coupler | +8 | | + Loader (two loads) | −9 |
| + Amplifier | +6 | | + Spring | −14 |
| + Clamp Magnet | +6 | | + Magnet | −15 |

**Reading:**
- **The scale is compressed.** The six main decks got weaker, so the retuned enemies are easier and the starter deck now wins 71%. Only 29 points of headroom remain, so these numbers aren't comparable to v5's; read the order, not the size. No pick is an outlier any more: the top is +21.
- **Clamp Magnet + Slider came down from +39 to +13.**
- **The second load barely helps the Loader** (−11 → −9), and payoffs still do better alone than with it. The Loader's problem isn't how much it loads: the gear fills by itself within about 3 turns of normal installs, so filling empty slots only matters early in a fight. Loader decks deal more damage per turn (10.1 vs 9.5 with Assembly) but lose more, because the Loader and the parts it loads crowd out Plates.
- **The plain starter (71%) now beats spring_chain (about 57%) and utility (about 42%) in the tuning run.** Those decks carry the parts that test negative (Spring, Loader, Magnet).

---

## Results v7 (full tier comparison on the current rules)

**Rules since v2:**
- crank direction locked per turn;
- Hammer 9 damage, +4 Heat;
- balance pass v5;
- Loader: two loads, and with the gear full one load replaces the part opposite it;
- Magnet: swaps, and gains 6 Block per pulled part;
- enemy HP ±3 per fight; enemies v6;
- greedy heuristic Heat weight 2.

**Win rate** (random / greedy at 1000 fights per cell → MCTS@200 at 100 fights per cell):

| Deck | dummy | spiker | enrager | saboteur | clock_tower |
|---|---|---|---|---|---|
| starter | 0 / 35 → 93% | 0 / 36 → 99% | 0 / 22 → 93% | 0 / 26 → 93% | 0 / 25 → 97% |
| spring_chain | 0 / 33 → 85% | 0 / 32 → 85% | 0 / 30 → 79% | 0 / 20 → 82% | 0 / 26 → 86% |
| copy_loop | 0 / 41 → 89% | 0 / 49 → 92% | 0 / 40 → 91% | 0 / 34 → 85% | 0 / 56 → 99% |
| big_hit | 0 / 56 → 100% | 0 / 57 → 96% | 0 / 63 → 97% | 0 / 43 → 95% | 4 / 70 → 100% |
| sustain | 0 / 40 → 89% | 0 / 44 → 88% | 0 / 30 → 85% | 0 / 29 → 85% | 0 / 22 → 72% |
| utility | 0 / 98 → 100% | 0 / 79 → 99% | 0 / 28 → 79% | 0 / 98 → 100% | 0 / 9 → 64% |

**Overall:**

| Agent | Win | Overheats per fight | Damage taken | HP left |
|---|---|---|---|---|
| random | 0.1% | 0.61 | 54.6 | 0.4 |
| greedy | 42.4% | 1.60 | 46.6 | 8.4 |
| MCTS@200 | 89.9% | 1.43 | 41.2 | 13.8 |

**MCTS budget sweep** (50 fights per cell; v2 values in brackets):

| Cell | 100 | 300 | 1000 | 3000 |
|---|---|---|---|---|
| starter vs enrager | 76% | 88% | 98% | 100% [100%] |
| starter vs saboteur | 80% | 92% | 96% | 100% [100%] |
| utility vs enrager | 70% | 90% | 94% | 96% [90%] |
| utility vs saboteur | 100% | 100% | 100% | 100% [94%] |

**Reading:**
- **The tier curve is healthy:** 0% → 42% → 90%. Both steps are large and comparable, and none comes from a new exploit: no burst turns, no runaways, at most 8 triggers in a turn. The direction lock removed back-and-forth cranking; only 27 greedy fights had a part trigger more than twice in a turn, against about 7,300 in v2.
- **The MCTS ceiling is reached now.** Every cell saturates by 1000–3000 simulations, while in v2 the utility deck was still climbing at 3000. By the roadmap's rule, Stage 3 (RL) would have a stable ceiling to compare against, though it is still best left until the rules settle.
- **Planning is worth more than ever.** The greedy → MCTS step (+48 points) is now larger than random → greedy (+42). The puzzle is real, but a casual player will find it hard: the enemies are tuned so MCTS@50 wins about 65%, and greedy only manages 42%.
- **The utility deck is now polarized.** Greedy wins 98% against dummy and saboteur but 9% against clock_tower. Two Magnets that always swap and gain 6 Block per pull make a defensive engine that trivializes enemies with steady attacks, but it spends cranks the clock_tower doesn't allow. One Magnet probed at +10; two together are much stronger than that suggests.
- **spring_chain is now the weakest deck** for MCTS (79–86%). It carries three uncoiled Springs, and Spring is still the most negative single pick (−14).
- **Still open:**
  - the Heat rework: overflow is still forgiven, about 0.85 Heat per fight;
  - Spring and Mirror on their own;
  - whether two Magnets need a cap on their Block;
  - calibrating difficulty against human playtests.

---

## Results v8 (Clock Tower v2, and HP left after winning)

**Clock Tower v2 (chime).** Human playtesting found the 12-crank limit made Block useless: every Plate trigger spent one of the 12 cranks, so the fight was a pure damage race only a near-perfect planner could win (greedy 25% vs MCTS@200 97% with the starter deck). The new tower has no regular attack. On every 4th crank of the fight (Spring cranks count) it strikes at once, after the arriving part's chain, hitting your current Block.

Settings tested (all 6 decks):

| Setting | MCTS@50 | greedy | HP left on win (MCTS@50) | Strike damage blocked |
|---|---|---|---|---|
| 52 HP, every 4 × 15 | 100% | 100% | 32 | 25% |
| 90 HP, every 4 × 18 | 79% | 51% | 7.3 | 21% |
| 98 HP, every 4 × 18 | 55% | 32% | 6.6 | 20% |
| **115 HP, every 4 × 15 (chosen)** | **66%** | **41%** | **9.5** | **30%** |

At 52 HP, better agents block more of the strike damage (greedy 22%, MCTS@50 25%, MCTS@200 38%), so timing Block is now a real skill. 15-damage strikes keep the most blocking in play, because a Plate's 6 covers more of them. Strike damage near 22 sits on a survival breakpoint: three unblocked strikes kill a 55-HP player, and 22 → 23 dropped the casual win rate from 66% to 33%. The utility deck flips from worst (9% against the old tower) to best (98–100%), because its Magnet Block engine counters strikes. Per deck at the chosen setting (MCTS@50): starter 53%, spring_chain 43%, copy_loop 91%, big_hit 96%, sustain 14%, utility 100%.

**HP left after winning is very low everywhere.** In the v7 run, wins ended with these averages (minimum in brackets), out of 55 HP:

| Agent | dummy | spiker | enrager | saboteur |
|---|---|---|---|---|
| greedy | 8.5 (1) | 6.8 (1) | 7.2 (1) | 9.8 (1) |
| MCTS@200 | 8.7 (1) | 8.4 (1) | 10.5 (1) | 8.8 (1) |

64% of MCTS@200's wins end under 15 HP. The enemies were tuned for win rate only, so every fight became a close race. If HP carries over between fights, as in Slay the Spire, a run is unwinnable. Normal fights should cost something like 10–20 HP for a decent player. Fix: tune two numbers per enemy, win rate and HP lost on a win, by lowering attacks and raising enemy HP (longer fights that hurt less). The tuner currently scales both together; it needs separate knobs.

---

## Results v9 (HP carries over between fights)

**Rule:** HP carries over between fights, and a small heal follows each win (placeholder: 10 HP, `heal_between_fights`). The previous enemies were tuned on win rate only. Every fight was a close race, wins ended at about 9/55 HP, and a casual player (MCTS@50) cleared the mini-run below 0% of the time with every deck, mostly dying by fight 3.

**Retune** (`clockwork.tune` now has `--knob attack/hp/both`, `--metric win/hp_lost` and `--start-hp`):
- **Normal enemies:** HP and attacks are scaled down together until a casual player loses about 15 HP per win. Scaling attacks alone also reached the target, but left enemies attacking for 1–2 across 8–9-turn fights. Shorter fights with real attacks play better.
- **Boss:** tuned so a casual player arriving with 35 HP wins about 70%. Strike damage 12 vs 13 is a cliff (79% → 62%), so the strike stayed at 12 and HP was set between the measured points.

| Enemy | Before | Now | Casual: HP lost on a win |
|---|---|---|---|
| dummy | 82 HP, attack 11 | 55 HP, attack 7 | 13 |
| spiker | 89 HP, 5/5/22 | 58 HP, 3/3/14 | 15 |
| enrager | 82 HP, 4 +2/turn | 60 HP, 3 +1/turn | 12 |
| saboteur | 92 HP, 12/8 | 56 HP, 7/5 | 14 |
| clock_tower | 115 HP, strike 15 | 98 HP, strike 12 every 4 cranks | 24 (arriving with 35) |

At the boss setting, players block about 46% of strike damage.

**Mini-run** (`clockwork.campaign`: dummy → spiker → saboteur → enrager → clock_tower, 10 HP healed after each win). Run cleared, and HP on reaching the boss in brackets:

| Deck | greedy (100 runs) | MCTS@50 (60 runs) | MCTS@200 (20 runs) |
|---|---|---|---|
| starter | 13% (28) | 95% (45) | 100% (52) |
| spring_chain | 3% (25) | 50% (35) | 95% (43) |
| copy_loop | 26% (27) | 67% (34) | 85% (40) |
| big_hit | 33% (29) | 87% (39) | 100% (46) |
| sustain | 2% (25) | 45% (36) | 100% (47) |
| utility | 97% (41) | 100% (49) | 100% (53) |
| **average** | **29%** | **74%** | **97%** |

**Reading:**
- **Runs are survivable now, with a clear skill curve:** careless 29%, casual 74%, near-perfect 97%. Normal fights drain HP without killing, and the boss is the real test. Greedy reaches the boss about 90% of the time but arrives with about 27 HP and usually loses.
- **Casual players arrive at the boss with more HP than the 35 tuned for** (34–49), since 10 healed per win offsets most of the 12–15 lost. If the boss should be harder in practice, lower the heal or raise normal-fight damage slightly.
- **The utility deck trivializes the boss:** greedy clears 97%. Its Magnet Block engine blocks most strikes. Worth watching if Magnet decks become common in real runs.
- **Normal fights almost never kill now** (casual reaches the boss 98–100% of the time). That suits a first district, but later districts or elites will need real risk.

---

## Results v10 (run prototype: door map, cogs, Workshop, rest, attachments, elites)

**What's in** (Run-Design.md, "Decisions"; `clockwork/run_mode.py`, shared by the simulator and the playtest page):
- 9 stops of door choices, then the Clock Tower.
- Cogs looted per enemy: normal 12–16, elite 30–36, boss 60, each ±10%. Part rewards can be scrapped for 10 cogs.
- Rest sites: heal 15, or take 1 of 2 common attachments.
- Workshop: 3 parts, 2 attachments, sometimes a machine upgrade; remove, repair, and sell unattached attachments.
- Attachments have a rarity: common, uncommon or rare, with new generic ones (Sharpened, Counterweight, Bracing, Heat Sink, Governor, Echo). Up to 2 per part, permanent once attached.
- Elites (machine attackers), tuned so a casual player loses about 25 HP per win:

| Elite | HP | Attack | Twist |
|---|---|---|---|
| Overclocker | 80 | 7/5 | +3 Heat to your machine every other turn |
| Rust Golem | 86 | 7 | Rusts the top part (−2 damage/Block for the fight) every other turn |
| Pickpocket | 84 | 7 | Unscrews a part every turn |
| Jammer Prime | 74 | 7 | Jams 2 parts every other turn |

**Difficulty.** With rewards, attachments, rest sites and repairs on top of enemies tuned for fixed decks, runs were far too easy: greedy cleared 90%, MCTS@50 100%. Removing the after-win heal entirely still left the casual player at 92%. Two changes:
- the after-win heal goes from 10 to 5 ("heal a bit");
- **enemies grow through the district:** HP and attacks are multiplied by 1 + 0.11 × stop/9, so the boss is 11% stronger than base. Tuned so MCTS@50 clears about 65%.

**Whole runs** (`clockwork.run_policy`: fights played by the agent; doors, rewards, rest and Workshop choices made by simple rules; starter deck):

| Player | Runs cleared | Reached the boss (HP) | Elites fought | Attachments | Cogs left at the end |
|---|---|---|---|---|---|
| greedy (60 runs) | 47% | 78% (37) | 0.6 | 0.9 | 60 |
| MCTS@50 (60 runs) | 67% | 95% (37) | 1.3 | 1.3 | 86 |
| MCTS@200 (20 runs) | 80% | 95% (36) | 1.4 | 1.6 | 90 |

**Reading:**
- **The boss is the main wall:** 17 of the 20 casual deaths and 19 of 31 careless deaths are to the Clock Tower. Normal fights and elites drain HP but rarely kill.
- **The skill curve is flatter than in single fights** (47% → 67% → 80%). Part of that is the simple rule-based route and shop choices, which every agent shares. A smarter run policy would widen the gap.
- **Money isn't a constraint:** runs end with 60–90 cogs unspent and no machine upgrades bought (110–130 cogs, and the rules buy attachments first). Either raise prices or the value of what's for sale, or add more ways to spend.
- **Attachments are rarer than intended** (about 1.3 per run against a 2–4 target), because the rules skip elites below 70% HP. More attachment sources, or cheaper rest-site tinkering, would raise it.
- **Caveat:** every route, reward and Workshop decision here comes from fixed rules, so these numbers describe the content balance under one reasonable play style, not the best possible play.

## Results v11 (studies: attachments, machine upgrades, run styles, combo ceilings)

`python -m clockwork.studies attachments|machine|styles|combos` (casual player, MCTS@50). Single fights start at full HP against all 9 enemies (40 fights each, paired seeds) and almost always end in a win, so the measure is **HP kept per fight**. Run studies play 150 whole runs per variant on the same seeds; "+a/−b" counts runs the variant won that the base policy lost, and the reverse.

**What one attachment is worth** (HP kept per fight against the same deck without it; starter baseline 34.6):

| Attachment | Best host | HP kept | Weak or useless on |
|---|---|---|---|
| Sharpened | Plate | +3.6 (Striker +2.3) | Spring +0.3 |
| Counterweight | Plate | +4.1 | Striker +0.7 |
| Bracing | Striker | +0.3 | (only matters against a few enemies) |
| Heat Sink | Striker | +2.9 | Spring −0.1 |
| Coil | Spring | +0.7 | |
| Polish | Mirror | +2.3 | |
| Clamp | Magnet | +2.0 | |
| Feeder | Loader | +0.4 | |
| Governor | Hammer | +5.5 (Striker +2.9) | Spring −0.4 |
| Echo | Plate | +3.5 (Striker +3.2) | Spring +0.1, Hammer +1.7 |
| Sharpened + Echo | Striker | +6.6 | |
| Echo + Governor | Hammer | +12.6 | |

- **A single attachment is worth about 2–4 HP per fight.** Two on the same part stack better than either alone.
- **Dead attachments:** Bracing, Feeder, Coil, and anything on a Spring.
- Rare attachments (Governor, Echo) are not clearly better than common ones (Sharpened, Counterweight) unless paired.

**Machine upgrades:**

| Upgrade | Single fights (HP kept) | Runs started with it: cleared (base 69%) | Paired |
|---|---|---|---|
| Extra Hands | +0.6 | **84%** | +35/−12 |
| Heat Housing | +1.9 | **79%** | +28/−13 |
| Flywheel | +2.5 | 73% | +26/−20 |
| Bigger Gear | −0.7 | 67% | +20/−23 |

- Extra Hands and Heat Housing are strong in runs, mostly against the boss.
- **Bigger Gear is worthless:** 8 slots spread the same parts thinner.
- **Nobody can buy them:** even a policy that saves for machine upgrades bought 0.01 per run. Cogs arrive too slowly for 110–130 prices, and only half of Workshops stock one.

**Run styles** (base policy 69% cleared):

| Style | Cleared | Paired | Note |
|---|---|---|---|
| Avoid elites | **83%** | +31/−10 | 1.2 attachments instead of 2.1 |
| Seek elites (unless HP < 40%) | 43% | +9/−47 | |
| Rest: always heal | 69% | +3/−2 | |
| Rest: always tinker | 45% | +8/−43 | Reaches the boss with 24 HP instead of 36 |
| Never take parts (scrap) | 36% | +15/−64 | Part rewards matter a lot |
| Take the best part, always | 67% | +3/−5 | |
| Remove Strikers/Plates in Workshop | 69% | +1/−1 | Rarely affordable |
| Save for machine upgrades | 63% | +8/−16 | Never reaches the price |

**Where runs lose HP** (base policy):

| Node | Mean HP lost per fight | Deaths | Cogs |
|---|---|---|---|
| Normal fights | 12–14 | 9 in 659 fights | 12–16 |
| Elites | 26–27 | 2 in 175 fights | 30–36 (+ attachment) |
| Clock Tower | 25 | 36 in 139 fights | 60 |

**Combo ceilings** (loop finder, start Heat 0, every layout and crank plan; boss HP 98–109):

| Deck | Best single turn |
|---|---|
| big_hit / copy_loop / spring_chain (no attachments) | 28 / 24 / 21 |
| Echo+Sharpened Strikers | 38 |
| Echo Coupler + Hammers | 48 |
| Echo+Governor Hammer, Coupler, Mirror | 51 (ends at 9 Heat) |
| Coil, Polish, Heat Sink, Governor Spring combos | 24–35 |

- No degenerate combo: the 10-Heat cap bounds every chain, and the best turn is about half the boss's HP.
- **A plain Spring never adds a damaging trigger on a 6-slot gear:** its free crank replaces a crank you would have made. It only adds damage with Coil or Echo, which is why Spring measured slightly negative.

**Reading:**
- **Elites are a bad deal.** An elite costs about 13 HP more than a normal fight; its extra cogs and one attachment (worth 2–4 HP per later fight) don't pay that back. Rational players will skip them. Fix by making elites cheaper in HP (about −20% HP or attack) or richer: a choice of attachment *and* a part reward, more cogs, or a machine upgrade chance.
- **Resting to tinker is a trap:** 15 HP for a common attachment loses runs. Tinker should give more (an uncommon, or two commons), or cost less.
- **Machine upgrades are the strongest thing in the Workshop and can't be bought.** Suggested: prices 70–90 (Extra Hands highest), always stock one, and rework Bigger Gear (e.g. 7 slots plus +1 install, or "the gear's empty slots don't count for Spring cranks").
- **Weak attachments to buff or rework:** Bracing, Feeder, Coil, Spring-host attachments.
- **The boss remains the wall:** a quarter of the runs that reach it die there.

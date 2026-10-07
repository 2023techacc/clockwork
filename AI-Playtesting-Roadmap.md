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

## Results v12 (elites high risk/high return, tinkering, machine upgrades, attachment buffs)

**Changes** (designer decisions after v11):
- **Elites: high risk, high return.** Risk was roughly right; return was too low: the extra cogs had nothing worth buying, and one attachment is worth only 2–4 HP per later fight. Tested reward and strength variants against avoiding elites (150 runs each):

| Elite variant | Fight elites at HP ≥ 70% | At HP ≥ 40% | (avoid elites: 81%) |
|---|---|---|---|
| v11 rewards | 70% | 49% | |
| Better part + 1 of 3 attachments ("rich") | 77% | 52% | |
| rich + 20 cogs | 79% | 57% | |
| rich + 50% machine salvage | 79% | 64% | |
| rich + 100% machine salvage | 81% | 72% | |
| rich, elites at 90% | 79% | 73% | |
| rich, elites at 85% | 81% | 87% (no risk left) | |
| **rich + 50% salvage, elites at 90% (chosen)** | **80%** | **80%** | |

  Chosen: elites at 90% strength; loot is a part from the uncommon/rare tiers, 1 of 3 uncommon/rare attachments (rares 3× as likely), and a 50% chance to salvage a free machine upgrade.
- **Rest sites:** tinkering gives both offered common attachments.
- **Machine upgrades:** every Workshop stocks one; Flywheel 70, Bigger Gear 75, Heat Housing 85, Extra Hands 90. **Bigger Gear reworked** to 8 slots *and* +1 Crank Power (8 slots alone was useless). Candidates tested, runs started with each (no upgrade 66%): Extra Hands 82%, Heat Housing 81%, Flywheel 73%, old Bigger Gear 68%, new Bigger Gear 74%, Reinforced Frame (+10 max HP) 85%, Wide Hopper (4 parts offered) 70%. Reinforced Frame is kept as a candidate.
- **Attachments** (HP kept per fight; target 2.5–4):
  - Bracing: +1 damage and +1 Block on top of its immunity → +4.1 on a Striker, +5.8 on a Plate (was +0.3). +3 Block alone: +2.6/+4.4; +2/+2: +4.0/+7.3.
  - Coil: 8 damage → +3.2 (4: +0.7, 6: +1.7, 10: +5.0).
  - Feeder reworked: loads 1 more part and every loaded part triggers right away → +2.5. Extra loads alone did nothing (+0.3, −0.1); triggering 1 or 2 loaded parts gave +0.7 and +1.7. The Loader itself remains a weak host.
- **Run policy:** buys the machine upgrade first; picks the attachment worth most to the deck and puts it on its best host (MOD_VALUE/MOD_HOSTS from the studies).
- **Measurement fix:** v11's "cogs left" included the boss's loot, which can't be spent. Runs actually reached the boss with ~20–40 unspent cogs, not 60–90.
- **Difficulty:** district growth 0.11 → **0.20** (casual 80% → 72%). 0.21 rounds the boss chime from 14 up to 15 damage and drops the casual player to 59%.

**Whole runs** (starter deck):

| Player | Runs cleared | v10 | Elites | Attachments | Machine upgrades |
|---|---|---|---|---|---|
| greedy (150) | 43% | 47% | 0.7 | 1.5 | 0.4 |
| MCTS@50 (150) | 72% | 67% | 1.1 | 2.1 | 0.9 |
| MCTS@200 (60) | 88% | 80% | 1.3 | 2.2 | 1.0 |

**Run styles** (MCTS@50, base policy 72%):

| Style | Cleared | v11 | Note |
|---|---|---|---|
| Avoid elites | 63% | 83% | Elites now pay when healthy |
| Seek elites (unless HP < 40%) | 67% | 43% | 22% die before the boss; survivors bring 1.8 machine upgrades |
| Rest: always heal | 72% | 69% | |
| Rest: always tinker | 69% | 45% | Now a real choice: 7 attachments, boss at 27 HP |
| Never take parts | 50% | 36% | |
| Remove basics / save for machine | 71% / 69% | 69% / 63% | |

**Where runs lose HP:** normal fights 12–15 HP, elites 21–25 (was 26–27), Clock Tower 26 with 34 deaths in 142 fights.

**Reading:**
- **Elites are now high risk, high return:** taking them when healthy is the best plan, hunting them aggressively is a gamble that can pay off, and skipping them costs 9 points.
- **Every rest choice and route style is now within a few points of the base,** except skipping parts. There's no single dominant strategy.
- **The skill curve is wider** (43% → 72% → 88%, was 47% → 67% → 80%).
- **Remaining weak spots:** the Loader as a part (and so Feeder), attachments on a Spring, and the boss still causing most deaths.

## Results v13 (database, planned machine upgrades, five bosses)

**Changes:**
- **Database.md:** every part, attachment, enemy, boss, machine upgrade and run number, generated from the simulator (`python sim/build_database.py`; a test fails when it's stale). Descriptions live in `clockwork/describe.py`, shared with the playtest page.
- **Machine upgrades are no longer random.** Every Workshop sells all the upgrades you don't have, so players can plan and save for one. Elite salvage stays a 50% gamble, but you choose 1 of 2.
- **Bosses:** a run's boss is picked at the start (or chosen on the page) and shown all run. Four new bosses join the Clock Tower, with two new mechanics: **armor** (every hit deals less) and **swing** (the boss forces the turn direction).

| Boss | HP | Pattern | Tests |
|---|---|---|---|
| Clock Tower | 98 | No attacks; strikes for 12 on every 4th crank | Doing more with fewer cranks |
| Furnace | 74 | +1 Heat & attack 6, +1 Heat & attack 6, +3 Heat & attack 9 | Heat management |
| Dismantler | 84 | Unscrew 2 parts & attack 6, then rust the top part & attack 8 | Rebuilding, Bracing |
| Iron Colossus | 68 | Attack 7 every turn; armor 3 | Big single hits |
| Pendulum | 83 | Attack 4, then 10; odd turns clockwise, even counter-clockwise | Layouts that work both ways |

**Tuning.** Tuning against fixed test decks from 36 HP (`clockwork.tune`) made the attacking bosses too hard in real runs (60–66% beaten vs the Clock Tower's 76%): run growth scales their attacks, while the Clock Tower barely attacks. New tool `clockwork.boss_tune` plays 300 runs to the boss door, keeps each run's state (deck, attachments, machine, HP), and tunes every boss against those same states. Attacks get rounded again when a run scales a boss, so attacks are fixed first and HP tuned last (`--knob hp`).

**Whole runs ending at each boss** (MCTS@50, 150 runs each; 139 reach the boss):

| Boss | Runs cleared | Beat the boss when reached |
|---|---|---|
| Clock Tower | 70% | 76% |
| Furnace | 71% | 76% |
| Dismantler | 73% | 78% |
| Iron Colossus | 65% | 71% |
| Pendulum | 71% | 77% |
| **Random boss (default)** | **67%** | |

**Which decks each boss punishes** (fixed test decks, 36 HP, base strength, 40 fights each):

| Boss | starter | spring_chain | copy_loop | big_hit | sustain | utility |
|---|---|---|---|---|---|---|
| Clock Tower | 72% | **45%** | 95% | 98% | **32%** | 100% |
| Furnace | 100% | 92% | 92% | 92% | 88% | 100% |
| Dismantler | 100% | 92% | 92% | 98% | 98% | 100% |
| Iron Colossus | 78% | 95% | **50%** | 92% | 100% | 100% |
| Pendulum | 98% | 88% | 90% | 90% | 92% | 100% |

**Reading:**
- The Clock Tower punishes Spring-heavy and slow decks; the Iron Colossus punishes Coupler/Mirror chains of small hits. These two give real counter-play.
- **The Furnace, Dismantler and Pendulum hit every deck about evenly:** their themes don't bite yet. To sharpen them, shift difficulty from attacks to the theme (more Heat for the Furnace, more unscrews for the Dismantler, a harsher swing for the Pendulum) and retune.

## Results v14 (balance targets; part picks re-measured)

**Balance targets** now live in `sim/clockwork/targets.py` and at the top of Database.md: each metric's target, its latest measurement, and whether it's on target. Most are on target. The two content rows that aren't are part picks and some attachments.

**Part picks, re-measured.** The old part values (v6) came from win rates at full HP against the pre-run enemies; with HP carry-over tuning, nearly every single fight from full HP is now won. So they're re-measured as **win-rate points from 30 HP** (typical mid-run HP): the starter plus one copy of the part, against all 13 enemies, 40 fights each (520 fights per deck, same seeds). The starter wins 81%.

| Part | Win pts | | Part | Win pts |
|---|---|---|---|---|
| Magnet | **+15.6** | | Assembly | −2.5 |
| Amplifier | +8.5 | | Hammer | −2.7 |
| Coolant | +5.4 | | Mirror | −4.6 |
| Primer | +3.1 | | Coupler | −6.2 |
| Slider | −0.2 | | Loader | −7.3 |
| | | | Spring | −8.1 |

(From full HP the same probes measure −1.7 to +0.6 HP kept per fight for everything but Magnet, which keeps +6.0: one extra part in an 8-part deck rarely matters when the fight is safe.)

**Reading:**
- **Magnet is now the outlier.** Its 6 Block per pulled part made it the best pick by far.
- **Hammer and Coupler have slipped below zero** since v6. The Heat-based elites and bosses, and the HP carry-over tuning, punish their Heat.
- Spring, Mirror and Loader stay negative alone, as before (enablers that need partners). The proposed target allows enablers to be slightly negative.
- Proposed target: **+3 to +10 points per pick**. A part balance pass would bring Magnet down (e.g. 4–5 Block per pull) and Hammer/Coupler up (less Heat).

## Results v15 (part balance pass; difficulty and bosses retuned)

**Part pass** (`clockwork.part_pass`: win-rate points over the starter when one copy is added, fights from 30 HP against all 13 enemies; 60 fights per enemy for the final check). Target +3 to +10; combo enablers may be slightly negative alone. An extra Striker measures −1.2, as a reference.

| Part | v14 | Change | v15 |
|---|---|---|---|
| Magnet | +15.6 | 3 Block + 2 per pull (was 6 per pull) | +9.5 |
| Slider | −0.2 | 7 damage (was 5) | +8.1 |
| Primer | +3.1 | — | +7.7 |
| Assembly | −2.5 | 1 damage + 3 per install (was 0 + 3) | +6.7 |
| Amplifier | +8.5 | — | +5.5 |
| Coupler | −6.2 | deals 2 damage, no extra Heat (was +2 Heat) | +5.4 |
| Coolant | +5.4 | — | +4.4 |
| Hammer | −2.7 | 10 damage, +3 Heat (was 9, +4) | +3.8 |
| Mirror (enabler) | −4.6 | — | −1.7 |
| Loader (enabler) | −7.3 | +3 Block | −2.8 |
| Spring (enabler) | −8.1 | +3 Block (chain Heat rule unchanged) | −3.5 |

- **Magnet had a breakpoint:** two pulls at 4 Block (8 total) stop a 7-damage attack outright (+12.7); at 3 (6 total) it fell to +0.4. A flat 3 plus 2 per pull keeps 7 Block for two pulls with less swing.
- Single measurements move by a few points between runs (Primer read +3.1, then +7.7, unchanged), so values within ~3 points of a band edge are noise-level.

**Knock-on retuning.** Stronger parts (and the starter's Spring now giving Block) made runs much easier (casual 89%, careless 57%). District growth 0.20 → **0.30**. Bosses re-tuned in run conditions (`boss_tune`): first all five to 76% at growth 0.27, then HP only at 0.30 against the Clock Tower. Bases are chosen so the run's scaled values match what was tuned (attacks round twice otherwise):

| Boss | Base HP | Attacks / special | Beaten on arrival (150 runs each) |
|---|---|---|---|
| Clock Tower | 91 | chime 11 every 4 cranks | 73% |
| Furnace | 66 | 6/6/9, +1/+1/+3 Heat | 72% |
| Dismantler | 85 | 6/8, unscrew 2 / rust | 69% |
| Iron Colossus | 78 | 6, armor 3 | 74% |
| Pendulum | 87 | 4/10, swing | 72% |

**Whole runs:** careless 43%, casual 69% (random boss), expert 87%. Normal fights cost 12–14 HP, elites 19–23.

**Run styles** (casual, base 68%): seek elites 73%, avoid elites 57%, always heal 73%, always tinker 57%, never take parts 57%, save for machine 60%.

**Combo ceiling** rose to 60 (Echo Coupler next to Hammers; Echo+Governor Hammer with Coupler and Mirror 58), from 51.

**Off target now** (Database.md, Balance targets):
- **Rest:** always healing beats always tinkering by 16 points (target ≤ 5). Healing got stronger as fights hit harder. Options: tinker gives an uncommon, or rest heals less (e.g. 12).
- **Strongest single turn** 60 vs ≤ 55: the Coupler's new 2 damage repeats under Echo. Options: Echo can't go on a Coupler, or accept it (it needs a rare attachment).
- Attachment and machine-upgrade values predate this pass and should be re-measured.

## Results v16 (rest heal; attachments and machine upgrades re-measured)

**Rest heal.** After the v15 pass, always healing beat always tinkering by 16 points. The rest heal goes down, and the after-win heal up to keep overall difficulty (300 runs per style from here on, since 150 runs swing ±5 points):

| Rest heal | After-win heal | Base | Always heal | Always tinker | Gap |
|---|---|---|---|---|---|
| 15 | 5 | 68% | 73% | 57% | 16 (v15) |
| 10 | 5 | 55% | 57% | 60% | −3 (150 runs) |
| 10 | 6 | 60% | 62% | 53% | 9 |
| **8** | **7** | **64%** | **66%** | **63%** | **3** |

Chosen: rest heals 8, every win heals 7.

**Attachments** (HP kept per fight from full HP, all 13 enemies, 40 fights each; target +2.5 to +4 for commons/uncommons, +4 to +6 for rares):

| Attachment | v11/v12 | v16 | | Attachment | v11/v12 | v16 |
|---|---|---|---|---|---|---|
| Coil (Spring) | +3.2 | **+5.4** | | Clamp (Magnet) | +2.0 | +2.8 |
| Heat Sink (Striker) | +2.9 | +3.6 | | Feeder (Loader) | +2.5 | +2.8 |
| Bracing (Striker) | +4.1 | +3.5 | | Polish (Mirror) | +2.3 | **+2.3** |
| Counterweight (Plate) | +4.1 | +3.3 | | Governor (Hammer) | +5.5 | **+6.5** |
| Sharpened (Plate) | +3.6 | +3.0 | | Echo (Striker) | +3.2 | **+3.0** |

Pairs: Sharpened+Echo on a Striker +6.5; Echo+Governor on a Hammer +12.9.

- Coil climbed above the band, since its Spring now also gives Block. Governor is slightly high on a Hammer. Echo (rare) is below the rare band. Polish is slightly low.

**Machine upgrades** (runs started with each, 150 runs, base 65%):

| Upgrade | Price | v12 | v16 |
|---|---|---|---|
| Bigger Gear | 75 | +8 | **+18** |
| Flywheel | 70 | +7 | **+16** |
| Extra Hands | 90 | +16 | +14 |
| Heat Housing | 85 | +15 | +11 |

- **Crank Power became much more valuable** (Flywheel, Bigger Gear) now that the Coupler and Hammer cost less Heat, so more cranks can be used. The two cheapest upgrades are now the strongest, so price no longer matches value: reprice (e.g. Bigger Gear 90, Flywheel 85, Extra Hands 80, Heat Housing 70) or trim Crank Power.

## Results v17 (attachment fixes, smarter run policy, fun measurement)

**Attachment fixes** (HP kept per fight, 40 fights per enemy):
- **Coil:** 6 damage (was 8): +5.4 → **+3.5**. 7 damage measured +4.6.
- **Polish:** +40% (was +20%): +2.3 → **+3.4**. +30% measured +2.2.
- **Echo** stays one repeat per turn but becomes **uncommon** (+3.0 fits the uncommon band). Repeating twice measured +6.0 on a Striker (a good rare value), but it raised the strongest single turn from 60 to 78: two Echo Strikers next to a Coupler reach 74 even with Echo kept off Couplers.

**Smarter run policy.** The policy's thresholds became settings, plus three new behaviours: synergy-aware part picks, saving for a nearly affordable machine upgrade, and a measured machine-upgrade order. Each was tested alone against the old policy (200 runs, round 1), and the winners again with 300 runs (round 2):

| Change | Round 1 (base 58%) | Round 2 (base: elites from 60%, 70%) |
|---|---|---|
| Take elites from 60% HP (was 70%) | **68%** | — |
| Take elites from 50% HP | — | **76%** |
| Take elites from 80% HP | 50% | — |
| Rest door below 60% HP (was 50%) | 66% | **75%** |
| Workshop from 70 cogs / 40 cogs | 62% / 61% | 69% |
| Heal below 70% / 50% | 60% / 56% | 70% |
| Save for a machine upgrade | 60% | 66% |
| Synergy-aware part picks | 58% | — |
| Machine upgrade order by v16 value | 58% | — |

New defaults: elites from 50% HP, rest door below 60%. The other behaviours stay available as settings but are off.

**With the smarter policy** (casual 300 runs, careless 300, expert 60): careless 44%, casual **77%**, expert 90%. Runs now take 3.2 elites, find 3.9 attachments and 2.0 machine upgrades, and reach the boss with 63 unspent cogs.

| Boss | Beaten when reached |
|---|---|
| Clock Tower | **66%** |
| Furnace | 85% |
| Dismantler | 85% |
| Iron Colossus | 84% |
| Pendulum | 86% |

**Fun measurement.**
- **Playtest ratings:** when a run or single fight ends, the page asks 6 quick 1–5 ratings (fun, tension, agency, clarity, variety, play again). They go into the copied report and the GitHub issue with the minutes played and decisions made. Reports saved in `playtests/` fill the "Fun (playtests)" rows of Database.md.
- **Simulator proxies** (`studies fun`, casual player, 150 runs, 1030 fights):

| Proxy | Result | Target |
|---|---|---|
| Fight length (turns), normal / elite / boss | 6.3 / 7.5 / 7.6 | 4–8 / – / 6–12 |
| Close wins (≤ 25% HP left), normal / elite / boss | 3% / 20% / 45% | 5–15% / 15–30% / 30–50% |
| Combo turns (4+ triggers) | 18% | 10–30% |
| Choice weight: best plan minus the median plan | 7.3 | ≥ 6 |
| Turns with only one good option (within 3 points) | 16% | < 25% |
| Build variety: entropy of each run's most-copied added part | 0.64 (Magnet in 88 of 150 runs) | ≥ 0.75 |

**Reading:**
- **Elites pay too well now.** The smart player wins most by fighting them down to 50% HP. Since v12 (when elites were tuned), parts and attachments got stronger and salvage gives upgrades, so the "high risk" half has faded. Options: elites back to 100% strength, salvage at 25–35%, or more elite HP.
- **The Clock Tower is now the hard boss** (66% vs 84–86%). Smarter runs arrive with more machine upgrades; the other bosses suffer from them, but extra Crank Power makes the Clock Tower chime more often.
- **Money piles up again** (63 unspent at the boss), from the extra elites. Prices are on hold until acts 2–3 exist.
- **Magnet dominates builds** (the most-copied part in 59% of runs), partly because the policy ranks parts by fixed values. Real players pick more variously; the playtest "variety" rating will tell.
- **Normal fights are rarely close** (3%): a quiet act until elites and bosses. That fits a first act; acts 2–3 can raise it.
- Difficulty is not retuned to 65–70% here: the acts 2–3 targets (Acts-Design.md, question 1) will change act 1's target anyway.

## Results v18 (3 acts, boss rewards, machine levels, elites re-tuned, rare content)

Structure (Acts-Design.md, decisions of 2026-10-06): 3 acts with veteran enemies in acts 2–3, one boss per act (Clock Tower or Pendulum / Furnace or Dismantler / Iron Colossus), a start choice and boss rewards of 1 of 3 machine upgrades, Workshop level-ups, half the missing HP healed between acts. Elites no longer give machine upgrades.

**Deck growth (question 4).** Win rate from 30 HP with the same key parts, adding cards:

| Deck | Win rate |
|---|---|
| 12 parts | 97.3% |
| + 6 basics | 96.3% |
| + 12 basics | 94.8% |
| + 6 weak filler (Coolant / Mirror / Spring) | 92.3% |
| + 12 weak filler | 88.3% |

Size alone costs little; weak filler costs more. No new rule needed (option A stays), and Workshop removal keeps its value.

**Rare content** (elite loot). Attachments: HP kept per fight on the host; parts: win-rate points over the starter from 30 HP.

| Content | First version | Final | Value |
|---|---|---|---|
| Overdrive (attachment) | +50%: +3.9 | **+75%** (+100% measured +6.9) | +4.9 |
| Kickback (attachment) | next part triggers too: Striker +2.0, Plate +3.6 | **next 2 parts trigger too** | Striker +4.4, Plate +5.7 |
| Hammer (rare part) | 10 / +3 Heat: −0.4 to +3.8 | **12 / +1 Heat** (14 / +2 measured +5.1) | +4.8 |
| Boiler (rare part) | 3 + 2 per Heat: +4.4 | **5 + 2 per Heat** (3 + 3 per Heat measured +4.8) | +5.7 |

Hammer 14 / +2 raised the strongest turns to 78–88, so 12 / +1 was chosen (76–84). Loop finder with the final numbers: builds without rare attachments top out at 50; the biggest are Kickback + Overdrive Hammers 84, Echo Coupler + 3 Hammers 76, Boilers + Hammers 71. These need 2–4 rare pieces, so they are act-3 builds; the strongest-turn target is now split: ≤ 55 for builds without rare attachments, ≤ 90 (half an act-3 boss) with them.

**Elites: risk was wrong, not return.** Act-1 runs, casual player, 200 runs per row:

| Elite strength | Avoid elites | Elites from 70% HP | from 50% | from 30% | HP per elite |
|---|---|---|---|---|---|
| ×0.9 (v17) | 70% | 84% | **89%** | 68% | 16 (won 100%) |
| ×1.0 | – | **82%** | 70% | 46% | 22 |
| **×1.05** | – | **79%** | 64% | – | 26–27 |
| ×1.15 | – | 64% | 38% | 8% | 33–34 |

At ×0.9 elites cost no more than a normal fight, so hunting them was always right. At ×1.05 fighting them when healthy still pays (+9 over avoiding) but hunting them hurt costs runs. The policy now takes elites from 70% HP (was 50%). The response is steep: +10% strength roughly doubles the HP cost.

**Machine upgrades** (act-1 runs started with exactly one, 200 runs, paired; none: 57%):

| Upgrade | Clear | Level 2 |
|---|---|---|
| Cooling Fins | 83% (+26) | – |
| Flywheel | 82% (+25) | 84% (+2 more) |
| Extra Hands | 78% (+21) | – |
| Reinforced Frame | 76% (+19) | 88% (+12 more) |
| Heat Housing | 75% (+18) | 79% (+4 more) |
| Bigger Gear | 72% (+15) | – |
| Wide Hopper | 64% (+7) | – |

The policy picks by this order and buys level-ups Frame first. Wide Hopper is a weak start choice and Flywheel's second level adds little; both are candidates for a rework once prices are set.

**Act difficulty** (3-act runs, casual player; acts = clear rate of the runs that reach each act):

| Setting | Runs | Acts 1 / 2 / 3 |
|---|---|---|
| First build: growth 0.3, act strength ×1.35 / ×1.7, armor +1 / +2 (200 runs) | 4% | 80% / 27% / 20% |
| Growth 0.2, ×1.15 / ×1.3, armor +1 / +1 (200) | 82% | 92% / 94% / 95% |
| Growth 0.2, ×1.25 / ×1.45, armor +1 / +1 (120) | 55% | 94% / 73% / 80% |
| Growth 0.2, ×1.3 / ×1.55, armor +1 / +2 (120) | 32% | 94% / 75% / 45% |
| **Final: growth 0.2, ×1.3 / ×1.5, armor +1 / +2** (150) | **41%** | **93% / 76% / 58%** |
| Target | ~35% | ~90% / ~75% / ~55% |

Bosses got their own act strength table (same values for now), so bosses and veterans can be tuned apart later. Within an act, enemies still grow; the first act now grows 20% (was 30%).

Final setting, all players:

| Player | Runs | Acts 1 / 2 / 3 | Target |
|---|---|---|---|
| Careless (greedy, 200 runs) | 14% | 78% / 48% / 36% | ~10% |
| Casual (MCTS@50, 150) | 41% | 93% / 76% / 58% | ~35% |
| Expert (MCTS@200, 60) | 57% | 97% / 76% / 77% | ~70% |

Casual details: bosses when reached Clock Tower 93%, Pendulum 94%, Dismantler 85%, Furnace 89%, Iron Colossus 77%; HP at each boss 37 / 36 / 37; a normal fight costs 10.5 / 12.4 / 14.7 HP by act, an elite 24.6 / 29.4 / 35.0. A run ends with 20.7 parts, 6.0 attachments and 3.8 machine upgrade levels, and reaches the first boss with 43 unspent cogs.

**Reading:**
- The difficulty curve is very steep in act strength: ×1.15 → ×1.3 in act 2 moved its clear rate from 94% to 75%. Small steps from here.
- Iron Colossus is the most common killer (armor punishes many small hits); act 3 has only one boss until more are added.
- Dismantler is a little harder than the Furnace (85% vs 89%; was 72% vs 86% at ×1.25), within noise now.
- Unspent cogs (43) are just over the target; prices wait for the full run economy, as decided.
- **The expert is below target** (57% vs ~70%; the 95% range is 44–68% with 60 runs). Expert and casual clear act 2 at the same rate (76%) because both use the same run policy: routes, rewards and the Workshop don't get smarter with search. Next step: a smarter run policy for the expert (for example, routes planned by remaining HP and the act's boss) before changing the difficulty.
- Wide Hopper is a weak start choice (+7 against +15 to +26) and Flywheel level 2 adds little (+2).

## Results v19 (expert run planning; the hours map in the simulator)

**Expert run planning.** Until v18 the expert used the casual run policy (fixed HP thresholds) and only fought better, so it cleared act 2 no more often than the casual player. The expert now plans its route (`clockwork/planner.py`, `run_policy.EXPERT_STYLE`):
- **Forecasts:** every 3 stops it plays quick greedy fights in its head (4 normal enemies, 3 elites, 3 of the act's boss) with its current deck and machine, and scales their HP cost by 0.7 (the expert loses about 70% of what greedy loses).
- **HP plan:** for each door it projects the HP left when the boss arrives, assuming the remaining stops are normal fights. It takes an elite, a Workshop or a fight only while that projection covers the boss: the boss's forecast cost × 1.5 + 5 HP (at most 85% of max HP). Otherwise it rests. Rest sites heal when the plan falls short (else tinker), and Workshops repair until it doesn't.

Same casual fights (MCTS@50), 120 runs, paired seeds:

| Run policy | Runs | Acts 1 / 2 / 3 | HP at the bosses | Elites | Rests |
|---|---|---|---|---|---|
| Fixed thresholds (casual) | 39% | 94% / 75% / 55% | 37 / 36 / 37 | 2.9 | 6.9 |
| Plan, margin 1.0 × boss cost | 32% | 88% / 62% / 58% | 32 / 31 / 33 | 2.3 | 5.2 |
| Plan, 1.25 × + 5 | 50% | 99% / 72% / 70% | 46 / 43 / 48 | 0.8 | 7.8 |
| **Plan, 1.5 × + 5** | **57%** | 100% / 82% / 70% | 51 / 50 / 55 | 0.4 | 9.4 |
| Plan, 1.25 × + 10 | 56% | 100% / 83% / 67% | 50 / 49 / 55 | 0.5 | 9.2 |
| Plan, 2.0 × + 5 | 58% | 100% / 81% / 72% | 53 / 53 / 59 | 0.3 | 9.8 |

**Expert (MCTS@200 + plan, 60 runs): 73%** (target ~70%; was 57%), acts 100% / 93% / 79%, HP at the bosses 51 / 50 / 56, 0.7 elites and 9.7 rests per run.

Skill now pays off in route choices as well as fights: careless 14%, casual 41%, expert 73%.

**Reading:** the best route skips elites and rests often. Arriving at the boss with 50+ HP is worth more than an elite's loot, and a rest stop (+8 HP and no fight) beats a fight stop (about −11 + 7 HP plus loot) whenever HP is short. Elites passed the act-1 check in v18 (fighting them when healthy beat avoiding them), but over three acts a planning player avoids them. If elites should be part of the expert's route, their reward or the rest site's value needs another look; playtests should show whether people play this way.

**The hours map ("twelve hours to midnight", simulator only).** Each act is a 5 × 3 district (6 fights, 3 elites, 2 rest sites, 3 Workshops; the gate's neighbours are fights). The player enters any unvisited node next to a visited one if its hours fit (fight 2, elite 3, Workshop 1, rest 2), and the boss strikes at midnight or when the player chooses to wait. Rules are in Run-Design.md. Same enemies and acts as the door map; MCTS@50 fights, 100 runs per row:

| Map | Runs | Acts 1 / 2 / 3 | Act 1: fights + elites, cogs | HP at the bosses | Rests | Attachments | Machine levels |
|---|---|---|---|---|---|---|---|
| Doors (casual policy) | 38% | 93% / 76% / 54% | 3.9 + 1.6, 108 | 37 / 36 / 36 | 6.9 | 5.8 | 3.8 |
| Hours 12 | 9% | 86% / 37% / 28% | 3.5 + 0.8, 77 | 38 / 34 / 37 | 1.5 | 2.2 | 2.6 |
| Hours 12, planner | 12% | 95% / 48% / 26% | 4.0 + 0.1, 60 | 47 / 41 / 38 | 2.1 | 1.0 | 2.6 |
| Hours 16 | 10% | 88% / 48% / 24% | 4.3 + 1.2, 101 | 34 / 35 / 29 | 2.4 | 4.0 | 2.8 |
| Hours 16, 3 rest sites | 15% | 84% / 52% / 34% | 3.9 + 1.1, 92 | 33 / 36 / 31 | 3.8 | 4.6 | 2.9 |
| Hours 16, 3 rest sites, planner | 15% | 93% / 45% / 36% | 4.2 + 0.2, 68 | 46 / 38 / 38 | 4.8 | 2.4 | 2.7 |

**Reading:**
- **12 hours buys about 25% less than a door act** (act-1 cogs 77 vs 108). 16 hours matches the door map's income and fight count.
- **Even with door-level income the hours map is much harder** (10–15% vs 38%). The door map hands out healing: rest doors are common and the stop before every boss is a rest site or a Workshop, so the casual player rests about 7 times a run. A district has 2–3 rest sites, often out of the way, so runs rest 2–4 times, tinker less (fewer attachments) and reach acts 2–3 weaker.
- The planner doesn't rescue it: it keeps HP but skips elites and fights, so decks stay small.
- **If the real game uses the hours map**, it needs its own tuning before the acts' difficulty carries over: more rest sites (or rests cheaper than 2 hours), a guaranteed rest or Workshop next to the boss, or weaker veterans. Prices should be set on whichever map ships, since income differs by up to 30%.
- The playtest page keeps the door map (decision 6: doors on the page, hours in the simulator).

## Results v20 (the day map: package 1 of Hours-Map-Ideas.md)

The designer picked package 1, "A Day in the Brass Quarter", for the prototype; B2 (the sweeping hour hand) and B3 (the turning district) are planned later. Built as `Run(map="day")` in the simulator (rules in Hours-Map-Ideas.md, "What was built"). The page keeps doors.

**Tuning steps** (casual player, MCTS@50, 100 runs each; door map for comparison: 38–41%):

| Version | Runs | Acts 1 / 2 / 3 | Notes |
|---|---|---|---|
| As drafted: night ×1.15 on all enemies, cogs ×1.5 at night and at dawn | 17% | 67% / 55% / 46% | a quarter of runs die before act 1's boss; 99 unspent cogs |
| Planner on the same | 14% | 86% / 43% / 38% | |
| Inns open all day | 3% | 59% / 22% / 23% | daytime naps keep players fighting; night elites kill |
| Night strength on normal fights only, bonuses ×1.25 | 15% | 81% / 57% / 33% | elites (night only) had cost 24–44 HP |
| + inns open all day | 6% | 75% / 31% / 26% | |
| Fights 3 hours, elites 4 | 7% | 67% / 39% / 27% | fewer Workshop visits, weaker machines |
| Same, planner | 21% | 88% / 60% / 40% | waits a lot; 2–3 fights per act in acts 2–3 |
| Inns also open for lunch (12–14) | 7% | 80% / 41% / 21% | |
| Enemies ×0.85 on the day map | 57% | 97% / 76% / 77% | 4 elites per run |
| Enemies ×0.9 | 45% | 96% / 78% / 60% | |
| **Enemies ×0.93 (final)** | **41%** | 87% / 74% / 64% | |

**Reading:** the day's shape (fight by day, sleep at night) wasn't the problem; daytime healing (inns all day or at lunch) made runs worse, because players spent it on more fights. A day simply holds more fighting than a door act (about 5.8 fights and 1.3 elites per act against 3.9 and 1.6), so the door map's enemy strength was too high. With its own strength (×0.93 for normal enemies and elites) the day map matches the door map's difficulty.

**Final day map, all players:**

| Player | Runs | Acts 1 / 2 / 3 | Doors (v18/v19) |
|---|---|---|---|
| Careless (greedy, 200 runs) | 16% | 72% / 55% / 42% | 14% |
| Casual (MCTS@50, 100) | 41% | 87% / 74% / 64% | 41% |
| Expert (MCTS@200 + plan, 40) | 70% | 100% / 88% / 80% | 73% |

Casual details: act 1 earns 148 cogs from fights (doors 108) and reaches the first boss with 110 unspent (doors 44), since Workshops close at night; HP at the bosses 41 / 42 / 42; per run 3.5 inn visits (sleep until dawn 1.9, 4 hours 1.1, nap 0.5) and 2.5 Workshops; 2.5 elites, 8.1 attachments, a 25-part deck. Bosses are beaten 89–94% when reached; the danger is in the day's fights.

**Elites are back in the expert's route:** on the day map the planning expert fights 3.3 elites per run (1.8 in act 1), against 0.7 on the door map, because a night's sleep wins back the HP they cost. The day map's structure does what v19 asked for: risk now pays for a player who plans.

**Open points for the day map:**
- **Too much money:** 110 unspent at the first boss. Options: Workshops also sell repairs that take time (D3), commissions (E2), or lower day bonuses. Prices wait for the map that ships.
- **Night is mostly for sleeping:** the casual player sleeps until dawn in about 2 of 3 acts. If the night shift should tempt more, it may need better loot rather than more cogs. (How many fights happen at night isn't measured yet.)
- **Bosses are easy when reached** (89–94%) because players arrive after a night's sleep. Neither automated player tries the ambush (going early) on purpose, so its value is untested.

## Results v21 (the day map: unspent money and a tempting night)

v20's open points: about 110 cogs unspent at the first boss, and a night spent sleeping. Casual player (MCTS@50), 100 runs per row unless noted.

**Step 1: the night market and night loot.** A new night-only node, the night market (1 hour; uncommon/rare attachments and parts, no repairs), 2 per district (7 × 3 grid). Night wins also offer 1 of 2 common/uncommon attachments, and night fights stop paying extra cogs.

| Version | Runs | Unspent at boss 1 | Night fights / run | Markets / run |
|---|---|---|---|---|
| v20 | 41% | 110 | 4.0 | – |
| + market, night attachments | 32% | 56 | 4.0 | 1.4 |

The casual player's fixed rules don't respond to loot: it fights at night exactly as often as before. "Tempting" needs a test of the choice itself.

**Step 2: is the night worth going out for?** Two play styles: the **sleeper** goes to bed at nightfall and stays in; the **night owl** fights, takes elites and visits markets at night.

| Version | Sleeper | Night owl | Notes |
|---|---|---|---|
| v20 (sleep until dawn) | **61%** | 7% | the sleeper meets every boss at full HP (55) |
| + market, night attachments | 55% | 7% | loot can't make up 27 HP at the boss |
| Full night's sleep = 6 hours, once a night; owl: night out, then bed | 38% | 35% | a real choice; the owl ends with 8.9 attachments vs 5.0 |
| + night enemies ×1.05 (was ×1.15) | 38% | **41%** | going out now edges out staying in |

Sleeping until dawn was the problem: it turned every night into a full heal right before the boss. A 6-hour full sleep (then only naps) leaves about 6 night hours, and a night out followed by bed is now at least as good as staying in.

**Step 3: money.** Hurry bonus ×1.1 (was ×1.25) and a bigger market (4 attachments, 3 parts):

| Player | Runs | Acts 1 / 2 / 3 | Unspent at boss 1 | Night fights / run | Markets / run |
|---|---|---|---|---|---|
| Careless (greedy, 200 runs) | 16% | 76% / 50% / 43% | 51 | 3.4 | 1.5 |
| Casual (MCTS@50, 100) | 37% | 95% / 65% / 60% | 55 | 4.7 | 1.9 |
| Expert (MCTS@200 + plan, 40) | 70% | 100% / 90% / 78% | 49 | 5.4 | 2.2 |

The smaller hurry bonus barely moved income (act 1: 133 → 128 cogs), so one more sink: **inns charge for a bed** (nap free, 4 hours 10 cogs, a full night 20). Casual: **39%** (acts 94% / 68% / 61%), **47 unspent** at the first boss, 4.8 night fights and 1.6 markets per run. (The careless and expert rows above were measured just before bed prices.)

**Reading:**
- **Money:** unspent cogs at the first boss went from 110 to 47, about the door map's 44. The "under 40" target waits for the price pass (prices are set once the run economy is final).
- **The night:** staying in is no longer the obvious choice. A night out (then bed) now beats staying in (41% vs 38%), and every player fights at night 3–5 times per run and visits a night market about 2 times.
- **Difficulty is unchanged:** careless 16%, casual 37–39%, expert 70% (targets ~10 / ~35 / ~70%).

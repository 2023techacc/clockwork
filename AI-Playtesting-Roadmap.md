# Clockwork — AI Playtesting Roadmap

Four agent tiers, each meant to be a little smarter than the last, run against the same headless simulator and the same fixed encounter(s). The point isn't just automated playtesting — the *shape* of the improvement curve across tiers is itself a balance signal. A well-balanced fight should show smooth, explainable gains as agents get smarter. A sudden jump at any one tier usually means that tier found something qualitatively different (an exploit, a broken loop, a design assumption that doesn't hold under real pressure) rather than just "playing better." Watch for the jump, not just the final numbers.

Prerequisite for all four: a rules-accurate headless simulator (trigger order, Heat curve, reshuffle curve, Mirror/Coupler restrictions, etc. — see Rules-Decisions.md for the current test-baseline ruleset). Building that is the bulk of the work; each agent tier below is cheap by comparison.

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

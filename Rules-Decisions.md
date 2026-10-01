# Clockwork — Design Decisions (addendum to Rules.md)

Resolutions to the critical gaps flagged in review. Anything still open is marked **OPEN**.

---

## Trigger resolution order
**Decision:** Coupler resolves its two neighbors left, then right (not simultaneous). Applies generally: whenever a single trigger causes multiple downstream triggers, resolve in a fixed, deterministic order rather than "at once" — left/clockwise-first is the default unless a part says otherwise.

## Block
**Decision:** Block resets to 0 at the start of each turn (standard deckbuilder behavior), not persistent.

## Empty Trigger Point
**Decision:** Nothing happens — no trigger, no Heat, no effect. This is intentionally a dead outcome to build around.
**Idea to explore:** some parts could specifically care about an empty Trigger Point (e.g., a part that triggers *because* the point is empty, or benefits from gaps in the gear). Not designed yet — flag for the part-type pass.

## Bag/discard reshuffle
**Leaning toward (not fully decided):** when the bag runs out mid-turn/fight, the discard pile shuffles back into the bag to refill it. Reshuffle Heat cost is shifted down one step from the original idea: **+0 Heat on the first reshuffle of a turn, +1 on the second, +2 on the third**, etc.
**Why the shift to +0 first:** a single reshuffle will happen naturally in any fight that runs long enough — it shouldn't be taxed just for occurring. The escalation should only kick in on *repeated* reshuffling within the same turn, which is the actual loop-risk signal (something trying to cycle the whole bag multiple times in one turn), not ordinary play.
**Why this matters beyond the curve tweak:** draw/reshuffle-related part archetypes are wanted for variety (regardless of whether the base resource-feed ends up being a draw-from-bag or a visible queue) — a gentler curve means strong draw-payoff parts can be designed without every one of them needing individual loop-safety review. This is the main reason #1 was picked over deleting the mechanic (option 4) or moving it off Heat entirely (option 3).
**OPEN:** still not locked in. Also still open: whether this coexists with or replaces the hard "8 triggers/turn" cap from §8b (§8b itself is unsettled — see below).

## Crank Power
**Decision:** Crank Power exists and is given fresh every turn (does not carry over) — it's the Energy/mana equivalent from other deckbuilders, but scoped only to buying extra crank steps rather than gating card/part plays.
**Why per-turn, not a fight-long pool:** a flat per-turn amount can't accumulate no matter how long a fight runs, which keeps it from ever growing large enough to let a player reliably reach any gear slot late in a fight — that would quietly kill the timing-puzzle half of the game (see §9's "when do I let the big part reach the top"). A fight-long pool that Blueprints could grow risks exactly that. It would also cannibalize the Clock Tower boss's identity (§7), whose whole twist is a *fight-total* crank budget — if that were the default for every fight, Clock Tower stops being special.
**Idea, not yet decided:** if a "banked/stored power" fantasy is still wanted (mainspring flavor), it should live as a separate, capped, Blueprint-only resource layered on top of the per-turn baseline (e.g., "once per fight, gain +5 Crank Power on a turn of your choice") rather than replacing the per-turn model.

## Win/loss conditions
**Decision:** Follow Slay the Spire conventions — enemy HP to 0 wins the fight, player HP to 0 ends the run. No new mechanic needed here; just make it explicit in Rules.md.

---

## Systems previously underspecified

### Second Gear
**Decision:** Second Gear shares most systems with the first (same bag, same hand, same install budget) — it isn't a parallel economy. Its distinguishing features are just: it meshes with Gear A (turns opposite direction, per existing rule) and it adds more slot space overall.
**OPEN:** exact slot count for Gear B, and whether the existing "2 installs per turn" budget covers both gears combined or needs to change now that there's more board to fill. Not decided yet.

### Workshop currency
**Decision:** Deferred — currency source/curve to be decided later, after the base loop is validated. Not a blocker for early prototyping (can proxy with "generic gold" placeholder).

### Part upgrades
**Decision:** Upgrading a part literally upgrades it — effect differs per part type (e.g., Striker+ might deal more damage, Coolant+ might remove more Heat). No universal upgrade formula; each part needs its own upgrade defined when that part is designed.

### Magnet
**Decision:** Magnet pulls a part toward it only when the destination slot is empty. If the destination is occupied, nothing happens by default — swap/bump behavior would require a distinct, separate part that explicitly says so (a "Magnet+"-type variant), not baseline Magnet behavior.

### Amplifier's scope
**Decision:** Amplifier's +50% applies only to damage- and Block-type effects (Striker, Hammer, Plate, etc.), not to utility effects (Heat removal, part loading/rearranging, etc.).

### Rust's "power"
**Decision:** "Power" as a generic stat name is wrong/unclear and will be replaced. Needs a real term once the full part-effect model is defined (likely per-effect-type reduction — e.g., separate handling for damage parts vs. utility parts — rather than one universal stat).

---

## Test baseline v1 (for balance/paper-prototype work)

These are fixed as working assumptions to start balance testing with — expected to change after actual play, but needed as a stable starting point rather than open questions.

- **Resource feed: queue, not draw.** Going with the visible-queue/conveyor model over random bag-draw for the prototype. Reshuffle-Heat (below) still applies conceptually — whatever the queue's equivalent of "recycling used parts back into supply" turns out to be should carry the same escalating Heat cost.
- **Reshuffle/recycle Heat:** +0 on the first reshuffle of a turn, +1 on the second, +2 on the third, etc. (see below).
- **Crank Power:** 2 per turn as the starting value; expect to tune somewhere in the 1–3 range once tested.
- **§8b Balance Rules — split by priority:**
  - **Implementing now (still tunable, but active in the test baseline):** #3 Spring Heat curve, #4 no-copy-loop rules (Mirror can't copy Mirror, Coupler can't trigger Coupler), #5 "big numbers go on slow parts" as a design guideline, #6 enemies scale with machine size.
  - **On hold, not yet implemented:** #1 (2-triggers-per-part cap) and #2 (8-triggers-per-turn hard cap). Revisit after seeing whether #3/#4/#5/#6 plus reshuffle-Heat are sufficient on their own.
- **Draw/queue-reliant archetypes need their own reason to exist** — not just "safe because the loop-brake is gentle now," but an actual payoff/identity (e.g., consistency, digging for a specific answer, a resource-conversion angle) worth designing toward deliberately in the part-type pass, not just permitted by default.

---

## Explicitly not decided yet

- **§8b rules #1 (2-triggers-per-part cap) and #2 (8-triggers-per-turn cap)** — on hold, see test baseline above. Revisit once #3/#4/#5/#6 + reshuffle-Heat have been playtested.
- **Enemy design** (base attack patterns, elite tier, multi-enemy encounters, per-enemy Jam/Rust/Unscrew/Wind Back tuning) — acknowledged as a significant chunk of work on its own; not started. Use §8b's placeholder ("Attack 8 every turn, 60 HP") for initial testing.
- **Currency/economy curve** — see Workshop currency above.

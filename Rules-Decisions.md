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

---

## Simulator defaults v1

Provisional rules the headless simulator (`sim/`) runs on. Tunable numbers and on/off rules live in `sim/clockwork/config.py`. Items marked **(sim default)** were filled in for the simulator and still need confirming; everything else is confirmed.

### Heat
- **Every trigger adds 1 Heat**, and part extras are added on top: Spring +1 (first in a chain), Hammer +2 (3 Heat total). The §8 example costs **8 Heat** (Spring 2 + Spring 3 + Hammer 3).
- **Spring chain:** a chain is everything that follows from one crank the player makes (free, extra or backward). The n-th Spring in a chain adds +n on top of the base 1 (+1, +2, +3, +4, …).
- **Overheat:** reaching 10 Heat stops the turn immediately, with no further triggers or cranks. Heat goes back to 0. The part that hit 10 still applies its own effect (damage, Block, …) before the stop. The next turn is dead: no free crank and no paid cranks; installing is still allowed.
- **Coolant (sim default):** its own +1 Heat counts first, then it removes 3, so it nets −2. Heat never goes below 0.
- **Excess Heat is forgiven (decided, intentional).** Heat above 10 is discarded by the Overheat reset, so the trigger that tips the machine over pays only part of its Heat cost. This is kept on purpose: it rewards using high-Heat parts as the last trigger before an Overheat. Side effect, as the simulator shows: Heat costs don't make parts weaker smoothly (e.g. a 6-Heat Hammer outperformed a 4-Heat one), so balance high-Heat parts by sweeping, not by intuition.
- **Hammer (sim v3): 9 damage, +4 Heat** (Rules.md: 15 damage, +2 Heat). Swept so one Hammer adds about +25 win-rate points to the starter deck; see Results v3b in the roadmap. This value accounts for forgiven excess Heat.

### Geometry and resolution order
- Left/right are as seen from the centre of the gear looking out at a part: left is the counter-clockwise neighbour.
- A forward crank turns the gear clockwise, so the part to the **left** of the top comes up next. The §8 example's list is in the order parts come up, which is counter-clockwise around the gear. The "Gear (clockwise)" label in Rules.md §8 should probably say "in arrival order".
- **Coupler** resolves depth-first: its left neighbour and everything that follows from it, then its right neighbour. The Coupler's own trigger costs 1 Heat, and each neighbour costs its own. **(sim default: the targets are the parts that were next to it when it triggered.)**
- **Spring** cranks in the direction its trigger was travelling, away from the part before it. After a forward crank it cranks forward. After a backward crank it cranks backward. A Coupler's left neighbour cranks forward and its right neighbour cranks backward.
- **Mirror** acts exactly as if the opposite part were sitting in the Mirror's slot: same Heat and same effect. Amplifiers next to the Mirror apply, and a copied Spring cranks. A copied Coupler triggers the Mirror's neighbours, and since it counts as a Coupler, a Coupler can't trigger it. Copying a Mirror, an empty slot or an Amplifier does nothing and costs no Heat.
- **Any part can be triggered** unless it says otherwise. The Amplifier says otherwise.
- **Amplifiers add up:** +50% each, applied to damage and Block only, rounded down.

### Cranking and installing
- **Crank direction is locked per turn:** when installing ends, the player picks clockwise or counter-clockwise for the whole turn. The free crank and every paid crank (1 Crank Power each, no limit) go that way, and each triggers the new top part. Cranking back and forth in one turn is no longer possible. (The setting `crank_direction_lock` turns it off for comparison: free crank clockwise, paid cranks either way.)
- Springs still crank the way their trigger was travelling, so a Coupler's right-hand Spring can still turn the gear against the turn's direction. **(sim default: the lock covers player cranks only.)**
- **Gear starts empty.** Installing into the top slot is allowed but does not trigger anything. Replacing a part sends the old one to the discard pile.
- **Empty Trigger Point:** nothing happens and the chain ends.

### Queue
- 5 parts are visible, and the first 3 of them are offered each turn, so 2 upcoming parts can be seen beyond the hand.
- Offered parts you don't install are discarded. This may change; the discard and reshuffle may go away entirely.
- **Recycling:** when fewer than 3 parts are left to offer, the discard pile is shuffled and added behind the queue. It costs +0 Heat for the first recycle in a turn, +1 for the second, +2 for the third, and so on.

### Parts still undefined in the rules (sim defaults)
- **Magnet:** pulls both parts that are 2 slots away (left side first), each only into an empty slot.
- **Loader:** installs the next part in the queue. If the queue is empty, recycling happens first. If there's no empty slot, nothing happens. The loaded part doesn't trigger. **(sim default: it goes into a random empty slot.)**
- **Jam:** blocks a slot (not a part) for 2 of the player's turns. Amplifiers still work in a jammed slot. Moving a part out of a jammed slot frees that part. Targets are chosen when the intent is revealed.
- **Unscrew:** the part goes to the discard pile. **Wind Back:** the gear turns 1 step counter-clockwise and nothing triggers.
- **Clock Tower (v2, chime):** no regular attack. Every 4th crank of the fight, including Spring cranks, it strikes for 15 after the arriving part's chain resolves, hitting current Block (a strike still lands if that trigger overheats). 115 HP (±3). Replaced the 12-crank instant-loss rule, which made Block useless: every Plate trigger spent one of the 12 cranks. When the 12th crank happens, the tower strikes at the end of that turn unless the enemy is already dead.
- **Not simulated yet:** Rust (its stat is undefined), Blueprints, Second Gear, Bigger Gear (gear size is a setting), part upgrades, and §8b #6 (enemies scaling with machine size).
- **Win/loss:** the fight is won the moment enemy HP reaches 0, even partway through a chain.

---

## New parts and attachments (sim v4, proposals under test)

**Payoff parts** for the enablers that underperform:

| Part | Effect | Pairs with |
|---|---|---|
| **Primer** | 18 damage on its first trigger after being installed, 4 after that. Installing it again (from the queue, or via Loader) re-arms it. | Loader, replacing parts |
| **Assembly** | 2 damage per occupied gear slot, itself included (12 on a full 6-slot gear) | Loader filling the gear |
| **Slider** | 5 damage, +6 if a Magnet moved it this turn | Magnet |

**Attachments:** a per-part upgrade, like bolting something onto a part. A part takes at most one, and each attachment fits one part type. How players get them in a run is not designed yet; for now they're fixed in the test decks. A Mirror copying a part copies its attachment too, consistent with "the copied part sits in the Mirror's place".

| Attachment | Fits | Effect |
|---|---|---|
| **Coil** | Spring | The part this Spring's crank triggers also deals 4 damage (flat, not amplified). Lost if the crank lands on an empty slot. |
| **Polish** | Mirror | The copy's damage and Block get +50%, added to any Amplifier bonus |
| **Clamp** | Magnet | Every part this Magnet pulls is triggered (left side first) |
| **Feeder** | Loader | Loads into the next empty slot to come up in the turn's direction, not a random one |

Numbers are first guesses; the probe results are in the roadmap ("Results v4").

### Balance pass v5 (current simulator values)
- **Primer:** 2 damage; 8 if it triggers on the turn it was installed.
- **Assembly:** 3 damage per part installed this turn (by hand or by Loader).
- **Coupler:** +2 Heat.
- **Amplifier:** +30%.
- **Polish:** +20%.
- **Clamp:** triggers only the first pulled part.
- **Hammer:** 9 damage, +4 Heat.
- **Coil:** 4 damage.
- **Magnet:** pulls into occupied slots by swapping.

All numbers are settings in `sim/clockwork/config.py` and `sim/clockwork/parts.py`. See "Results v5" in the roadmap.
- **Loader:** installs the next **two** parts in the queue per trigger.
- **Slider:** moved bonus +3 (was +6).
- **Enemy HP:** each fight rolls base ±3.

### Balance pass v12 (attachments)
Measured as HP kept per fight (roadmap, Results v11/v12). Target: common and uncommon attachments worth about 2.5–4 HP per fight.
- **Bracing:** +1 damage and +1 Block when it triggers, on top of the immunity to Jam, Rust and Unscrew (immunity alone was worth +0.3).
- **Coil:** 8 damage (was 4; 4 and 6 were worth +0.7 and +1.7).
- **Feeder (reworked):** the Loader loads 1 more part, into the next slots to come up, and every part it loads triggers right away. Extra loads alone were worth nothing.

### Runs: HP carry-over (decided)
- **HP carries over between fights; a small heal follows each win.** Sim placeholder: 10 HP (`heal_between_fights`).
- **Normal enemies** are tuned to cost a casual player about 15 HP per win.
- **The boss** is tuned for a casual player arriving with about 35 HP to win roughly 70%.
- **Current enemies (v7):** dummy 55 HP / attack 7; spiker 58 / 3-3-14; enrager 60 / 3 +1 per turn; saboteur 56 / 7-5; Clock Tower 98 HP, strikes every 4 cranks for 12.

# Clockwork database

Every part, attachment, enemy and machine upgrade with its current numbers. **Generated** from the simulator by `python sim/build_database.py`; don't edit by hand (a test fails when it is stale). Rules and reasoning: Rules.md, Rules-Decisions.md, Run-Design.md; measurements: AI-Playtesting-Roadmap.md.

## Balance targets

What each number is tuned toward, and the latest measurement (from the roadmap results named in Source; `sim/clockwork/targets.py`). Casual = MCTS@50, careless = greedy, expert = MCTS@200.

| Area | Metric | Target | Latest | Status | Source |
|---|---|---|---|---|---|
| Runs | Casual player clears a run | 65–70% | 64–65% | ⚠️ partly off | v16 |
| Runs | Careless player clears a run | 40–50% | 43% | ✅ on target | v15 |
| Runs | Expert player clears a run | 85–90% (clearly above casual) | 87% | ✅ on target | v15 |
| Runs | HP when reaching the boss (casual) | about 35 | 37 | ✅ on target | v15 |
| Fights | HP a normal fight costs (casual) | about 15 | 12–14 | ✅ on target | v15 |
| Fights | HP an elite costs (casual) | about 25 (high risk) | 19–23 | ⚠️ partly off | v15 |
| Fights | Boss beaten when reached (casual) | about 75%, every boss within ±5 of the others | 69–74% | ✅ on target | v15 |
| Choices | Fighting elites when healthy vs avoiding them | elites at least as good (high return) | 68% vs 57% | ✅ on target | v15 |
| Choices | Rest: always heal vs always tinker | within 5 points of each other | 66% vs 63% | ✅ on target | v16 (300 runs each) |
| Choices | Run styles (route, rest, Workshop) | no style more than 5 points above the base | best: seek elites, always heal (+5) | ✅ on target | v15 |
| Content | One part pick (win-rate points over the starter, fights from 30 HP) | +3 to +10; combo enablers (Spring, Mirror, Loader) may be slightly negative alone | Magnet +9.5, Slider +8.1, Primer +7.7, Assembly +6.7, Amplifier +5.5, Coupler +5.4, Coolant +4.4, Hammer +3.8 | ✅ on target | v15 |
| Content | One combo-enabler pick (same measure) | −5 to +3 | Mirror −1.7, Loader −2.8, Spring −3.5 | ✅ on target | v15 |
| Content | One common/uncommon attachment (HP kept per fight) | +2.5 to +4 | Coil +5.4, Heat Sink +3.6, Bracing +3.5, Counterweight +3.3, Sharpened +3.0, Clamp +2.8, Feeder +2.8, Polish +2.3 | ⚠️ partly off | v16 |
| Content | One rare attachment (HP kept per fight) | +4 to +6 | Governor +6.5, Echo +3.0 | ❌ off target | v16 |
| Content | One machine upgrade (run clear points, started with it) | +7 to +16, rising with price (Flywheel 70, Bigger Gear 75, Heat Housing 85, Extra Hands 90) | Bigger Gear +18, Flywheel +16, Extra Hands +14, Heat Housing +11 | ⚠️ partly off | v16 |
| Content | Strongest single turn (any combo) | about half the boss's HP (≤ 55; a few over is accepted) | 60 | ✅ on target | v15 (Echo Coupler + Hammers) |
| Economy | Attachments per run | 2–4 | 2.3 | ✅ on target | v15 |
| Economy | Machine upgrades per run | about 1 | 0.93 | ✅ on target | v15 |
| Economy | Cogs unspent when reaching the boss | under 40 | 35 | ✅ on target | v15 |
| Fun (playtests) | “How fun was it?” (1–5) | 4.0 or more | no playtests yet |  | 0 reports in playtests/ |
| Fun (playtests) | “How tense were the fights?” (1–5) | 3.5–4.5 (tense, not stressful) | no playtests yet |  | 0 reports in playtests/ |
| Fun (playtests) | “Did your choices matter?” (1–5) | 4.0 or more | no playtests yet |  | 0 reports in playtests/ |
| Fun (playtests) | “Was it clear what happened and why?” (1–5) | 3.5 or more | no playtests yet |  | 0 reports in playtests/ |
| Fun (playtests) | “Did it feel different from your earlier runs?” (1–5) | 3.5 or more | no playtests yet |  | 0 reports in playtests/ |
| Fun (playtests) | “How much do you want to play again right now?” (1–5) | 3.5 or more | no playtests yet |  | 0 reports in playtests/ |
| Fun (playtests) | Human players clear a run | close to the casual AI (65–70%) | no playtests yet |  | 0 finished runs |
| Fun (playtests) | Minutes per run | 20–40 | no playtests yet |  | page timer |

## Basics

| Rule | Value |
|---|---|
| Player HP | 55 |
| Gear slots | 6 |
| Parts offered per turn / visible in the queue | 3 / 5 |
| Installs per turn | 2 |
| Crank Power per turn (after the free crank) | 2 |
| Heat per trigger | 1 |
| Overheat at | 10 Heat: the turn stops, Heat goes to 0, next turn is dead; Heat past the limit is forgiven |
| Crank direction | one direction per turn, chosen when installing ends |
| Max attachments per part | 2 |

## Parts

Tier decides how often a part shows up as a reward and its Workshop price.

| Part | Tier | Price | Heat per trigger | Effect |
|---|---|---|---|---|
| **Striker** | starter | - | 1 | Deal 6 damage. |
| **Plate** | starter | - | 1 | Gain 6 Block. |
| **Spring** | common | 30 | 1 | Gain 3 Block. Crank again for free, continuing in the direction the trigger came from. Extra Heat: +1 for the 1st Spring in a chain, +2 for the 2nd, +3 for the 3rd... |
| **Mirror** | common | 30 | 1 | Acts exactly as the part directly opposite it (attachments included). Can't copy a Mirror. |
| **Amplifier** | uncommon | 45 | 0 | Passive: neighbours' damage and Block +30%. Never triggers. |
| **Coupler** | uncommon | 45 | 1 | Deal 2 damage. Triggers its left neighbour, then its right one. Can't trigger a Coupler. |
| **Loader** | uncommon | 45 | 1 | Gain 3 Block. Installs the next 2 queue parts into empty slots. If the gear is full, one replaces the part opposite the Loader. |
| **Coolant** | common | 30 | 1 | Remove 3 Heat. |
| **Hammer** | rare | 65 | 4 | Deal 10 damage. +3 Heat. |
| **Magnet** | uncommon | 45 | 1 | Gain 3 Block. Pulls the parts 2 slots away into the slots next to it (swapping if occupied). +2 Block per part pulled. |
| **Primer** | uncommon | 45 | 1 | Deal 2 damage, or 8 if it was installed this turn. |
| **Assembly** | uncommon | 45 | 1 | Deal 1 damage, +3 per part installed this turn. |
| **Slider** | uncommon | 45 | 1 | Deal 7 damage, +3 if a Magnet moved it this turn. |

## Attachments

Items with a rarity. Attached permanently to one part copy (up to 2 per part, no duplicates); unattached ones can be sold for half price. Value = HP kept per fight on its best host (studies, Results v11/v12).

| Attachment | Rarity | Fits | Price | Effect | Value |
|---|---|---|---|---|---|
| **Sharpened** | common | any part | 30 | +2 damage when it triggers. | +3.0 (Plate) |
| **Counterweight** | common | any part | 30 | +2 Block when it triggers. | +3.3 (Plate) |
| **Bracing** | common | any part | 30 | +1 damage and +1 Block when it triggers. Immune to Jam, Rust and Unscrew. | +3.5 (Striker) |
| **Heat Sink** | uncommon | any part | 55 | Its triggers cost 1 less Heat. | +3.6 (Striker) |
| **Coil** | uncommon | Spring | 55 | The part this Spring's crank triggers also deals 6 damage. | +3.5 |
| **Polish** | uncommon | Mirror | 55 | The copy's damage and Block +40%. | +3.4 |
| **Clamp** | uncommon | Magnet | 55 | The first part it pulls is triggered. | +2.8 |
| **Feeder** | uncommon | Loader | 55 | Loads 1 more part, into the next slots to come up instead of random ones, and the loaded parts trigger right away. | +2.8 |
| **Echo** | uncommon | any part | 55 | The first time it triggers each turn, it triggers again. | +3.0 (Striker) |
| **Governor** | rare | any part | 90 | Its triggers add no Heat. | +6.5 (Hammer) |

## Enemies

In a run, enemies grow through the district: HP and attacks × (1 + 0.3 × stop/9), so the boss is ×1.30. Elites are fought at ×0.9 on top. Each fight's HP also rolls ±3. Cogs vary ±10%.

### Normal

| Enemy | HP | Cogs | Pattern | Tests |
|---|---|---|---|---|
| **dummy** | 55 | 12 | Every turn: attack 7. | Plain attacker: the baseline. |
| **spiker** | 58 | 15 | Turn 1: attack 3. Turn 2: attack 3. Turn 3: attack 14. Then repeats. | Telegraphed big hit every 3rd turn: tests Block timing. |
| **enrager** | 60 | 14 | Every turn: attack 3 (+1 per turn). | Attacks grow every turn: tests burst damage. |
| **saboteur** | 56 | 16 | Turn 1: attack 7. Turn 2: jam a part (2 turns), attack 5. Turn 3: wind back (gear turns 1 step counter-clockwise), attack 7. Turn 4: unscrew a part, attack 5. Then repeats. | Messes with the machine (jam, wind back, unscrew). |

### Elites

| Enemy | HP | Cogs | Pattern | Tests |
|---|---|---|---|---|
| **overclocker** | 80 | 32 | Turn 1: attack 7. Turn 2: +3 Heat to your machine, attack 5. Then repeats. | Adds Heat to your machine. |
| **rust_golem** | 86 | 34 | Turn 1: rust the top part (-2 damage/Block this fight), attack 7. Turn 2: attack 7. Then repeats. | Rusts the part at the top: it deals and blocks less for the rest of the fight. |
| **pickpocket** | 84 | 30 | Every turn: unscrew a part, attack 7. | Unscrews a part every turn. |
| **jammer_prime** | 74 | 36 | Turn 1: jam a part (2 turns), jam a part (2 turns), attack 7. Turn 2: attack 7. Then repeats. | Jams 2 parts every other turn. |

### Bosses

| Enemy | HP | Cogs | Pattern | Tests |
|---|---|---|---|---|
| **clock_tower** | 91 | 60 | No regular attacks. Strikes for 11 on every 4th crank (Springs count). | No attacks; strikes on every 4th crank of the fight, after the part that comes up. Tests doing more with fewer cranks. |
| **furnace** | 66 | 60 | Turn 1: +1 Heat to your machine, attack 6. Turn 2: +1 Heat to your machine, attack 6. Turn 3: +3 Heat to your machine, attack 9. Then repeats. | Heats your machine every turn, a big stoke every 3rd: tests Heat management. |
| **dismantler** | 85 | 60 | Turn 1: unscrew a part, unscrew a part, attack 6. Turn 2: rust the top part (-2 damage/Block this fight), attack 8. Then repeats. | Takes your machine apart: tests rebuilding and Bracing. |
| **iron_colossus** | 78 | 60 | Every turn: attack 6. Armor 3: every hit on it deals 3 less. | Armor on every hit: tests big single hits over many small ones. |
| **pendulum** | 87 | 60 | Turn 1: attack 4. Turn 2: attack 10. Then repeats. Swing: odd turns must crank clockwise, even turns counter-clockwise. | Forces the turn direction (odd turns clockwise, even counter-clockwise): tests layouts that work both ways. |

## Machine upgrades

Permanent upgrades to the machine. Every Workshop sells all the ones you don't have; elites have a 50% chance to let you salvage 1 of 2 for free.

| Upgrade | Price | Effect |
|---|---|---|
| **Flywheel** | 70 | +1 Crank Power per turn |
| **Heat Housing** | 85 | +2 Heat before Overheat |
| **Extra Hands** | 90 | +1 install per turn |
| **Bigger Gear** | 75 | 8 gear slots instead of 6, and +1 Crank Power to turn it |

Candidates (simulator only, not sold): Reinforced Frame: +10 max HP; Wide Hopper: 4 parts offered each turn instead of 3; Bigger Gear (old): 8 gear slots instead of 6.

## Run

| Rule | Value |
|---|---|
| Stops | 9 door choices, then the boss (picked at the start from: clock_tower, furnace, dismantler, iron_colossus, pendulum) |
| Doors | stops 1-2 are fights; then 3 doors weighted fight 4, elite 2, workshop 1.5, rest 1.5; the last stop offers a rest site or a Workshop |
| After a win | heal 7 HP, loot cogs, pick 1 of 3 parts (or scrap for 10 cogs, or skip) |
| Part reward tiers | common 5, uncommon 4, rare 1 (weights) |
| Elite loot | a part from the uncommon/rare tiers, 1 of 3 uncommon/rare attachments, 50% chance of a free machine upgrade (1 of 2) |
| Rest site | heal 8, or tinker: take both offered common attachments |
| Workshop | 3 parts, 2 uncommon/rare attachments, every machine upgrade you lack; repair 15 HP for 25; remove a part for 40 (+15 each time) |

## Test decks

`starter` is the run's starting deck; the others are fixed test decks (the starter plus 4 parts).

| Deck | Parts |
|---|---|
| **starter** | 4× Striker, 3× Plate, 1× Spring |
| **spring_chain** | 4× Striker, 3× Plate, 3× Spring, 1× Coolant, 1× Hammer |
| **copy_loop** | 4× Striker, 3× Plate, 1× Spring, 2× Coupler, 2× Mirror |
| **big_hit** | 4× Striker, 3× Plate, 1× Spring, 2× Hammer, 2× Amplifier |
| **sustain** | 4× Striker, 3× Plate, 2× Spring, 2× Coolant, 1× Coupler |
| **utility** | 4× Striker, 3× Plate, 1× Spring, 2× Loader, 2× Magnet |

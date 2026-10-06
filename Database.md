# Clockwork database

Every part, attachment, enemy and machine upgrade with its current numbers. **Generated** from the simulator by `python sim/build_database.py`; don't edit by hand (a test fails when it is stale). Rules and reasoning: Rules.md, Rules-Decisions.md, Run-Design.md; measurements: AI-Playtesting-Roadmap.md.

## Balance targets

What each number is tuned toward, and the latest measurement (from the roadmap results named in Source; `sim/clockwork/targets.py`). Casual = MCTS@50, careless = greedy, expert = MCTS@200.

| Area | Metric | Target | Latest | Status | Source |
|---|---|---|---|---|---|
| Runs | Casual player clears a run | 65–70% | 77% | ❌ off target | v17 (smarter run policy) |
| Runs | Careless player clears a run | 40–50% | 44% | ✅ on target | v17 |
| Runs | Expert player clears a run | 85–90% (clearly above casual) | 90% | ✅ on target | v17 |
| Runs | HP when reaching the boss (casual) | about 35 | 36 | ✅ on target | v17 |
| Fights | HP a normal fight costs (casual) | about 15 | 12–14 | ✅ on target | v15 |
| Fights | HP an elite costs (casual) | about 25 (high risk) | 19–23 | ⚠️ partly off | v15 |
| Fights | Boss beaten when reached (casual) | about 75%, every boss within ±5 of the others | Clock Tower 66%, others 84–86% | ❌ off target | v17 |
| Choices | Fighting elites when healthy vs avoiding them | elites at least as good (high return) | 68% vs 57% | ✅ on target | v15 |
| Choices | Hunting elites at low HP (risk) | should cost runs (high risk) | elites from 50% HP beat 60% and 70% (76% vs 70% vs 58%) | ❌ off target | v17 policy search |
| Choices | Rest: always heal vs always tinker | within 5 points of each other | 66% vs 63% | ✅ on target | v16 (300 runs each) |
| Choices | Run styles (route, rest, Workshop) | no style more than 5 points above the base | best: seek elites, always heal (+5) | ✅ on target | v15 |
| Content | One part pick (win-rate points over the starter, fights from 30 HP) | +3 to +10; combo enablers (Spring, Mirror, Loader) may be slightly negative alone | Magnet +9.5, Slider +8.1, Primer +7.7, Assembly +6.7, Amplifier +5.5, Coupler +5.4, Coolant +4.4, Hammer +3.8 | ✅ on target | v15 |
| Content | One combo-enabler pick (same measure) | −5 to +3 | Mirror −1.7, Loader −2.8, Spring −3.5 | ✅ on target | v15 |
| Content | One common/uncommon attachment (HP kept per fight) | +2.5 to +4 | Heat Sink +3.6, Coil +3.5, Bracing +3.5, Polish +3.4, Counterweight +3.3, Sharpened +3.0, Echo +3.0, Clamp +2.8, Feeder +2.8 | ✅ on target | v16/v17 (Coil 6, Polish +40%, Echo now uncommon) |
| Content | One rare attachment (HP kept per fight) | +4 to +6 | Governor +6.5 | ❌ off target | v16 |
| Content | One machine upgrade (run clear points, started with it) | +7 to +16, rising with price (Flywheel 70, Bigger Gear 75, Heat Housing 85, Extra Hands 90) | Bigger Gear +18, Flywheel +16, Extra Hands +14, Heat Housing +11 | ⚠️ partly off | v16 |
| Content | Strongest single turn (any combo) | about half the boss's HP (≤ 55; a few over is accepted) | 60 | ✅ on target | v15 (Echo Coupler + Hammers) |
| Economy | Attachments per run | 2–4 | 3.9 | ✅ on target | v17 |
| Economy | Machine upgrades per run | about 1 | 2.0 | ❌ off target | v17 |
| Economy | Cogs unspent when reaching the boss | under 40 | 63 | ❌ off target | v17 |
| Fun (simulator) | Fight length (turns): normal / boss | 4–8 / 6–12 | 6.3 / 7.6 | ✅ on target | v17 |
| Fun (simulator) | Close wins (≤ 25% HP left): normal fights | 5–15% (rarely a scare) | 3% | ❌ off target | v17 |
| Fun (simulator) | Close wins: elites / bosses | 15–30% / 30–50% | 20% / 45% | ✅ on target | v17 |
| Fun (simulator) | Combo turns (4+ triggers) | 10–30% of turns | 18% | ✅ on target | v17 |
| Fun (simulator) | Choice weight: best plan minus the median plan | 6 or more (choosing well matters) | 7.3 | ✅ on target | v17 |
| Fun (simulator) | Turns with only one good option | under 25% (rarely forced) | 16% | ✅ on target | v17 |
| Fun (simulator) | Build variety (entropy of the most-copied added part, 0–1) | 0.75 or more | 0.64 | ❌ off target | v17 (Magnet in 88 of 150 runs) |
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
| **Boiler** | rare | 65 | 2 | Deal 3 damage, +2 per point of Heat (after its own). +1 Heat. |

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
| **Overdrive** | rare | any part | 90 | Its damage and Block +50% (adds to Amplifiers). | +5.0 (Hammer) |
| **Kickback** | rare | any part | 90 | After it triggers, the part that would come up next this turn triggers too (the gear doesn't turn). | +4.0 (Hammer) |

## Enemies

A run has 3 acts. Within an act, enemies grow: HP and attacks × act strength × (1 + 0.3 × stop/9). Act strength: act 1 ×1.0, act 2 ×1.35, act 3 ×1.7. In acts 2 and 3 normal enemies and elites are **veterans** (placeholders until themed districts exist): the act-1 enemies at that strength with extra armor (act 1 +0, act 2 +1, act 3 +2). Elites are fought at ×0.9 on top. Each fight's HP also rolls ±3. Cogs vary ±10%.

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

Bosses by act: act 1: clock_tower or pendulum; act 2: furnace or dismantler; act 3: iron_colossus.

## Machine upgrades

Permanent upgrades with levels. A run starts by choosing 1 of 3, and every boss but the last gives 1 of 3 you don't have (its exclusive reward). Workshops sell level-ups for the upgrades you have; nothing else gives new upgrades.

| Upgrade | Per level | Max level |
|---|---|---|
| **Flywheel** | +1 Crank Power per turn | 2 |
| **Heat Housing** | +2 Heat before Overheat | 2 |
| **Extra Hands** | +1 install per turn | 2 |
| **Bigger Gear** | 8 gear slots instead of 6, and +1 Crank Power to turn it | 1 |
| **Reinforced Frame** | +8 max HP | 3 |
| **Wide Hopper** | +1 part offered (and shown) each turn | 2 |
| **Cooling Fins** | 1 Heat drains away at the start of each turn | 2 |

Level-up prices: level 2 90 cogs, level 3 130 cogs (placeholders until the economy is tuned across all acts).

## Run

| Rule | Value |
|---|---|
| Acts | 3; each is 9 door choices, then the act's boss (all bosses shown at the start) |
| Doors | stops 1-2 are fights; then 3 doors weighted fight 4, elite 2, workshop 1.5, rest 1.5; the last stop offers a rest site or a Workshop |
| After a win | heal 7 HP, loot cogs, pick 1 of 3 parts (or scrap for 10 cogs, or skip) |
| Between acts | the boss's exclusive reward (1 of 3 machine upgrades), then half of the missing HP heals |
| Part reward tiers (weights) | act 1: common 5, uncommon 4, rare 1; act 2: common 3, uncommon 4, rare 2; act 3: common 2, uncommon 4, rare 3 |
| Elite loot | a part from the uncommon/rare tiers (rares ×2 as likely), and 1 of 3 uncommon/rare attachments (rare weight 3 against 3 per uncommon); no machine upgrades |
| Rest site | heal 8, or tinker: take both offered common attachments |
| Workshop | 3 parts, 2 uncommon/rare attachments, level-ups for your machine upgrades; repair 15 HP for 25; remove a part for 40 (+15 each time) |

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

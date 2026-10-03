# Clockwork — Rough Rules

**Type A: random run (roguelike, engine-building)**
You're a tinkerer fighting through a mechanical city. Instead of playing cards from your hand, you install **parts** on a rotating **gear**. Each turn the gear turns, and whatever reaches the top **triggers**. Placement and timing are everything.

---

## 1. Basics

| Item | Starting value |
|---|---|
| HP | 55 |
| Gear size | 6 slots (like a clock with 6 positions) |
| Parts drawn per turn | 3 |
| Parts you can install per turn | 2 |
| Crank Power per turn | 2 |
| Starting bag | 8 parts (4 Strikers, 3 Plates, 1 Spring) |

---

## 2. Turn structure

1. **Draw** 3 parts from your bag.
2. **Install** up to 2 parts into empty slots. (You may also **replace** an installed part: the old one goes to the discard.)
3. **Crank:** the gear rotates **1 step clockwise for free**. The part now at the top (**Trigger Point**) activates.
4. **Extra cranks:** spend 1 Crank Power per extra step (each step triggers the new top part). You can also spend 1 to crank **backwards** once.
5. Unused parts in hand are discarded. Enemies act.

**Parts stay on the gear between turns.** Over the fight you are building a machine.

---

## 3. Heat
- Every trigger adds **1 Heat** to the machine.
- At **10 Heat** → **Overheat**: nothing triggers next turn and Heat resets to 0.
- Coolant parts lower Heat. Some powerful parts add extra Heat.

---

## 4. Part types

| Part | Trigger effect | Notes |
|---|---|---|
| **Striker** | Deal 6 damage | Basic |
| **Plate** | Gain 6 Block | Basic |
| **Spring** | Crank again for free | Chains triggers! +1 Heat |
| **Mirror** | Copy the effect of the part directly **opposite** on the gear | Great with big parts |
| **Amplifier** | Passive: the parts **next to it** get +50% | Doesn't trigger itself |
| **Coupler** | Trigger both neighbors | 2 triggers = 2 Heat |
| **Loader** | Install a random part from your bag into an empty slot | Engine growth |
| **Coolant** | Remove 3 Heat | Keeps long combos going |
| **Hammer** | Deal 15 damage, +2 Heat | Big hit |
| **Magnet** | Pull the part 2 slots away next to this one | Rearranges the gear |

---

## 5. Enemies
Enemies show intent. Some target your machine instead of your HP:
- **Jam:** a slot is disabled for 2 turns (the part stays but can't trigger).
- **Rust:** a part permanently loses 2 power.
- **Unscrew:** removes a part back to your bag.
- **Wind Back:** turns your gear 1 step counter-clockwise.

---

## 6. The run
- 3 districts (Brass Quarter, Steam Docks, Clock Tower), branching maps.
- Rewards after fights: pick 1 of 3 random parts.
- **Workshop** (shop/rest): buy parts, upgrade parts, or buy machine upgrades:
  - **Bigger Gear:** 8 slots (more space, but slower to cycle back to key parts).
  - **Second Gear:** it meshes with your first gear. When Gear A cranks clockwise, Gear B cranks **counter-clockwise**, and both Trigger Points fire.
  - **Flywheel:** +1 Crank Power per turn.

### Blueprints (relics)
- **Oiled Axle:** the first Spring each turn adds no Heat.
- **Double Pointer:** there are two Trigger Points (top AND bottom).
- **Salvage Kit:** when a part is destroyed, gain 1 Crank Power.

---

## 7. Bosses

| Boss | Twist | Counter ideas |
|---|---|---|
| **The Jammer** | Jams 2 random slots every turn. | Duplicates of key parts, Magnet to move parts out of jammed slots |
| **Reverse Engine** | On odd turns, your gear spins **counter-clockwise**. | Symmetrical layouts, Mirrors, backward crank |
| **Clock Tower** | No regular attack. **Every 4th crank** of the fight (Springs count) it strikes at once for heavy damage, after the part that comes up triggers; your current Block absorbs it. *(Was: 12 total cranks, then instant loss.)* | Plates timed to come up on the strike, Block engines, fewer but bigger cranks |

---

## 8. Example combo
Gear (clockwise): `[Spring] [Spring] [Hammer] [Amplifier] [Plate] [Coolant]`
- Crank → Spring triggers → free crank → Spring → free crank → **Hammer** (15 × 1.5 from Amplifier = 22 damage).
- 1 free crank did 3 triggers. Heat: +1 (Spring) +2 (2nd Spring in the chain) +2 (Hammer) = 5.
- Next turn: Crank to Amplifier (nothing), spend power → Plate, → Coolant (Heat back down).

---

## 8b. Balance rules (to keep combos under control)
Clockwork is hard to balance, mainly because of **infinite loops** (Springs cranking into more Springs). These guard rails keep it fair without killing combos:

1. **Each part can trigger at most 2 times per turn.** After that it's "spent" (shown greyed out) until next turn.
2. **Trigger Limit:** max **8 triggers per turn** total. Relics can raise it by 1–2, never unlimited.
3. **Springs add Heat** (+1), and a 2nd Spring in the same chain adds +2 instead. Long spring chains overheat quickly.
4. **Mirror can't copy a Mirror**, and **Coupler can't trigger a Coupler** (stops copy loops).
5. **Big numbers go on slow parts:** high-damage parts (Hammer) should cost Heat or need a set-up turn.
6. **Enemies scale with machine size:** later enemies have more Jam/Rust abilities, so huge engines are still under pressure.

### How to test it (paper prototype)
- Draw a circle with 6 slots on paper, and write parts on small paper scraps.
- Play 5 fights against a simple enemy ("Attack 8 every turn, 60 HP").
- Write down: damage per turn, and how many turns until a loop appears.
- If any combo does more than **~3× the normal damage** early on, change the numbers or add a limit.

---

## 9. Where the creativity is
- Your deck is a **physical layout**: the same parts do different things depending on where they are.
- Timing puzzles: when do I let the big part reach the top?
- Random parts + bosses that attack the machine make you redesign on the fly.

---

## 10. Changes from the first version
- Added balance rules (trigger limits, Spring Heat, no copy loops) and a paper-prototype test plan.

# Clockwork: Ideas for a More Immersive Hours Map

The v19 hours map works as a budget ("spend 12 hours, then the boss"), but it plays like a spreadsheet: a grid of node icons with price tags. These ideas aim to make time feel like the city's own clockwork, something you live in, not a counter you spend. The length can be anything (12 hours, 24 hours, a night, a week).

**What the numbers say any rework must fix** (AI-Playtesting-Roadmap.md, Results v19):
- **Healing:** on the door map runs rest about 7 times; in a district only 2–4. With today's enemies that alone drops the casual clear rate from 38% to 10–15%.
- **Income:** 12 hours buys about 25% less than a door act; 16 hours matches it.
- **Skipping:** a planning player avoids elites and fights. Time should make fights feel worth taking, not just cost hours.

Setting reminders (Rules.md): a mechanical city of districts (Brass Quarter, Steam Docks, Clock Tower); you're a tinkerer with a hand-cranked machine; bosses include the Clock Tower and the Pendulum.

Each idea lists **how it plays**, **why it's immersive**, and **what it does to the numbers**. Ideas marked ★ directly address a v19 problem.

---

## A. What "time" is

| # | Idea | How it plays | Why it's immersive | Effect |
|---|---|---|---|---|
| A1 | **A day in the city (24 hours, dawn to dawn)** | The act is one full day. Dawn, day, dusk and night each change the district (see section C). The boss is the hour the district's master clock strikes its last chime. | You live through a day; the light, sounds and people change around you. | More hours to plan with, but split into phases that each feel different. |
| A2 | **Each act zooms into the clock** | Act 1 is measured in hours across a day in the Brass Quarter; act 2 in minutes across the last hour, inside the Steam Docks' engine halls; act 3 in seconds, inside the Clock Tower's mechanism. Same rules, new units and art. | Escalation you can feel: the closer to the heart of the clock, the finer the time. | No balance change; pure framing. Tells the story without cutscenes. |
| A3 | **Your mainspring** | Your machine runs on a mainspring wound before the run. Hours are its turns: every node unwinds it, and the boss attacks when the city's spring and yours line up. Winding at an inn (rest) rewinds you, not the city. | Time is part of your machine, like Heat and Crank Power. | Lets "rest" and "time" be one system (see D1). |
| A4 | **Shifts and bells** | The city works in shifts marked by bells (e.g. every 3 hours). Things happen on the bell: shops change stock, patrols change, the tram departs. | The world has a rhythm you learn and exploit. | Gives the hours a structure without more rules per node. |

## B. The shape of the map

| # | Idea | How it plays | Why it's immersive | Effect |
|---|---|---|---|---|
| B1 | **The district is a clock face** | 12 sectors in a ring around the boss's tower at the centre, numbered like hours. Sector *n* is "where the hour hand points at *n* o'clock". You walk around the face. | You're literally walking on the clock. Midnight is a place as well as a time. | Readable: you see how far midnight is by looking at the dial. |
| B2 | **The hour hand sweeps the map** ★ | On a clock-face district the hour hand moves one sector per hour. Nodes under the hand are **struck**: closed, or an elite patrol stands there. Behind the hand, nodes **reset** (new loot, new enemies). | The clock is an enemy you dodge and race. | Creates timing puzzles; fresh nodes behind the hand ease the "only 2–3 rest sites" problem. |
| B3 | **The district turns like the gear** | Every bell, the outer ring of the district rotates one notch (the original clock-ring idea, Run-Design B). Streets realign; a Workshop that was across the city is suddenly next door. | Mirrors the core mechanic: plan around a rotating board, just like your gear. | Adds route planning; needs good visuals. |
| B4 | **Clockwise is the grain** | Moving clockwise around the district costs 1 hour per step; against the grain costs 2. | Same feeling as cranking your gear: going backward costs more. | Shapes routes simply; one rule to read. |
| B5 | **Trams on a timetable** | Brass tram lines cross the district. A tram leaves a stop every 3 hours and crosses fast (1 hour across the city). Miss it and you walk. | Cities run on schedules; catching the tram feels clever. | A cheap way to make far-away rest sites and Workshops reachable. |
| B6 | **Streets lit by the lamplighter** | At dusk the lamplighter walks a route; lit streets show what's inside, dark ones only show a silhouette (fight? shop?) until you're next to them. | Night is mysterious and a bit scary. | Adds a light gamble at night (see C2), without hiding everything. |

## C. Time of day changes the district

| # | Idea | How it plays | Why it's immersive | Effect |
|---|---|---|---|---|
| C1 | **Opening hours** ★ | Workshops are open from 6 to 18; inns serve rest from 18 to 6; the scrap market opens at dawn. A closed node shows when it opens. | Shops and inns behave like real places. | Shapes the day: shop in daylight, rest at night. Rest is guaranteed to be available when it's most needed. |
| C2 | **Night shift** ★ | After dark, enemies are the night watch: tougher (+1 armor or +20%) but carry more cogs and rarer loot. Elites prowl only at night. | Risk feels like a choice of *when*, not just *where*. | Gives fights a reason to be taken: the high-risk, high-return hour. Makes elites a night-time temptation. |
| C3 | **Rush hour** | At 8 and 17 the streets are crowded: walking costs double, but pickpocket-style enemies are everywhere (easy, low loot). | The city feels busy and alive. | Small spice; optional. |
| C4 | **The noon market** | At exactly noon the market square sells at half price for one hour. | A city event you plan your morning around. | A pull toward the centre of the map at the middle of the day; helps spending. |
| C5 | **Weather from the boilers** | The Steam Docks' boilers vent on a schedule. Venting hours fill streets with steam: +2 Heat at the start of fights there, but hidden routes open. | Each district has its own "weather" that fits its theme. | District-specific variety; connects to the Heat mechanic. |

## D. Rest and healing in time ★

| # | Idea | How it plays | Why it's immersive | Effect |
|---|---|---|---|---|
| D1 | **Sleep instead of resting** ★ | At an inn you choose how long to sleep: 1 hour (nap, small heal), 4 hours (good heal) or until dawn (full heal and a free tinker). Time passes for the city while you sleep. | Sleeping costs the night; you wake to a changed district. | Healing becomes a real time trade instead of a scarce node. Fixes the main v19 problem: heal amount scales with hours, not node count. |
| D2 | **Camp anywhere** | You can stop on any visited node and camp: 2 hours, a small heal, no tinkering. Inns heal more. | You're a wandering tinkerer; you can sit down and patch yourself up. | A floor on healing; makes routes less punishing when rest sites are far. |
| D3 | **Repairs take time** | Workshop repairs cost hours as well as cogs (1 hour per 10 HP). | Fixing a machine takes time, like in real life. | Another time-for-HP trade; lets cogs and time both matter. |
| D4 | **Tinkering takes time** | Attaching an attachment, swapping parts or installing a machine upgrade costs 1 hour. Free at an inn overnight. | The tinkerer's craft is part of the clock. | Makes building feel deliberate; small balance cost. |

## E. Earning, buying and saving time

| # | Idea | How it plays | Why it's immersive | Effect |
|---|---|---|---|---|
| E1 | **Work a shift** | At a Workshop you can spend hours repairing other people's machines for cogs (e.g. 1 hour = 10 cogs). | You're a tinkerer by trade; this is your job. | Lets non-fighters earn; gives the hours a cogs value, which helps price tuning. |
| E2 | **Commissions** | Order a specific part or attachment at a Workshop. It's ready at a given hour; pick it up then (Run-Design's planned "commissions"). | Waiting for an order to be done is very "craftsman". | Turns time into planned rewards; replaces random shop luck. |
| E3 | **Buy time** | Rare items move the clock: an **Escapement** attachment (+1 hour per act), a **Stopwatch** consumable (freeze time for one node), bribing the bell-ringer (cogs for +1 hour). Answers Run-Design's open question "can parts buy time?". | Bending the city's clock is the tinkerer's ultimate trick. | A reward type elites can carry that is valuable to everyone (helps the "elites are skipped" problem). |
| E4 | **Fights cost less time than travel** | A fight on your route takes 1 hour; going out of your way costs the hours. | Fights become things you run into, not destinations you pay for. | Makes fighting cheap and skipping costly; fixes the "planner skips fights" finding. |
| E5 | **Hurry bonus** ★ | Cogs and loot are higher the earlier in the day you win (dawn fights pay +50%, dusk +0%). | The early bird; the city rewards those who get going. | Pushes players to fight early and rest late, a natural day shape. |

## F. Midnight and the boss

| # | Idea | How it plays | Why it's immersive | Effect |
|---|---|---|---|---|
| F1 | **The boss is coming** ★ | The boss is a token that moves across the district each hour, getting closer. You see it coming. At midnight it reaches you wherever you are. | Dread: you watch the threat approach. | Lets you choose where to meet it (next to an inn, after a Workshop). |
| F2 | **Sabotage to delay it** | Some elite nodes are the boss's lieutenants or machinery (a bell rope, a boiler valve). Beating one delays the boss 2 hours, or weakens it. | Elites matter to the story of the act. | Gives elites a reward everyone wants (time or a weaker boss) and fixes "skip elites". |
| F3 | **Early bird: ambush the boss** ★ | Go to the boss before midnight and you get an ambush: its first turn is skipped, or it starts damaged by 2% per hour left. | Striking first is smart, not just brave. | Rewards efficient days; answers "what if I skip everything?" (you still lose the loot). |
| F4 | **Overtime instead of a hard stop** | Midnight doesn't force the boss. Instead, every hour past midnight the boss grows stronger (+5%) and the district goes dark (night shift for all nodes). | No sudden cut-off; the pressure mounts. | Softer budget; needs tuning so it isn't always worth staying. |
| F5 | **The Clock Tower's chime** | In act 3 (the Clock Tower), the chime that strikes in the boss fight (every 4th crank) is the same bell that marks the hours on the map. Hours you've spent appear as pre-rung chimes. | Map and fight share one clock. | Ties the map to an existing boss mechanic. |

## G. Presentation (cheap, high impact)

- **A pocket watch as the UI:** the hours left are shown on a brass pocket watch the tinkerer pulls out; the hand ticks when you move.
- **Light and sound:** the district changes colour from dawn to night; ticking gets louder near midnight; bells ring on each shift.
- **People with schedules:** a few named NPCs (the clockmaker, the scrap dealer, the bell-ringer) are at different places at different hours. Meeting them gives a unique offer.
- **A logbook:** after each act a one-line diary entry per hour ("06:00 — fixed a jammed press for 20 cogs. 09:00 — ambushed by a Saboteur.") turns the route into a story.

---

## Packages (ideas that fit together)

| Package | Ideas | Feel | Fixes |
|---|---|---|---|
| **1. A Day in the Brass Quarter** | A1 day, C1 opening hours, C2 night shift, D1 sleep, E5 hurry bonus, F3 ambush | Day: shop and fight; night: dangerous loot or sleep. Most "lived-in". | Healing (sleep), skipping (hurry bonus, ambush), elites (night temptation). |
| **2. The Clock Face** | B1 clock-face district, B2 sweeping hand, B4 clockwise grain, F1 boss coming | The map is a clock; you race the hand. Most "mechanical". | Healing (nodes reset behind the hand), route variety. Needs the most visuals. |
| **3. The Tinkerer's Trade** | A3 mainspring, D1 sleep, D4 tinkering takes time, E1 work a shift, E2 commissions | Time is your working day as a craftsman. Most about building. | Income (shifts), healing (sleep); quieter, less danger. |
| **4. The Countdown** | F1 boss coming, F2 sabotage, F3 ambush, F4 overtime, E3 buy time | A tense race against the act's boss. Most "story". | Elites (sabotage), skipping (ambush), a softer midnight. |
| **5. Zoom** | A2 hours → minutes → seconds, plus any one package | Framing for the whole run. | No balance change; combines with anything. |

**Recommendation:** **package 1 with A2's framing**, borrowing **F2 (sabotage)** from package 4.
- It fixes all three v19 problems with rules players already understand: the time of day, opening hours, sleeping.
- It needs no new map shape, so the simulator's district can be reused.
- Sabotage gives elites a reason to exist that the expert planner will value, without changing their loot.
- Package 2 (the clock face) is the most distinctive but carries the most design and art risk; it could come later as the act-3 map inside the Clock Tower.

**Simulator checks before choosing:**
- Sleep (D1) with 1 / 4 / until-dawn options against today's 8-HP rest: does the casual clear rate on the hours map return to door levels (about 38%)?
- Night shift (C2): does a planning player fight at night when the loot is better, and does it cost runs when taken at low HP?
- Hurry bonus and ambush (E5, F3): does skipping fights stop being the best plan?
- Income per act against the door map, so prices can be set on the map that ships.

**Questions for the designer:**
1. Which package (or mix) feels most like Clockwork to you?
2. Should a day be 12 or 24 hours? 24 fits A1 and opening hours better; 12 fits a clock face (B1).
3. Should midnight be a hard stop (the boss arrives) or overtime (F4)?
4. Should acts keep the same length of day, or zoom (A2)?

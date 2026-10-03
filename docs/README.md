# Clockwork playtest page

A browser version of the fight simulator for human playtesting. It runs the **same Python
simulator** as the AI agents (through [Pyodide](https://pyodide.org)), so the rules always match.

- `index.html`, `style.css`, `app.js`: the page.
- `play.py`: bridge between the page and the simulator.
- `py/`: copy of the simulator modules. After changing rules in `sim/clockwork/`, run
  `python sim/build_web.py` (a unit test fails if this copy is stale).

**Publishing:** repository Settings → Pages → "Deploy from a branch" → pick the branch and the
`/docs` folder. The page appears at `https://2023techacc.github.io/clockwork/`.

**Local test:** `cd docs && python -m http.server`, then open http://localhost:8000.

**Modes:** *Run* (default): dummy → spiker → saboteur → enrager → Clock Tower with HP carried over,
10 HP healed after each win, and an optional pick-1-of-3 part reward (or skip) after each fight.
*Single fight*: any deck against any enemy at full HP.

Playtesters can copy a fight report (setup, result and every action, so each fight can be replayed
exactly in the simulator; run reports include every fight and reward pick) or open a pre-filled GitHub issue from the result screen.

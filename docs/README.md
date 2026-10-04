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

**Modes:**
- *Run* (default): one district of door choices (fight, elite, Workshop, rest), then the Clock Tower. HP carries over, enemies carry cogs, and attachments go into an inventory and can be attached to parts between fights. It uses the simulator's own run logic (`clockwork/run_mode.py`).
- *Single fight*: any deck against any enemy (including the elites) at full HP.

Playtesters can copy a fight report (setup, result and every action, so each fight can be replayed
exactly in the simulator; run reports include every fight and reward pick) or open a pre-filled GitHub issue from the result screen.

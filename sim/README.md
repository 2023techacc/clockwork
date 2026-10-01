# Clockwork simulator

Headless fight simulator for the AI playtesting roadmap (`../AI-Playtesting-Roadmap.md`).
Python 3.10+, standard library only. Rules follow "Simulator defaults v1" in `../Rules-Decisions.md`;
every number and on/off rule lives in `clockwork/config.py`.

```
cd sim
python -m unittest discover -s tests -t .                       # rules tests + random-play fuzz
python -m clockwork.run --deck starter --enemy dummy --fights 1000
python -m clockwork.run --deck copy_loop --enemy saboteur --seed 3 --trace   # one fight, full log
```

| File | |
|---|---|
| `clockwork/config.py` | `RulesConfig`: numbers, §8b caps (off = on hold), safety limits |
| `clockwork/parts.py` | part stats |
| `clockwork/engine.py` | state, legal actions, turn flow, trigger resolution |
| `clockwork/enemies.py` / `decks.py` | test enemies and decks (Experiment setup v1) |
| `clockwork/agents/` | agents (`act(state, legal_actions) -> action`) |

Agent API: `new_fight(...)`, `legal_actions(s)`, `apply(s, action)`, `s.clone()`, `summary(s)`.
In `render()`/traces the gear is shown from the Trigger Point onward, in the order forward cranks bring parts up.

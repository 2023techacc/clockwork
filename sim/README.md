# Clockwork simulator

Headless fight simulator for the AI playtesting roadmap (`../AI-Playtesting-Roadmap.md`).
Python 3.10+, standard library only. Rules follow "Simulator defaults v1" in `../Rules-Decisions.md`;
every number and on/off rule lives in `clockwork/config.py`.

```
cd sim
python -m unittest discover -s tests -t .                       # rules tests + random-play fuzz
python -m clockwork.run --deck starter --enemy dummy --fights 1000
python -m clockwork.run --deck copy_loop --enemy saboteur --seed 3 --trace   # one fight, full log
python -m clockwork.run --agent greedy --deck starter --enemy enrager --fights 200
python -m clockwork.experiment --agents random greedy --fights 1000 --out results   # full matrix, ~8 min on 4 cores
python -m clockwork.loopfinder --deck big_hit --heat 0 5 --top 10                  # strongest single turns
```

| File | |
|---|---|
| `clockwork/config.py` | `RulesConfig`: numbers, §8b caps (off = on hold), safety limits |
| `clockwork/parts.py` | part stats |
| `clockwork/engine.py` | state, legal actions, turn flow, trigger resolution |
| `clockwork/enemies.py` / `decks.py` | test enemies and decks (Experiment setup v1) |
| `clockwork/agents/` | agents (`act(state, legal_actions) -> action`): random, greedy |
| `clockwork/search.py` | every way to play out the current turn (used by greedy and the loop finder) |
| `clockwork/experiment.py` | decks x enemies x agents matrix, CSV + win-rate table |
| `clockwork/loopfinder.py` | best single turn for every gear layout of a deck |

Agent API: `new_fight(...)`, `legal_actions(s)`, `apply(s, action)`, `s.clone()`, `summary(s)`.
In `render()`/traces the gear is shown from the Trigger Point onward, in the order forward cranks bring parts up.

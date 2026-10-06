"""Route planning for the expert run policy: forecast what fights will cost, then plan HP to the boss.

The casual policy (run_policy.DEFAULT_STYLE) uses fixed HP thresholds. The expert looks ahead instead:
- **Forecasts:** it plays the fights it could meet next in its head (quick greedy simulations with the
  current deck and machine, against every normal enemy, the elites and the act's boss at their current
  strength) and scales the HP they cost by FORECAST_SCALE, since the expert plays better than greedy.
- **HP plan:** for each option it projects the HP left when the boss arrives, assuming every later stop
  is a normal fight (the safe case). It takes an option only if that projection still covers the boss
  with a margin.

Map-agnostic: the door map and the hours map both ask `projected_boss_hp(run, option, fights_left)`.
"""
import random
import statistics

from .engine import apply, legal_actions, new_fight
from .enemies import ELITES, NORMAL
from .run import make_agent

FORECAST_AGENT = "greedy"
FORECAST_FIGHTS = (4, 3, 3)  # simulated fights per forecast: normal enemies, elites, the act's boss
FORECAST_SCALE = 0.7        # expert HP cost / greedy HP cost (v18 3-act runs: 8.4/13.4, 20.6/27.6)
BOSS_MARGIN = 1.5           # arrive at the boss with this many times its forecast cost (v19 search)...
BOSS_EXTRA = 5              # ...plus this much HP


def _cost(run, enemy, node, seeds, progress=None):
    """HP lost per fight (from full HP; a loss counts as all of it), one entry per seed."""
    spec = run.enemy_spec(enemy, node, progress)
    rules = run.rules()
    out = []
    for seed in seeds:
        s = new_fight(run.fight_deck(), spec, seed=seed, rules=rules, start_hp=rules.player_hp)
        agent = make_agent(FORECAST_AGENT, seed)
        while s.result is None:
            apply(s, agent.act(s, legal_actions(s)))
        out.append(rules.player_hp - (s.hp if s.result == "win" else 0))
    return out


def forecast(run, scale=FORECAST_SCALE):
    """{"fight": mean cost, "elite": mean cost, "boss": mean cost, "elite_worst": the worst elite seen}
    for the current deck, machine and act. Refreshed every 3 stops and in each act (the deck changes
    slowly; forecasting is the expensive part of an expert run)."""
    key = (run.act, run.stop // 3)
    cache = run.__dict__.setdefault("_forecast", {})
    if key not in cache:
        rng = random.Random(run.seed * 7 + run.act * 101 + run.stop)
        n_fight, n_elite, n_boss = FORECAST_FIGHTS
        fight = [_cost(run, rng.choice(NORMAL), "fight", [rng.randrange(10 ** 9)])[0] for _ in range(n_fight)]
        elite = [_cost(run, rng.choice(ELITES), "elite", [rng.randrange(10 ** 9)])[0] for _ in range(n_elite)]
        boss = _cost(run, run.boss, "boss", [rng.randrange(10 ** 9) for _ in range(n_boss)])
        cache.clear()
        cache[key] = {"fight": statistics.mean(fight) * scale, "elite": statistics.mean(elite) * scale,
                      "elite_worst": max(elite) * scale, "boss": statistics.mean(boss) * scale}
    return cache[key]


NEED_CAP = 0.85             # never plan for more than this share of max HP (else it would only rest)


def boss_need(f, run, margin=BOSS_MARGIN, extra=BOSS_EXTRA):
    return min(f["boss"] * margin + extra, NEED_CAP * run.max_hp())


def projected_boss_hp(run, option, fights_left, f=None, heal=None):
    """HP when the boss arrives if `option` is taken now and then `fights_left` normal fights follow.
    option: "fight" | "elite" | "rest" (heal) | "tinker" | "workshop" | "repair:<hp>"."""
    f = f or forecast(run)
    heal = run.base_rules.heal_between_fights if heal is None else heal
    from .run_mode import REST_HEAL
    top = run.max_hp()
    hp = run.hp
    if option in ("fight", "elite"):
        hp = min(top, hp - f[option] + heal)
    elif option == "rest":
        hp = min(top, hp + REST_HEAL)
    elif option.startswith("repair:"):
        hp = min(top, hp + int(option.split(":")[1]))
    for _ in range(max(0, fights_left)):
        hp = min(top, hp - f["fight"] + heal)
    return hp

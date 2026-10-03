"""Mini-run: a sequence of fights with HP carried over and a small heal after each win.

    python -m clockwork.campaign --agent mcts@50 --runs 100

Default route: dummy, spiker, saboteur, enrager, then the clock_tower boss.
"""
import argparse
import os
import statistics
from concurrent.futures import ProcessPoolExecutor

from .config import DEFAULT_RULES
from .decks import DECKS
from .engine import apply, legal_actions, new_fight
from .run import make_agent

ROUTE = ["dummy", "spiker", "saboteur", "enrager", "clock_tower"]


def run_campaign(deck, agent_name, seed, route=ROUTE, rules=DEFAULT_RULES):
    """Returns (fights won, HP before each fight, HP after the last fight played)."""
    hp, before = rules.player_hp, []
    for i, enemy in enumerate(route):
        before.append(hp)
        s = new_fight(DECKS[deck], enemy, seed=seed * 100 + i, rules=rules, start_hp=hp)
        agent = make_agent(agent_name, seed * 100 + i)
        while s.result is None:
            apply(s, agent.act(s, legal_actions(s)))
        if s.result != "win":
            return i, before, 0
        hp = min(rules.player_hp, s.hp + rules.heal_between_fights)
    return len(route), before, s.hp


def _block(args):
    deck, agent, seeds = args
    return deck, [run_campaign(deck, agent, seed) for seed in seeds]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="mcts@50")
    ap.add_argument("--runs", type=int, default=100)
    ap.add_argument("--decks", nargs="+", default=list(DECKS), choices=list(DECKS))
    args = ap.parse_args(argv)
    tasks = [(d, args.agent, range(lo, min(lo + 10, args.runs))) for d in args.decks
             for lo in range(0, args.runs, 10)]
    res = {}
    with ProcessPoolExecutor(os.cpu_count()) as pool:
        for deck, out in pool.map(_block, tasks):
            res.setdefault(deck, []).extend(out)
    print(f"{args.agent}: route {' > '.join(ROUTE)}, heal {DEFAULT_RULES.heal_between_fights} after each win")
    print(f"{'deck':13s}{'cleared':>8s}  " + "".join(f"{'reach ' + e[:7]:>15s}" for e in ROUTE)
          + f"{'HP at boss':>11s}")
    for deck, out in res.items():
        n = len(out)
        reach = [sum(o[0] >= i for o in out) / n for i in range(len(ROUTE))]
        boss_hp = [o[1][-1] for o in out if len(o[1]) == len(ROUTE)]
        cleared = sum(o[0] == len(ROUTE) for o in out) / n
        print(f"{deck:13s}{cleared:8.0%}  " + "".join(f"{r:15.0%}" for r in reach)
              + f"{statistics.mean(boss_hp) if boss_hp else 0:11.1f}")


if __name__ == "__main__":
    main()

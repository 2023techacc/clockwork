"""Sweep a part's stats and measure what one copy of it is worth.

For every combination of values, plays a probe deck (starter plus that part) against
every enemy and reports its mean win rate minus the plain starter deck's.

    python -m clockwork.sweep --part Hammer --set damage 8 10 12 --set extra_heat 2 3 4 \\
        --deck plus_hammer --agent mcts@50 --fights 100
"""
import argparse
import itertools
import os
from concurrent.futures import ProcessPoolExecutor

from .config import RulesConfig
from .enemies import ENEMIES
from .run import make_agent, play


def _cell(args):
    agent, deck, enemy, seeds, overrides = args
    rules = RulesConfig(part_overrides=overrides)
    wins = dmg = turns = 0
    for seed in seeds:
        s = play(deck, enemy, seed, make_agent(agent, seed), rules=rules)
        wins += s.result == "win"
        dmg += sum(s.stats.damage_by_turn)
        turns += s.turn
    return deck, overrides, enemy, wins, len(seeds), dmg, turns


def run(pool, agent, deck, overrides, fights, enemies, block=25):
    tasks = [(agent, deck, e, range(lo, min(lo + block, fights)), overrides)
             for e in enemies for lo in range(0, fights, block)]
    per_enemy, dmg, turns = {}, 0, 0
    for _, _, e, w, n, d, t in pool.map(_cell, tasks):
        a, b = per_enemy.get(e, (0, 0))
        per_enemy[e] = (a + w, b + n)
        dmg, turns = dmg + d, turns + t
    rates = [w / n for w, n in per_enemy.values()]
    return sum(rates) / len(rates), dmg / turns


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", required=True)
    ap.add_argument("--set", nargs="+", action="append", required=True, metavar=("FIELD", "VALUE"))
    ap.add_argument("--deck", required=True)
    ap.add_argument("--baseline", default="starter")
    ap.add_argument("--agent", default="mcts@50")
    ap.add_argument("--fights", type=int, default=100)
    ap.add_argument("--enemies", nargs="+", default=list(ENEMIES))
    args = ap.parse_args(argv)

    fields = [(f[0], [int(v) for v in f[1:]]) for f in args.set]
    with ProcessPoolExecutor(os.cpu_count()) as pool:
        base, base_dpt = run(pool, args.agent, args.baseline, (), args.fights, args.enemies)
        print(f"{args.baseline}: win {base:.0%}, {base_dpt:.1f} damage/turn", flush=True)
        for values in itertools.product(*(vals for _, vals in fields)):
            overrides = tuple((args.part, f, v) for (f, _), v in zip(fields, values))
            rate, dpt = run(pool, args.agent, args.deck, overrides, args.fights, args.enemies)
            label = ", ".join(f"{f}={v}" for (f, _), v in zip(fields, values))
            print(f"{args.part} {label}: win {rate:.0%} ({(rate - base) * 100:+.0f} points), "
                  f"{dpt:.1f} damage/turn", flush=True)


if __name__ == "__main__":
    main()

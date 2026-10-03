"""Retune enemy difficulty automatically.

For each enemy, scales HP and attacks by one factor (bisection) until a reference agent's
mean win rate across the test decks hits the target. Fight i uses seed i at every step, so
win rate changes only because the enemy changed.

    python -m clockwork.tune --agent greedy --target 0.65 --fights 200
"""
import argparse
import os
from concurrent.futures import ProcessPoolExecutor

from .decks import DECKS
from .enemies import ENEMIES, scaled
from .engine import apply, legal_actions, new_fight
from .run import make_agent


def _win_rate(args):
    agent_name, deck, spec, fights = args
    wins = 0
    for seed in range(fights):
        s = new_fight(DECKS[deck], spec, seed=seed)
        agent = make_agent(agent_name, seed)
        while s.result is None:
            apply(s, agent.act(s, legal_actions(s)))
        wins += s.result == "win"
    return wins / fights


def mean_win_rate(pool, agent, spec, fights):
    rates = list(pool.map(_win_rate, [(agent, d, spec, fights) for d in DECKS]))
    return sum(rates) / len(rates), rates


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="greedy", help="random, greedy, mcts or mcts@<budget>")
    ap.add_argument("--enemies", nargs="+", default=list(ENEMIES), choices=list(ENEMIES))
    ap.add_argument("--target", type=float, default=0.65)
    ap.add_argument("--fights", type=int, default=200)
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--lo", type=float, default=0.5)
    ap.add_argument("--hi", type=float, default=4.0)
    args = ap.parse_args(argv)

    with ProcessPoolExecutor(os.cpu_count()) as pool:
        for name in args.enemies:
            base = ENEMIES[name]
            lo, hi = args.lo, args.hi
            best = None
            for _ in range(args.steps):
                f = (lo + hi) / 2
                spec = scaled(base, f)
                rate, rates = mean_win_rate(pool, args.agent, spec, args.fights)
                if best is None or abs(rate - args.target) < abs(best[1] - args.target):
                    best = (f, rate, rates, spec)
                print(f"  {name} x{f:.3f}: hp {spec.hp}, mean win {rate:.1%}", flush=True)
                if rate > args.target:
                    lo = f
                else:
                    hi = f
            f, rate, rates, spec = best
            print(f"{name}: x{f:.3f} -> hp {spec.hp}, pattern {spec.pattern}, growth {spec.attack_growth} | "
                  f"mean {rate:.1%} | " + ", ".join(f"{d} {r:.0%}" for d, r in zip(DECKS, rates)), flush=True)


if __name__ == "__main__":
    main()

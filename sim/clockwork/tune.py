"""Retune enemy difficulty automatically.

Bisects one scale factor per enemy until a reference agent hits a target, averaged over the
test decks. Fight i uses seed i at every step, so results change only because the enemy did.

  --knob both    scale HP and attacks together (default)
  --knob attack  scale attacks only (attack growth and chime damage too); HP stays
  --knob hp      scale HP only
  --metric win      target = mean win rate (default)
  --metric hp_lost  target = mean HP lost on a win
  --start-hp N      fights start with N HP (HP carried over in a run)

    python -m clockwork.tune --agent mcts@50 --knob attack --metric hp_lost --target 15
"""
import argparse
import os
import statistics
from concurrent.futures import ProcessPoolExecutor

from .decks import DECKS
from .enemies import ENEMIES, scaled
from .engine import apply, legal_actions, new_fight
from .run import make_agent


def _deck_stats(args):
    agent_name, deck, spec, fights, start_hp = args
    wins, lost = 0, []
    for seed in range(fights):
        s = new_fight(DECKS[deck], spec, seed=seed, start_hp=start_hp)
        agent = make_agent(agent_name, seed)
        while s.result is None:
            apply(s, agent.act(s, legal_actions(s)))
        if s.result == "win":
            wins += 1
            lost.append((start_hp or s.rules.player_hp) - s.hp)
    return wins / fights, lost


def measure(pool, agent, spec, fights, start_hp=None):
    """(mean win rate over decks, mean HP lost on a win, per-deck win rates)."""
    results = list(pool.map(_deck_stats, [(agent, d, spec, fights, start_hp) for d in DECKS]))
    rates = [r for r, _ in results]
    lost = [x for _, l in results for x in l]
    return sum(rates) / len(rates), (statistics.mean(lost) if lost else float("inf")), rates


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="greedy", help="random, greedy, mcts or mcts@<budget>")
    ap.add_argument("--enemies", nargs="+", default=list(ENEMIES), choices=list(ENEMIES))
    ap.add_argument("--knob", choices=["both", "attack", "hp"], default="both")
    ap.add_argument("--metric", choices=["win", "hp_lost"], default="win")
    ap.add_argument("--target", type=float, default=0.65)
    ap.add_argument("--start-hp", type=int, default=None)
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
                spec = {"both": lambda: scaled(base, f), "attack": lambda: scaled(base, 1.0, f),
                        "hp": lambda: scaled(base, f, 1.0)}[args.knob]()
                rate, lost, rates = measure(pool, args.agent, spec, args.fights, args.start_hp)
                value = rate if args.metric == "win" else lost
                if best is None or abs(value - args.target) < abs(best[1] - args.target):
                    best = (f, value, rate, lost, rates, spec)
                print(f"  {name} x{f:.3f}: hp {spec.hp}, pattern {spec.pattern}, chime {spec.chime_damage} | "
                      f"win {rate:.1%}, HP lost on win {lost:.1f}", flush=True)
                # Both metrics fall as f falls for "both"/"hp" (win rises); handle direction per metric.
                too_hard = rate < args.target if args.metric == "win" else lost > args.target
                if too_hard:
                    hi = f
                else:
                    lo = f
            f, value, rate, lost, rates, spec = best
            print(f"{name}: x{f:.3f} -> hp {spec.hp}, pattern {spec.pattern}, growth {spec.attack_growth}, "
                  f"chime {spec.chime_damage} | win {rate:.1%}, HP lost on win {lost:.1f} | "
                  + ", ".join(f"{d} {r:.0%}" for d, r in zip(DECKS, rates)), flush=True)


if __name__ == "__main__":
    main()

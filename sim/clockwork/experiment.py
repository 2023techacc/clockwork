"""Run the Experiment setup v1 matrix (decks x enemies x agents) and write results.

    python -m clockwork.experiment --agents random greedy --fights 1000 --out results

Fight i uses seed i for every agent, so tiers face identical queues. Writes one CSV row
per fight to <out>/fights.csv and prints a win-rate table with 95% Wilson intervals.
"""
import argparse
import csv
import math
import os
from concurrent.futures import ProcessPoolExecutor

from .decks import DECKS
from .enemies import ENEMIES
from .engine import summary
from .run import AGENTS, play

NORMAL_TURN_DAMAGE = 18    # best starter turn: 3 Striker triggers
BURST_TURNS = 5            # "early on"


def wilson(wins, n, z=1.96):
    if n == 0:
        return 0.0, 0.0
    p = wins / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def run_cell(args):
    agent_name, deck, enemy, fights = args
    rows = []
    for seed in range(fights):
        s = play(deck, enemy, seed, AGENTS[agent_name](seed=seed))
        r = summary(s)
        early = s.stats.damage_by_turn[:BURST_TURNS]
        r.update(agent=agent_name, deck=deck, enemy=enemy, seed=seed,
                 burst_flag=int(max(early, default=0) >= 3 * NORMAL_TURN_DAMAGE))
        rows.append(r)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", nargs="+", default=["random", "greedy"], choices=sorted(AGENTS))
    ap.add_argument("--decks", nargs="+", default=list(DECKS), choices=list(DECKS))
    ap.add_argument("--enemies", nargs="+", default=list(ENEMIES), choices=list(ENEMIES))
    ap.add_argument("--fights", type=int, default=1000)
    ap.add_argument("--out", default="results")
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    args = ap.parse_args(argv)

    cells = [(a, d, e, args.fights) for a in args.agents for d in args.decks for e in args.enemies]
    with ProcessPoolExecutor(args.workers) as pool:
        results = list(pool.map(run_cell, cells))
    rows = [r for cell in results for r in cell]

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "fights.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    for agent in args.agents:
        print(f"\n{agent}: win rate (95% CI), {args.fights} fights per cell")
        print(f"{'deck':13s}" + "".join(f"{e:>20s}" for e in args.enemies))
        for deck in args.decks:
            line = f"{deck:13s}"
            for enemy in args.enemies:
                cell = [r for r in rows if (r["agent"], r["deck"], r["enemy"]) == (agent, deck, enemy)]
                wins = sum(r["result"] == "win" for r in cell)
                lo, hi = wilson(wins, len(cell))
                line += f"{wins / len(cell):>8.0%} ({lo:.0%}-{hi:.0%})"
            print(line)
        mine = [r for r in rows if r["agent"] == agent]
        print(f"  flags: burst {sum(r['burst_flag'] for r in mine)} fights | "
              f">8 triggers/turn {sum(r['turns_over_turn_cap'] > 0 for r in mine)} | "
              f"part >2x/turn {sum(r['turns_over_part_cap'] > 0 for r in mine)} | "
              f"runaway {sum(r['runaway_turns'] > 0 for r in mine)} | "
              f"max triggers in a turn {max(r['max_triggers_turn'] for r in mine)} | "
              f"max damage in a turn {max(r['max_damage_turn'] for r in mine)}")


if __name__ == "__main__":
    main()

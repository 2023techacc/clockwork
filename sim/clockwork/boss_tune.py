"""Tune bosses in run conditions.

Plays whole runs (clockwork.run_policy) up to the boss door and keeps each run's state there
(deck with attachments, machine upgrades, HP). Every boss is then fought from those same
states, and each boss's scale is bisected until its win rate matches the reference boss's.

    python -m clockwork.boss_tune --runs 150 --bosses furnace dismantler iron_colossus pendulum
"""
import argparse
import os
from concurrent.futures import ProcessPoolExecutor

from .config import DEFAULT_RULES
from .engine import apply, legal_actions, new_fight
from .enemies import BOSSES, ENEMIES, scaled
from .run import make_agent
from .run_mode import Run
from .run_policy import DEFAULT_STYLE, attach_all, best_mod, choose_door, play_fight, shop, MACHINE_PRIORITY, PART_VALUE
from .parts import Kind


def run_to_boss(args):
    """Play run `seed` until the boss door; return the state there (or None if the run died)."""
    seed, agent = args
    run = Run("starter", seed, rules=DEFAULT_RULES)
    style = DEFAULT_STYLE
    while run.phase not in ("won", "lost"):
        attach_all(run)
        if run.phase == "doors":
            if run.doors == ["boss"]:
                return {"seed": seed, "deck": run.fight_deck(), "rules": run.rules(), "hp": run.hp,
                        "scale": run.enemy_scale()}
            run.choose_door(choose_door(run, style))
        elif run.phase == "fight":
            play_fight(run, agent)
        elif run.phase == "reward":
            parts = sorted(run.offer["parts"], key=lambda p: -PART_VALUE.get(Kind(p), 0))
            best = parts[0] if PART_VALUE.get(Kind(parts[0]), 0) > 0 else ""
            salvage = sorted(run.offer.get("salvage", []), key=MACHINE_PRIORITY.index)
            run.take_reward(part=best, attachment=best_mod(run, run.offer.get("attachments", [])),
                            scrap=not best, salvage=salvage[0] if salvage else "")
        elif run.phase == "rest":
            run.rest("heal" if run.hp < 0.6 * run.max_hp() else "tinker")
        elif run.phase == "workshop":
            shop(run, style)
    return None


def boss_fight(args):
    snap, boss, f, agent = args
    spec = scaled(ENEMIES[boss], snap["scale"] * f)
    s = new_fight(snap["deck"], spec, seed=snap["seed"] * 100 + 99, rules=snap["rules"], start_hp=snap["hp"])
    a = make_agent(agent, snap["seed"])
    while s.result is None:
        apply(s, a.act(s, legal_actions(s)))
    return s.result == "win"


def win_rate(pool, snaps, boss, f, agent):
    res = list(pool.map(boss_fight, [(sn, boss, f, agent) for sn in snaps], chunksize=4))
    return sum(res) / len(res)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="mcts@50")
    ap.add_argument("--runs", type=int, default=150)
    ap.add_argument("--reference", default="clock_tower")
    ap.add_argument("--bosses", nargs="+", default=[b for b in BOSSES if b != "clock_tower"])
    ap.add_argument("--steps", type=int, default=5)
    ap.add_argument("--lo", type=float, default=0.7)
    ap.add_argument("--hi", type=float, default=1.1)
    args = ap.parse_args(argv)
    with ProcessPoolExecutor(os.cpu_count()) as pool:
        snaps = [s for s in pool.map(run_to_boss, [(seed, args.agent) for seed in range(args.runs)]) if s]
        print(f"{len(snaps)} of {args.runs} runs reached the boss "
              f"(mean HP {sum(s['hp'] for s in snaps) / len(snaps):.1f})", flush=True)
        target = win_rate(pool, snaps, args.reference, 1.0, args.agent)
        print(f"reference {args.reference}: wins {target:.0%} from those states", flush=True)
        for boss in args.bosses:
            base = ENEMIES[boss]
            lo, hi, best = args.lo, args.hi, None
            for _ in range(args.steps):
                f = (lo + hi) / 2
                rate = win_rate(pool, snaps, boss, f, args.agent)
                spec = scaled(base, f)
                print(f"  {boss} x{f:.3f}: hp {spec.hp}, pattern {spec.pattern} | wins {rate:.0%}", flush=True)
                if best is None or abs(rate - target) < abs(best[1] - target):
                    best = (f, rate, spec)
                if rate < target:
                    hi = f
                else:
                    lo = f
            f, rate, spec = best
            print(f"{boss}: x{f:.3f} -> hp {spec.hp}, pattern {spec.pattern} | wins {rate:.0%} "
                  f"(target {target:.0%})", flush=True)


if __name__ == "__main__":
    main()

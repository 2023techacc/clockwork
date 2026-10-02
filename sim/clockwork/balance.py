"""Balance pass: sweep one knob per part and measure what one pick of it is worth.

Each sweep plays a probe deck (the starter plus that part) against every enemy at each value
and reports win-rate points over the starter deck. The value closest to TARGET inside BAND is
recommended. Checks are single measurements of enabler pairings at the default values.

    python -m clockwork.balance --agent mcts@50 --fights 100
"""
import argparse
import os
from concurrent.futures import ProcessPoolExecutor

from .config import RulesConfig
from .enemies import ENEMIES
from .run import make_agent, play

TARGET, BAND = 18, (10, 25)

# (name, probe deck, list of settings); a setting is a dict of RulesConfig fields, where
# "part" entries become part_overrides.
SWEEPS = [
    ("Primer", "plus_primer", [{"part": [("Primer", "fresh_damage", v)]} for v in (6, 8, 10, 12, 14, 18)]),
    ("Assembly", "plus_assembly", [{"part": [("Assembly", "per_install_damage", v)]} for v in (0, 1, 2, 3)]),
    ("Coil", "coil_starter", [{"coil_damage": v} for v in (1, 2, 3, 4)]),
    ("Polish", "plus_polish_mirror", [{"polish_bonus": v} for v in (0.1, 0.2, 0.3, 0.5)]),
    ("Coupler", "plus_coupler", [{"part": [("Coupler", "extra_heat", v)]} for v in (0, 1, 2, 3)]),
    ("Amplifier", "plus_amplifier", [{"amplifier_bonus": v} for v in (0.2, 0.3, 0.4, 0.5)]),
    ("Hammer", "plus_hammer", [{"part": [("Hammer", "damage", d), ("Hammer", "extra_heat", h)]}
                               for d, h in ((9, 4), (10, 4), (11, 4), (12, 4), (10, 3), (11, 3), (12, 3))]),
]
# Round 2: finer settings for parts whose first sweep jumped over the band.
SWEEPS += [
    ("Primer2", "plus_primer", [{"part": [("Primer", "damage", b), ("Primer", "fresh_damage", f)]}
                                for b, f in ((4, 7), (2, 8), (2, 10), (0, 12))]),
    ("Assembly2", "plus_assembly", [{"part": [("Assembly", "damage", b), ("Assembly", "per_part_damage", pp),
                                              ("Assembly", "per_install_damage", pi)]}
                                    for b, pp, pi in ((0, 0, 3), (0, 0, 4), (2, 0, 3), (3, 0, 2))]),
    ("Slider", "plus_clamp_magnet_slider", [{"part": [("Slider", "moved_bonus", v)]} for v in (0, 2, 4)]),
    ("Coil2", "coil_starter", [{"coil_damage": v} for v in (3, 4)]),
]

CHECKS = ["plus_loader_primer", "plus_feeder_loader_primer", "plus_loader_assembly", "plus_magnet",
          "plus_slider", "plus_magnet_slider", "plus_clamp_magnet_slider"]


def make_rules(setting):
    kwargs = {k: v for k, v in setting.items() if k != "part"}
    return RulesConfig(part_overrides=tuple(setting.get("part", ())), **kwargs)


def _cell(args):
    agent, deck, enemy, seeds, setting = args
    rules = make_rules(setting)
    wins = 0
    for seed in seeds:
        wins += play(deck, enemy, seed, make_agent(agent, seed), rules=rules).result == "win"
    return enemy, wins, len(seeds)


def measure(pool, agent, deck, setting, fights, block=25):
    tasks = [(agent, deck, e, range(lo, min(lo + block, fights)), setting)
             for e in ENEMIES for lo in range(0, fights, block)]
    per = {}
    for e, w, n in pool.map(_cell, tasks):
        a, b = per.get(e, (0, 0))
        per[e] = (a + w, b + n)
    return sum(w / n for w, n in per.values()) / len(per)


def label(setting):
    parts = [f"{f}={v}" for _, f, v in setting.get("part", ())]
    return ", ".join(parts + [f"{k}={v}" for k, v in setting.items() if k != "part"]) or "default"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="mcts@50")
    ap.add_argument("--fights", type=int, default=100)
    ap.add_argument("--only", nargs="*", help="sweep names to run (default all)")
    args = ap.parse_args(argv)

    with ProcessPoolExecutor(os.cpu_count()) as pool:
        base = measure(pool, args.agent, "starter", {}, args.fights)
        print(f"starter: {base:.0%}", flush=True)
        picks = {}
        for name, deck, settings in SWEEPS:
            if args.only and name not in args.only:
                continue
            results = []
            for setting in settings:
                pts = (measure(pool, args.agent, deck, setting, args.fights) - base) * 100
                results.append((pts, setting))
                print(f"{name:10s} {label(setting):40s} {pts:+5.0f}", flush=True)
            inside = [r for r in results if BAND[0] <= r[0] <= BAND[1]]
            pts, setting = min(inside or results, key=lambda r: abs(r[0] - TARGET))
            picks[name] = (pts, setting)
            print(f"  -> {name}: {label(setting)} ({pts:+.0f}){'' if inside else '  (no value inside the band)'}",
                  flush=True)
        if not args.only:
            for deck in CHECKS:
                pts = (measure(pool, args.agent, deck, {}, args.fights) - base) * 100
                print(f"check {deck:30s} {pts:+5.0f}", flush=True)
        print("\nRecommended:")
        for name, (pts, setting) in picks.items():
            print(f"  {name}: {label(setting)} ({pts:+.0f})")


if __name__ == "__main__":
    main()

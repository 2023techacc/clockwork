"""Part balance pass (v15): what one pick of a part is worth, as win-rate points over the starter
deck in fights that start at 30 HP (typical mid-run HP), against every enemy, paired seeds.
Target: +3 to +10 (clockwork.targets); combo enablers may be slightly negative alone.

    python -m clockwork.part_pass --fights 40              # current values for every part
    python -m clockwork.part_pass --fights 40 --sweep      # the candidate settings below
"""
import argparse
import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

from .config import DEFAULT_RULES
from .decks import STARTER
from .enemies import ENEMIES
from .engine import apply, legal_actions, new_fight
from .parts import Kind as K
from .run import make_agent
from .run_mode import PART_TIER

START_HP = 30


def _cell(args):
    deck, enemy, seeds, agent, rules = args
    wins = 0
    for seed in seeds:
        s = new_fight(deck, enemy, seed=seed, rules=rules, start_hp=START_HP)
        a = make_agent(agent, seed)
        while s.result is None:
            apply(s, a.act(s, legal_actions(s)))
        wins += s.result == "win"
    return wins, len(seeds)


def win_rate(pool, deck, rules, agent, fights, block=10):
    res = list(pool.map(_cell, [(deck, e, range(lo, min(lo + block, fights)), agent, rules)
                                for e in ENEMIES for lo in range(0, fights, block)]))
    return sum(w for w, _ in res) / sum(n for _, n in res)


def with_part(kind):
    deck = dict(STARTER)
    deck[kind] = deck.get(kind, 0) + 1
    return deck


def rules_for(setting):
    parts = tuple(setting.get("part", ()))
    other = {k: v for k, v in setting.items() if k != "part"}
    return replace(DEFAULT_RULES, part_overrides=DEFAULT_RULES.part_overrides + parts, **other)


# part, label, setting (RulesConfig fields; "part" entries become part_overrides)
SWEEP = [
    (K.MAGNET, "Block per pull 5", {"magnet_block_per_pull": 5}),
    (K.MAGNET, "Block per pull 4", {"magnet_block_per_pull": 4}),
    (K.HAMMER, "10 dmg, +3 Heat", {"part": [("Hammer", "damage", 10), ("Hammer", "extra_heat", 3)]}),
    (K.HAMMER, "11 dmg, +3 Heat", {"part": [("Hammer", "damage", 11), ("Hammer", "extra_heat", 3)]}),
    (K.HAMMER, "10 dmg, +2 Heat", {"part": [("Hammer", "damage", 10), ("Hammer", "extra_heat", 2)]}),
    (K.COUPLER, "+1 Heat", {"part": [("Coupler", "extra_heat", 1)]}),
    (K.COUPLER, "+0 Heat", {"part": [("Coupler", "extra_heat", 0)]}),
    (K.SLIDER, "6 dmg", {"part": [("Slider", "damage", 6)]}),
    (K.SLIDER, "7 dmg", {"part": [("Slider", "damage", 7)]}),
    (K.ASSEMBLY, "4 per install", {"part": [("Assembly", "per_install_damage", 4)]}),
    (K.ASSEMBLY, "2 + 3 per install", {"part": [("Assembly", "damage", 2)]}),
    (K.LOADER, "3 loads", {"loader_loads": 3}),
    (K.LOADER, "2 loads + 3 Block", {"part": [("Loader", "block", 3)]}),
    (K.SPRING, "no chain Heat", {"spring_heat_step": 0}),
    (K.SPRING, "+3 Block", {"part": [("Spring", "block", 3)]}),
]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="mcts@50")
    ap.add_argument("--fights", type=int, default=40)
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--only", nargs="*", help="part names to measure")
    args = ap.parse_args(argv)
    with ProcessPoolExecutor(os.cpu_count()) as pool:
        base = win_rate(pool, STARTER, DEFAULT_RULES, args.agent, args.fights)
        print(f"starter from {START_HP} HP: {base:.1%}", flush=True)
        if args.sweep:
            for kind, label, setting in SWEEP:
                if args.only and kind.value not in args.only:
                    continue
                rules = rules_for(setting)
                # The part's own setting can change the starter too (e.g. Spring), so re-measure it.
                b = base if kind not in STARTER else win_rate(pool, STARTER, rules, args.agent, args.fights)
                r = win_rate(pool, with_part(kind), rules, args.agent, args.fights)
                print(f"{kind.value:10s} {label:22s} {(r - b) * 100:+5.1f} pts", flush=True)
        else:
            for kind in PART_TIER:
                if args.only and kind.value not in args.only:
                    continue
                r = win_rate(pool, with_part(kind), DEFAULT_RULES, args.agent, args.fights)
                print(f"{kind.value:10s} {(r - base) * 100:+5.1f} pts", flush=True)


if __name__ == "__main__":
    main()

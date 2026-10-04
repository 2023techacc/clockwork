"""Loop finder: the strongest single turn each gear layout allows.

Tries every 6-slot layout that can be built from a deck's parts (with empty slots),
starting from a given Heat with full Crank Power, and every way to spend that Crank
Power. Reports the layouts with the most triggers and the most damage in one turn.

    python -m clockwork.loopfinder --deck copy_loop --heat 0 5 --top 10

Layouts are printed in arrival order: the first part is at the Trigger Point before the
turn's free crank, the second comes up on the free crank, and so on. No enemy HP limit,
no installs; Loaders find an empty queue.
"""
import argparse
import itertools
import os
from concurrent.futures import ProcessPoolExecutor

from .config import DEFAULT_RULES
from .decks import DECKS
from .engine import new_fight
from .parts import Kind, Part
from .search import after_installs


def layouts(deck, n):
    kinds = [None] + list(deck)
    for combo in itertools.product(kinds, repeat=n):
        if all(combo.count(k) <= c for k, c in deck.items()):
            yield combo


def evaluate(layout, heat, template):
    s = template.clone()
    n = len(layout)
    s.gear = [None] * n
    s.top = 0
    for k, key in enumerate(layout):
        if key is not None:
            kind, mods = key if isinstance(key, tuple) else (key, ())
            s.gear[(-k) % n] = Part(k, kind, mods)
    s.heat = heat
    best_t = best_d = None
    for acts, end in after_installs(s, []):
        t, d = end.triggers_turn, end.damage_turn
        if best_t is None or (t, d) > best_t[:2]:
            best_t = (t, d, end.heat, end.overheat_pending, acts)
        if best_d is None or (d, -t) > (best_d[1], -best_d[0]):
            best_d = (t, d, end.heat, end.overheat_pending, acts)
    return best_t, best_d


def _template(rules):
    s = new_fight({Kind.STRIKER: 1}, "dummy", seed=0, rules=rules)
    s.hand, s.queue, s.discard = [], [], []
    s.enemy_hp = 10 ** 9
    return s


def _chunk(args):
    deck_name, first, heat = args
    return chunk_for((DECKS[deck_name], first, heat))


def chunk_for(args):
    """Every layout of `deck` (keys Kind or (Kind, mods)) whose first part is `first`."""
    deck, first, heat = args
    rules = DEFAULT_RULES
    template = _template(rules)
    out = []
    rest_deck = dict(deck)
    if first is not None:
        rest_deck[first] -= 1
    for rest in layouts(rest_deck, rules.gear_size - 1):
        layout = (first,) + rest
        bt, bd = evaluate(layout, heat, template)
        out.append((layout, bt, bd))
    return out


def _name(key):
    if key is None:
        return "--"
    if isinstance(key, tuple):
        mods = key[1] if isinstance(key[1], tuple) else (key[1],)
        return key[0].value + "".join("+" + m.value for m in mods)
    return key.value


def fmt(layout, r):
    t, d, heat, over, acts = r
    names = " > ".join(_name(k) for k in layout)
    cranks = " ".join("free " + a[1] if a[0] == "end_install" and len(a) > 1 else a[0] for a in acts)
    return f"{t:3d} triggers {d:4d} dmg  end Heat {heat}{' OVERHEAT' if over else ''}  [{names}]  ({cranks})"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", nargs="+", default=list(DECKS), choices=list(DECKS))
    ap.add_argument("--heat", nargs="+", type=int, default=[0, 5])
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--workers", type=int, default=os.cpu_count())
    args = ap.parse_args(argv)

    with ProcessPoolExecutor(args.workers) as pool:
        for deck_name in args.deck:
            firsts = [None] + list(DECKS[deck_name])
            for heat in args.heat:
                rows = [r for chunk in pool.map(_chunk, [(deck_name, f, heat) for f in firsts]) for r in chunk]
                by_t = sorted(rows, key=lambda r: (r[1][0], r[1][1]), reverse=True)
                by_d = sorted(rows, key=lambda r: (r[2][1], -r[2][0]), reverse=True)
                print(f"\n=== {deck_name}, start Heat {heat}: {len(rows)} layouts | "
                      f"max triggers {by_t[0][1][0]}, max damage {by_d[0][2][1]} | "
                      f">8 triggers: {sum(r[1][0] > 8 for r in rows)} layouts | "
                      f">=54 damage: {sum(r[2][1] >= 54 for r in rows)} layouts")
                print("most triggers:")
                for layout, bt, _ in by_t[:args.top]:
                    print("  " + fmt(layout, bt))
                print("most damage:")
                for layout, _, bd in by_d[:args.top]:
                    print("  " + fmt(layout, bd))


if __name__ == "__main__":
    main()

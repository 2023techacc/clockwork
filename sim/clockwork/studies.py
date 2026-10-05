"""Studies run without human playtesters (AI-Playtesting-Roadmap.md, Results v11).

    python -m clockwork.studies attachments --fights 40
    python -m clockwork.studies machine --fights 40 --runs 150
    python -m clockwork.studies styles --runs 150
    python -m clockwork.studies combos
    python -m clockwork.studies bosses --fights 40 --runs 150

attachments  what one attachment is worth on each part it fits, in single fights against every
             enemy (normal, elite and boss): win-rate points and HP kept, paired seeds against the
             same deck without it.
machine      what each machine upgrade is worth, in single fights and when a run starts with it.
styles       run strategies (elite seeking, resting, deck thinning, saving for upgrades...) and
             where runs lose their HP (per enemy, per node).
combos       the strongest single turn attachment combos allow (loop finder).
bosses       every boss against every test deck, and whole runs ending at each boss.
fun          simulator proxies for fun: fight length, close wins, combo turns, how much each turn's
             choice matters, and build variety (human ratings come from playtests/).
"""
import argparse
import os
import statistics
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

from .config import DEFAULT_RULES
from .decks import STARTER
from .enemies import ENEMIES
from .engine import apply, legal_actions, new_fight
from .experiment import wilson
from .parts import Kind as K, Mod as M
from .run import make_agent
from .run_mode import MACHINE, Run
from .run_policy import simulate_run


def plus(extra, base=STARTER):
    deck = dict(base)
    for key, n in extra.items():
        deck[key] = deck.get(key, 0) + n
    return deck


def swap(kind, mods, base=STARTER):
    """The base deck with one plain copy of `kind` replaced by a copy carrying `mods`."""
    deck = plus({kind: -1, (kind, mods): 1}, base)
    return {k: n for k, n in deck.items() if n}


# (label, deck with the attachment, deck without it)
H = {K.HAMMER: 1}
ATTACHMENT_CASES = [
    ("Sharpened on Striker", swap(K.STRIKER, M.SHARPENED), STARTER),
    ("Sharpened on Plate", swap(K.PLATE, M.SHARPENED), STARTER),
    ("Sharpened on Spring", swap(K.SPRING, M.SHARPENED), STARTER),
    ("Counterweight on Plate", swap(K.PLATE, M.COUNTERWEIGHT), STARTER),
    ("Counterweight on Striker", swap(K.STRIKER, M.COUNTERWEIGHT), STARTER),
    ("Bracing on Striker", swap(K.STRIKER, M.BRACING), STARTER),
    ("Heat Sink on Striker", swap(K.STRIKER, M.HEAT_SINK), STARTER),
    ("Heat Sink on Spring", swap(K.SPRING, M.HEAT_SINK), STARTER),
    ("Coil on Spring", swap(K.SPRING, M.COIL), STARTER),
    ("Polish on Mirror", plus({(K.MIRROR, M.POLISH): 1}), plus({K.MIRROR: 1})),
    ("Clamp on Magnet", plus({(K.MAGNET, M.CLAMP): 1}), plus({K.MAGNET: 1})),
    ("Feeder on Loader", plus({(K.LOADER, M.FEEDER): 1}), plus({K.LOADER: 1})),
    ("Governor on Striker", swap(K.STRIKER, M.GOVERNOR), STARTER),
    ("Governor on Spring", swap(K.SPRING, M.GOVERNOR), STARTER),
    ("Governor on Hammer", plus({(K.HAMMER, M.GOVERNOR): 1}), plus(H)),
    ("Echo on Striker", swap(K.STRIKER, M.ECHO), STARTER),
    ("Echo on Plate", swap(K.PLATE, M.ECHO), STARTER),
    ("Echo on Spring", swap(K.SPRING, M.ECHO), STARTER),
    ("Echo on Hammer", plus({(K.HAMMER, M.ECHO): 1}), plus(H)),
    ("2 attachments: Sharpened+Echo on Striker", swap(K.STRIKER, (M.ECHO, M.SHARPENED)), STARTER),
    ("2 attachments: Echo+Governor on Hammer", plus({(K.HAMMER, (M.ECHO, M.GOVERNOR)): 1}), plus(H)),
]


# ---------------------------------------------------------------- single fights

def fight(deck, enemy, seed, agent, rules=DEFAULT_RULES):
    s = new_fight(deck, enemy, seed=seed, rules=rules)
    a = make_agent(agent, seed)
    while s.result is None:
        apply(s, a.act(s, legal_actions(s)))
    return s.result == "win", (s.hp if s.result == "win" else 0)


def _fights(args):
    deck, enemy, seeds, agent, rules = args
    return enemy, [fight(deck, enemy, seed, agent, rules) for seed in seeds]


def measure(pool, deck, agent, fights, rules=DEFAULT_RULES, block=10):
    """Per enemy: (wins, HP kept summed, n). HP kept counts a loss as 0."""
    tasks = [(deck, e, range(lo, min(lo + block, fights)), agent, rules)
             for e in ENEMIES for lo in range(0, fights, block)]
    per = {e: [0, 0, 0] for e in ENEMIES}
    for e, res in pool.map(_fights, tasks):
        per[e][0] += sum(w for w, _ in res)
        per[e][1] += sum(h for _, h in res)
        per[e][2] += len(res)
    return per


def overall(per):
    win = sum(w / n for w, _, n in per.values()) / len(per)
    hp = sum(h / n for _, h, n in per.values()) / len(per)
    return win, hp


def groups(per):
    """Win rate per enemy group: normal / elite / boss."""
    out = {}
    for name, (w, _, n) in per.items():
        e = ENEMIES[name]
        g = "boss" if name == "clock_tower" else "elite" if e.elite else "normal"
        out.setdefault(g, []).append(w / n)
    return {g: sum(v) / len(v) for g, v in out.items()}


def study_attachments(pool, args):
    cache = {}

    def get(deck):
        key = repr(sorted(deck.items(), key=repr))
        if key not in cache:
            cache[key] = measure(pool, deck, args.agent, args.fights)
        return cache[key]

    print(f"Attachments ({args.agent}, {args.fights} fights per enemy, all {len(ENEMIES)} enemies, full HP)")
    print(f"{'case':44s} {'win pts':>8s} {'HP kept':>8s} {'normal':>7s} {'elite':>7s} {'boss':>7s}")
    rows = []
    for label, with_, without in ATTACHMENT_CASES:
        a, b = get(with_), get(without)
        (wa, ha), (wb, hb) = overall(a), overall(b)
        ga, gb = groups(a), groups(b)
        rows.append((label, (wa - wb) * 100, ha - hb))
        print(f"{label:44s} {(wa - wb) * 100:+8.1f} {ha - hb:+8.1f} "
              + " ".join(f"{(ga[g] - gb[g]) * 100:+7.1f}" for g in ("normal", "elite", "boss")), flush=True)
    print("\nbaselines: " + ", ".join(f"{k}: {overall(v)[0]:.0%} win, {overall(v)[1]:.1f} HP kept"
                                       for k, v in [("starter", get(STARTER)), ("+Hammer", get(plus(H))),
                                                    ("+Mirror", get(plus({K.MIRROR: 1}))),
                                                    ("+Magnet", get(plus({K.MAGNET: 1}))),
                                                    ("+Loader", get(plus({K.LOADER: 1})))]))
    return rows


# ---------------------------------------------------------------- runs

def _runs(args):
    seeds, agent, style, machine, rules, patch, boss = args
    from . import run_mode
    saved = {name: getattr(run_mode, name) for name in patch}
    for name, value in patch.items():        # module-level run constants, e.g. ELITE_COG_BONUS
        setattr(run_mode, name, value)
    try:
        return [summarise(simulate_run("starter", seed, agent, rules=rules, style=style, machine=machine, boss=boss))
                for seed in seeds]
    finally:
        for name, value in saved.items():
            setattr(run_mode, name, value)


def summarise(run):
    fights = [h for h in run.history if "enemy" in h]
    boss_loot = sum(h.get("cogs", 0) for h in fights if h["node"] == "boss")
    return {"won": run.phase == "won", "stop": run.stop, "cogs": run.cogs - boss_loot,   # unspent before the boss
            "elites": sum(h["node"] == "elite" for h in fights),
            "attachments": sum(len(c["mods"]) for c in run.cards) + len(run.inventory),
            "machine": len(run.machine), "deck": len(run.cards),
            "boss_hp": next((h["hp_start"] for h in fights if h["node"] == "boss"), None),
            "died_to": fights[-1]["enemy"] if run.phase == "lost" else None,
            "fights": [(h["node"], h["enemy"], h["stop"], h["hp_start"], h["hp_end"], h["result"], h.get("cogs", 0))
                       for h in fights],
            "rests": [h["choice"] for h in run.history if h.get("node") == "rest"],
            "shops": sum(h.get("node") == "workshop" for h in run.history)}


def play_runs(pool, runs, agent, style=None, machine=(), rules=None, block=3, patch=None, boss=None):
    tasks = [(range(lo, min(lo + block, runs)), agent, style or {}, tuple(machine), rules, patch or {}, boss)
             for lo in range(0, runs, block)]
    return [o for chunk in pool.map(_runs, tasks) for o in chunk]


def run_line(label, out, base=None):
    n = len(out)
    won = sum(o["won"] for o in out)
    lo, hi = wilson(won, n)
    boss = [o["boss_hp"] for o in out if o["boss_hp"] is not None]
    delta = ""
    if base is not None:
        # Paired by seed: runs this variant won that the base lost, and the other way round.
        gain = sum(o["won"] and not b["won"] for o, b in zip(out, base))
        loss = sum(b["won"] and not o["won"] for o, b in zip(out, base))
        delta = f" | vs base +{gain}/-{loss}"
    print(f"{label:30s} cleared {won / n:4.0%} ({lo:.0%}-{hi:.0%}) | boss reached {len(boss) / n:4.0%} "
          f"at {statistics.mean(boss) if boss else 0:4.1f} HP | elites {statistics.mean(o['elites'] for o in out):.2f} "
          f"| attach {statistics.mean(o['attachments'] for o in out):.1f} | machine "
          f"{statistics.mean(o['machine'] for o in out):.2f} | deck {statistics.mean(o['deck'] for o in out):.1f} "
          f"| unspent {statistics.mean(o['cogs'] for o in out):3.0f}{delta}", flush=True)


def study_machine(pool, args):
    print(f"Machine upgrades, single fights ({args.agent}, {args.fights} per enemy):")
    decks = {"starter": STARTER, "mid deck (+Primer, Coupler, Hammer, Amplifier)":
             plus({K.PRIMER: 1, K.COUPLER: 1, K.HAMMER: 1, K.AMPLIFIER: 1})}
    for dname, deck in decks.items():
        base = measure(pool, deck, args.agent, args.fights)
        wb, hb = overall(base)
        print(f"  {dname}: base {wb:.0%} win, {hb:.1f} HP kept")
        for key in MACHINE:
            run = Run("starter", 0)
            run.machine = [key]
            per = measure(pool, deck, args.agent, args.fights, rules=run.rules())
            w, h = overall(per)
            g, gb = groups(per), groups(base)
            print(f"    {MACHINE[key][0]:14s} {(w - wb) * 100:+6.1f} win pts {h - hb:+6.1f} HP kept | "
                  + " ".join(f"{k} {(g[k] - gb[k]) * 100:+.0f}" for k in ("normal", "elite", "boss")), flush=True)
    print(f"\nMachine upgrades, whole runs started with it ({args.agent}, {args.runs} runs, paired seeds):")
    base = play_runs(pool, args.runs, args.agent)
    run_line("no upgrade", base)
    for key in MACHINE:
        run_line(f"start with {MACHINE[key][0]}", play_runs(pool, args.runs, args.agent, machine=[key]), base)


STYLES = [
    ("elites: seek", {"elites": "seek"}),
    ("elites: avoid", {"elites": "avoid"}),
    ("rest: always heal", {"rest": "heal"}),
    ("rest: always tinker", {"rest": "tinker"}),
    ("parts: never take (scrap)", {"parts": "none"}),
    ("parts: always take best", {"parts": "all"}),
    ("remove basics in Workshop", {"remove_basics": True}),
    ("save for machine upgrades", {"machine_first": True}),
    ("seek elites + save for machine", {"elites": "seek", "machine_first": True}),
]


def study_styles(pool, args):
    print(f"Run styles ({args.agent}, {args.runs} runs each, same seeds):")
    base = play_runs(pool, args.runs, args.agent)
    run_line("base policy", base)
    for label, style in STYLES:
        run_line(label, play_runs(pool, args.runs, args.agent, style=style), base)
    hp_report(base)


def hp_report(out):
    """Where runs lose HP: per enemy and per node, from the base-policy runs."""
    per = {}
    for o in out:
        for node, enemy, stop, start, end, result, cogs in o["fights"]:
            d = per.setdefault((node, enemy), {"lost": [], "deaths": 0, "cogs": []})
            d["lost"].append(start - end)
            d["deaths"] += result != "win"
            d["cogs"].append(cogs)
    print("\nWhere the base-policy runs lose HP (HP lost per fight, counting a death as all remaining HP):")
    print(f"  {'node':6s} {'enemy':13s} {'fights':>6s} {'mean HP lost':>12s} {'deaths':>6s} {'cogs':>5s} {'cogs/HP':>7s}")
    for (node, enemy), d in sorted(per.items(), key=lambda kv: ({"fight": 0, "elite": 1, "boss": 2}[kv[0][0]],
                                                                -statistics.mean(kv[1]["lost"]))):
        lost = statistics.mean(d["lost"])
        cogs = statistics.mean(d["cogs"])
        print(f"  {node:6s} {enemy:13s} {len(d['lost']):6d} {lost:12.1f} {d['deaths']:6d} {cogs:5.0f} "
              f"{cogs / lost if lost else float('inf'):7.1f}")


# ---------------------------------------------------------------- bosses

def _boss_fights(args):
    deck, boss, seeds, agent, start_hp, scale = args
    from .enemies import ENEMIES, scaled
    from .decks import DECKS
    spec = scaled(ENEMIES[boss], scale)
    wins, left = 0, []
    for seed in seeds:
        s = new_fight(DECKS[deck], spec, seed=seed, start_hp=start_hp)
        a = make_agent(agent, seed)
        while s.result is None:
            apply(s, a.act(s, legal_actions(s)))
        if s.result == "win":
            wins += 1
            left.append(s.hp)
    return deck, boss, wins, len(seeds), left


def study_bosses(pool, args):
    from .decks import DECKS
    from .enemies import BOSSES
    scale = 1.0     # fixed test decks have no attachments or upgrades, so base strength (not x1+GROWTH)
    print(f"Bosses vs test decks ({args.agent}, {args.fights} fights each, start at 36 HP, base strength): "
          "win rate")
    tasks = [(d, b, range(lo, min(lo + 10, args.fights)), args.agent, 36, scale)
             for b in BOSSES for d in DECKS for lo in range(0, args.fights, 10)]
    cell = {}
    for d, b, w, n, left in pool.map(_boss_fights, tasks):
        c = cell.setdefault((b, d), [0, 0, []])
        c[0] += w
        c[1] += n
        c[2] += left
    print(f"  {'boss':14s}" + "".join(f"{d:>13s}" for d in DECKS) + f"{'mean':>8s}")
    for b in BOSSES:
        rates = [cell[(b, d)][0] / cell[(b, d)][1] for d in DECKS]
        print(f"  {b:14s}" + "".join(f"{r:13.0%}" for r in rates) + f"{sum(rates) / len(rates):8.0%}", flush=True)
    print(f"\nWhole runs ending at each boss ({args.agent}, {args.runs} runs each, same seeds):")
    for b in BOSSES:
        out = play_runs(pool, args.runs, args.agent, boss=b)
        at_boss = [o for o in out if o["boss_hp"] is not None]
        boss_wins = sum(o["won"] for o in at_boss)
        run_line(f"boss {b}", out)
        print(f"    reached the boss {len(at_boss)}, beat it {boss_wins} ({boss_wins / max(1, len(at_boss)):.0%})",
              flush=True)


# ---------------------------------------------------------------- fun proxies

def _turn_choice(state):
    """How much this turn's choice matters, scored with the greedy heuristic over every distinct
    outcome (damage, Block, Heat, HP): (best - median score, outcomes within 3 points of the best)."""
    from .agents.greedy_agent import GreedyAgent
    from .search import turn_outcomes
    world = state.clone()
    world.log = None
    scorer = GreedyAgent()
    seen = {}
    for _, end in turn_outcomes(world):
        if end.result == "win":
            return None                       # a winning turn: nothing to weigh
        key = (end.enemy_hp, end.hp, end.block, end.heat, end.overheat_pending)   # distinct outcomes
        seen[key] = scorer.score(world, end)
    scores = sorted(v for v in seen.values() if v > -1e4)   # ignore plans that die to the attack
    if len(scores) < 2:
        return 0.0, 1
    best = scores[-1]
    return best - statistics.median(scores), sum(v >= best - 3 for v in scores)


def _fun_runs(args):
    seeds, agent = args
    from . import run_policy
    from .engine import summary
    fights = []

    def observed_fight(run, agent_name):
        s = new_fight(run.fight_deck(), run.enemy_spec(), seed=run.fight_seed(), rules=run.rules(), start_hp=run.hp)
        a = make_agent(agent_name, run.fight_seed())
        choices = []
        while s.result is None:
            if s.phase == "install" and not s.dead_turn and s.installs_left == s.rules.installs_per_turn:
                c = _turn_choice(s)
                if c is not None:
                    choices.append(c)
            apply(s, a.act(s, legal_actions(s)))
        run.finish_fight(s.result, s.hp, s.turn)
        fights.append({"node": run.node, "won": s.result == "win", "hp": s.hp, "max_hp": s.rules.player_hp,
                       "turns": s.turn, "triggers": list(s.stats.triggers_by_turn), "overheats": s.stats.overheats,
                       "choices": choices})

    saved = run_policy.play_fight
    run_policy.play_fight = observed_fight
    try:
        builds = []
        for seed in seeds:
            run = simulate_run("starter", seed, agent)
            added = [c["kind"].value for c in run.cards[8:]]
            builds.append(max(set(added), key=added.count) if added else "none")
    finally:
        run_policy.play_fight = saved
    return fights, builds


def study_fun(pool, args):
    import math
    tasks = [(range(lo, min(lo + 3, args.runs)), args.agent) for lo in range(0, args.runs, 3)]
    fights, builds = [], []
    for f, b in pool.map(_fun_runs, tasks):
        fights += f
        builds += b
    print(f"Fun proxies ({args.agent}, {args.runs} runs, {len(fights)} fights)")
    for node in ("fight", "elite", "boss"):
        fs = [f for f in fights if f["node"] == node]
        won = [f for f in fs if f["won"]]
        close = sum(f["hp"] <= 0.25 * f["max_hp"] for f in won)
        print(f"  {node:6s}: {statistics.mean(f['turns'] for f in fs):4.1f} turns per fight | "
              f"close wins (<= 25% HP) {close / max(1, len(won)):4.0%} of {len(won)} wins | "
              f"overheats per fight {statistics.mean(f['overheats'] for f in fs):.2f}")
    turns = [t for f in fights for t in f["triggers"]]
    print(f"  combo turns (4+ triggers): {sum(t >= 4 for t in turns) / len(turns):.0%} of {len(turns)} turns")
    choices = [c for f in fights for c in f["choices"]]
    spreads = [c[0] for c in choices]
    forced = sum(c[1] == 1 for c in choices)
    print(f"  turn choices: best plan beats the median plan by {statistics.mean(spreads):.1f} "
          f"(median {statistics.median(spreads):.1f}) | one good option only: {forced / len(choices):.0%} | "
          f"good options per turn (within 3 points): median {statistics.median(c[1] for c in choices)}")
    counts = {}
    for b in builds:
        counts[b] = counts.get(b, 0) + 1
    ent = -sum(n / len(builds) * math.log(n / len(builds)) for n in counts.values())
    norm = ent / math.log(len(counts)) if len(counts) > 1 else 0.0
    print(f"  build variety (most-copied added part): entropy {norm:.2f} of 1 | "
          + ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])))


# ---------------------------------------------------------------- combos

COMBO_DECKS = {
    # No attachments, for comparison (the strongest fixed decks).
    "big_hit (no attachments)": {K.HAMMER: 2, K.AMPLIFIER: 2, K.STRIKER: 4},
    "copy_loop (no attachments)": {K.COUPLER: 2, K.MIRROR: 2, K.STRIKER: 4},
    "spring_chain (no attachments)": {K.SPRING: 3, K.HAMMER: 1, K.COOLANT: 1, K.STRIKER: 4},
    # Attachment combos.
    "Echo+Sharpened Strikers": {(K.STRIKER, (M.ECHO, M.SHARPENED)): 2, K.STRIKER: 2, K.SPRING: 1, K.PLATE: 1},
    "Echo+Governor Hammer, Coupler, Mirror": {(K.HAMMER, (M.ECHO, M.GOVERNOR)): 1, K.COUPLER: 1, K.MIRROR: 1,
                                             K.STRIKER: 3, K.SPRING: 1},
    "Governor Hammers + Amplifier": {(K.HAMMER, M.GOVERNOR): 2, K.AMPLIFIER: 2, K.STRIKER: 2, K.SPRING: 1},
    "Echo Coupler + Hammers": {(K.COUPLER, M.ECHO): 1, K.HAMMER: 2, (K.HAMMER, M.GOVERNOR): 1, K.STRIKER: 3},
    "Governor Springs + Hammers": {(K.SPRING, M.GOVERNOR): 2, K.HAMMER: 2, K.STRIKER: 3},
    "Echo Spring + Hammers": {(K.SPRING, M.ECHO): 1, K.SPRING: 1, K.HAMMER: 2, K.STRIKER: 3},
    "Coil Springs + Hammer": {(K.SPRING, M.COIL): 2, K.HAMMER: 1, K.COOLANT: 1, K.STRIKER: 3},
    "Polish Mirrors + Sharpened Hammers": {(K.MIRROR, M.POLISH): 2, (K.HAMMER, M.SHARPENED): 2, K.AMPLIFIER: 1,
                                           K.STRIKER: 2},
    "Heat Sink everything": {(K.HAMMER, M.HEAT_SINK): 2, (K.STRIKER, M.HEAT_SINK): 3, (K.SPRING, M.HEAT_SINK): 2,
                             K.COUPLER: 1},
}


def study_combos(pool, args):
    from . import loopfinder
    print("Strongest single turn (loop finder: every layout, every crank plan, start Heat 0; "
          "boss HP is 98-109):")
    for name, deck in COMBO_DECKS.items():
        firsts = [None] + list(deck)
        rows = [r for chunk in pool.map(loopfinder.chunk_for, [(deck, f, 0) for f in firsts]) for r in chunk]
        by_d = sorted(rows, key=lambda r: (r[2][1], -r[2][0]), reverse=True)
        by_t = sorted(rows, key=lambda r: (r[1][0], r[1][1]), reverse=True)
        print(f"\n  {name}: {len(rows)} layouts | max damage {by_d[0][2][1]} | max triggers {by_t[0][1][0]} | "
              f">=54 damage in {sum(r[2][1] >= 54 for r in rows)} layouts")
        print("    " + loopfinder.fmt(by_d[0][0], by_d[0][2]))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("study", choices=["attachments", "machine", "styles", "combos", "bosses", "fun"])
    ap.add_argument("--agent", default="mcts@50")
    ap.add_argument("--fights", type=int, default=40)
    ap.add_argument("--runs", type=int, default=150)
    args = ap.parse_args(argv)
    with ProcessPoolExecutor(os.cpu_count()) as pool:
        {"attachments": study_attachments, "machine": study_machine, "styles": study_styles,
         "combos": study_combos, "bosses": study_bosses, "fun": study_fun}[args.study](pool, args)


if __name__ == "__main__":
    main()

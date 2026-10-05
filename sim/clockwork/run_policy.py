"""A simple automated player for whole runs (run_mode.Run), so runs can be simulated.

Fights are played by an agent (default mcts@50, the casual stand-in). Map, reward, rest and
Workshop choices follow plain heuristics:
- doors: an elite when HP is high, a rest site when HP is low, otherwise a Workshop if it can
  afford something, otherwise a fight;
- part rewards: highest value in PART_VALUE (from the partial-deck probes), else scrap;
- attachments: always taken and attached to the best part they fit;
- rest: heal below 60% HP, otherwise tinker (both offered common attachments);
- Workshop: repair when low, then buy the machine upgrade, then the best affordable attachments and parts.

    python -m clockwork.run_policy --agent mcts@50 --runs 60
"""
import argparse
import os
import statistics
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace

from .config import DEFAULT_RULES

from .decks import DECKS
from .engine import apply, legal_actions, new_fight
from .parts import Kind, Mod
from .run import make_agent
from .run_mode import Run

# Value of one copy: win-rate points over the starter in fights from 30 HP (part pass v15).
PART_VALUE = {Kind.MAGNET: 9.5, Kind.SLIDER: 8.1, Kind.PRIMER: 7.7, Kind.ASSEMBLY: 6.7, Kind.AMPLIFIER: 5.5,
              Kind.COUPLER: 5.4, Kind.COOLANT: 4.4, Kind.HAMMER: 3.8, Kind.MIRROR: -1.7, Kind.LOADER: -2.8,
              Kind.SPRING: -3.5}
# HP kept per fight on the best host (studies, Results v16), and the hosts in order of preference.
MOD_VALUE = {Mod.GOVERNOR: 6.5, Mod.COIL: 5.4, Mod.HEAT_SINK: 3.6, Mod.BRACING: 3.5, Mod.COUNTERWEIGHT: 3.3,
             Mod.SHARPENED: 3.0, Mod.ECHO: 3.0, Mod.CLAMP: 2.8, Mod.FEEDER: 2.8, Mod.POLISH: 2.3}
MOD_HOSTS = {
    Mod.GOVERNOR: [Kind.HAMMER, Kind.STRIKER, Kind.PRIMER],
    Mod.BRACING: [Kind.STRIKER, Kind.PLATE],
    Mod.COUNTERWEIGHT: [Kind.PLATE],
    Mod.SHARPENED: [Kind.PLATE, Kind.STRIKER, Kind.HAMMER],
    Mod.ECHO: [Kind.STRIKER, Kind.PLATE, Kind.PRIMER],
    Mod.HEAT_SINK: [Kind.STRIKER, Kind.HAMMER],
}
# Runs started with each machine upgrade (Results v12): Extra Hands +16, Heat Housing +15,
# Bigger Gear +8, Flywheel +7 points.
MACHINE_PRIORITY = ["extra_hands", "heat_housing", "bigger_gear", "flywheel"]
CARD_PRIORITY = [Kind.HAMMER, Kind.PRIMER, Kind.STRIKER, Kind.ASSEMBLY, Kind.SLIDER, Kind.COUPLER,
                 Kind.PLATE, Kind.SPRING, Kind.MIRROR, Kind.MAGNET, Kind.LOADER, Kind.AMPLIFIER, Kind.COOLANT]


def play_fight(run, agent_name):
    s = new_fight(run.fight_deck(), run.enemy_spec(), seed=run.fight_seed(), rules=run.rules(), start_hp=run.hp)
    agent = make_agent(agent_name, run.fight_seed())
    while s.result is None:
        apply(s, agent.act(s, legal_actions(s)))
    run.finish_fight(s.result, s.hp, s.turn)


def attach_all(run):
    i = 0
    while i < len(run.inventory):
        mod = run.inventory[i]
        cards = [c for c in run.cards if run.can_attach(mod, c)]
        if not cards:
            i += 1
            continue
        hosts = MOD_HOSTS.get(mod, [])
        cards.sort(key=lambda c: (hosts.index(c["kind"]) if c["kind"] in hosts else len(hosts),
                                  CARD_PRIORITY.index(c["kind"]) if c["kind"] in CARD_PRIORITY else 99,
                                  len(c["mods"])))
        run.attach(i, cards[0]["id"])


def best_mod(run, offered):
    """The offered attachment worth most to this deck (one that fits some part)."""
    usable = [m for m in offered if any(run.can_attach(Mod(m), c) for c in run.cards)] or offered
    return max(usable, key=lambda m: MOD_VALUE.get(Mod(m), 0)) if usable else ""


# Play-style knobs for studies (clockwork.studies); the defaults are the policy described above.
DEFAULT_STYLE = {
    "elites": "auto",       # auto (when HP >= 70%) | seek (unless HP < 40%) | avoid
    "rest": "auto",         # auto (heal below 60%) | heal | tinker
    "parts": "value",       # value (PART_VALUE > 0) | none (always scrap) | all (best offered, always)
    "remove_basics": False,  # Workshop: remove a Plate, then a Striker, when affordable
    "machine_first": False,  # Workshop: save for machine upgrades before buying attachments
}


def choose_door(run, style=DEFAULT_STYLE):
    doors = run.doors
    frac = run.hp / run.max_hp()
    order = []
    if style["elites"] == "seek" and frac >= 0.4 or style["elites"] == "auto" and frac >= 0.7:
        order.append("elite")
    if frac < 0.5:
        order.append("rest")
    if run.cogs >= 55:
        order.append("workshop")
    order += ["fight", "rest", "workshop"] + (["elite"] if style["elites"] != "avoid" else []) + ["boss"]
    for t in order:
        if t in doors:
            return doors.index(t)
    return 0


def shop(run, style=DEFAULT_STYLE):
    o = run.offer
    if run.hp < 0.5 * run.max_hp():
        while run.cogs >= 25 and run.hp < run.max_hp() - 10:
            run.buy("repair")
    machines = sorted(range(len(o["machines"])), key=lambda i: MACHINE_PRIORITY.index(o["machines"][i]["key"]))
    for i in machines:
        if not o["machines"][i]["sold"] and run.cogs >= o["machines"][i]["price"]:
            run.buy("machine", i)
            break
    reserve = 90 if style["machine_first"] and len(run.machine) < 2 else 0
    for i in sorted(range(len(o["attachments"])), key=lambda i: -MOD_VALUE.get(Mod(o["attachments"][i]["mod"]), 0)):
        item = o["attachments"][i]
        if (not item["sold"] and run.cogs - item["price"] >= reserve
                and any(run.can_attach(Mod(item["mod"]), c) for c in run.cards)):
            run.buy("attachment", i)
    if style["remove_basics"]:
        for kind in (Kind.PLATE, Kind.STRIKER):
            card = next((c for c in run.cards if c["kind"] == kind and not c["mods"]), None)
            if card and len(run.cards) > 6 and run.cogs - run.remove_price() >= reserve:
                run.remove_card(card["id"])
                break
    parts = sorted(range(len(o["parts"])), key=lambda i: -PART_VALUE.get(Kind(o["parts"][i]["kind"]), 0))
    for i in parts:
        item = o["parts"][i]
        if (not item["sold"] and run.cogs - item["price"] >= reserve and style["parts"] != "none"
                and PART_VALUE.get(Kind(item["kind"]), 0) > 0):
            run.buy("part", i)
    run.leave_workshop()


def simulate_run(deck, seed, agent_name="mcts@50", rules=None, growth=None, style=None, machine=(), boss=None):
    """Play a whole run. `style` overrides DEFAULT_STYLE keys; `machine` starts the run with
    those machine upgrades already installed."""
    style = {**DEFAULT_STYLE, **(style or {})}
    run = Run(deck, seed, rules=rules or DEFAULT_RULES, growth=growth, boss=boss)
    run.machine = list(machine)
    run.hp = run.max_hp()
    while run.phase not in ("won", "lost"):
        attach_all(run)
        if run.phase == "doors":
            run.choose_door(choose_door(run, style))
        elif run.phase == "fight":
            play_fight(run, agent_name)
        elif run.phase == "reward":
            parts = sorted(run.offer["parts"], key=lambda p: -PART_VALUE.get(Kind(p), 0))
            best = parts[0] if PART_VALUE.get(Kind(parts[0]), 0) > 0 or style["parts"] == "all" else ""
            if style["parts"] == "none":
                best = ""
            mods = run.offer.get("attachments", [])
            salvage = sorted(run.offer.get("salvage", []), key=MACHINE_PRIORITY.index)
            run.take_reward(part=best, attachment=best_mod(run, mods), scrap=not best,
                            salvage=salvage[0] if salvage else "")
        elif run.phase == "rest":
            heal = {"heal": True, "tinker": False}.get(style["rest"], run.hp < 0.6 * run.max_hp())
            run.rest("heal" if heal else "tinker")
        elif run.phase == "workshop":
            shop(run, style)
    return run


def _block(args):
    deck, agent, seeds, heal, growth = args
    rules = None if heal is None else replace(DEFAULT_RULES, heal_between_fights=heal)
    out = []
    for seed in seeds:
        run = simulate_run(deck, seed, agent, rules, growth)
        fights = [h for h in run.history if "enemy" in h]
        out.append({"won": run.phase == "won", "stop": run.stop, "hp": run.hp, "cogs": run.cogs,
                    "elites": sum(h["node"] == "elite" for h in fights),
                    "attachments": sum(len(c["mods"]) for c in run.cards),
                    "machine": len(run.machine), "deck": len(run.cards),
                    "boss_hp": next((h["hp_start"] for h in fights if h["node"] == "boss"), None),
                    "died_to": fights[-1]["enemy"] if run.phase == "lost" else None})
    return deck, out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="mcts@50")
    ap.add_argument("--runs", type=int, default=60)
    ap.add_argument("--decks", nargs="+", default=["starter"], choices=list(DECKS))
    ap.add_argument("--heal", type=int, default=None, help="override HP healed after each win")
    ap.add_argument("--growth", type=float, default=None, help="override enemy growth through the district")
    args = ap.parse_args(argv)
    tasks = [(d, args.agent, range(lo, min(lo + 5, args.runs)), args.heal, args.growth)
             for d in args.decks for lo in range(0, args.runs, 5)]
    res = {}
    with ProcessPoolExecutor(os.cpu_count()) as pool:
        for deck, out in pool.map(_block, tasks):
            res.setdefault(deck, []).extend(out)
    for deck, out in res.items():
        n = len(out)
        won = [o for o in out if o["won"]]
        boss = [o["boss_hp"] for o in out if o["boss_hp"] is not None]
        deaths = {}
        for o in out:
            if o["died_to"]:
                deaths[o["died_to"]] = deaths.get(o["died_to"], 0) + 1
        print(f"{args.agent} heal {args.heal if args.heal is not None else DEFAULT_RULES.heal_between_fights}"
              f" | {deck}: cleared {len(won)/n:.0%} of {n} runs | reached boss {len(boss)/n:.0%} "
              f"with {statistics.mean(boss) if boss else 0:.1f} HP | elites fought {statistics.mean(o['elites'] for o in out):.2f} "
              f"| attachments {statistics.mean(o['attachments'] for o in out):.1f} | machine upgrades "
              f"{statistics.mean(o['machine'] for o in out):.2f} | final deck {statistics.mean(o['deck'] for o in out):.1f} "
              f"| cogs left {statistics.mean(o['cogs'] for o in out):.0f} | deaths {deaths}")


if __name__ == "__main__":
    main()

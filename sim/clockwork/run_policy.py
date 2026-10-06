"""A simple automated player for whole runs (run_mode.Run), so runs can be simulated.

Fights are played by an agent (default mcts@50, the casual stand-in). Map, reward, rest and
Workshop choices follow plain heuristics:
- doors: an elite at 70% HP or more, a rest site below 60% HP, otherwise a Workshop if it can
  afford something, otherwise a fight (thresholds from the v17 policy search; elites v18);
- part rewards: highest value in PART_VALUE (from the partial-deck probes), else scrap;
- attachments: always taken and attached to the best part they fit;
- rest: heal below 60% HP, otherwise tinker (both offered common attachments);
- Workshop: repair when low, then buy a machine upgrade level, then the best affordable attachments and parts.

The expert's run decisions (EXPERT_STYLE, v19) replace the HP thresholds with a plan: it forecasts what
fights cost with its current machine and keeps enough HP for the act's boss (clockwork.planner).

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

# Value of one copy: win-rate points over the starter in fights from 30 HP (part pass v15; Hammer and
# Boiler re-measured after the v18 rare buffs).
PART_VALUE = {Kind.MAGNET: 9.5, Kind.SLIDER: 8.1, Kind.PRIMER: 7.7, Kind.ASSEMBLY: 6.7, Kind.AMPLIFIER: 5.5,
              Kind.COUPLER: 5.4, Kind.COOLANT: 4.4, Kind.HAMMER: 4.8, Kind.MIRROR: -1.7, Kind.LOADER: -2.8,
              Kind.SPRING: -3.5, Kind.BOILER: 5.7}
# HP kept per fight on the best host (studies, Results v16; Overdrive and Kickback v18), and the hosts in
# order of preference.
MOD_VALUE = {Mod.GOVERNOR: 6.5, Mod.COIL: 3.5, Mod.HEAT_SINK: 3.6, Mod.BRACING: 3.5, Mod.COUNTERWEIGHT: 3.3,
             Mod.SHARPENED: 3.0, Mod.ECHO: 3.0, Mod.CLAMP: 2.8, Mod.FEEDER: 2.8, Mod.POLISH: 3.4,
             Mod.OVERDRIVE: 4.9, Mod.KICKBACK: 5.0}
MOD_HOSTS = {
    Mod.GOVERNOR: [Kind.HAMMER, Kind.STRIKER, Kind.PRIMER],
    Mod.BRACING: [Kind.STRIKER, Kind.PLATE],
    Mod.COUNTERWEIGHT: [Kind.PLATE],
    Mod.SHARPENED: [Kind.PLATE, Kind.STRIKER, Kind.HAMMER],
    Mod.ECHO: [Kind.STRIKER, Kind.PLATE, Kind.PRIMER],
    Mod.HEAT_SINK: [Kind.STRIKER, Kind.HAMMER],
    Mod.OVERDRIVE: [Kind.HAMMER, Kind.SLIDER, Kind.STRIKER, Kind.PLATE],
    Mod.KICKBACK: [Kind.HAMMER, Kind.PLATE, Kind.STRIKER, Kind.SLIDER],
}
# Runs started with each machine upgrade (Results v12): Extra Hands +16, Heat Housing +15,
# Bigger Gear +8, Flywheel +7 points.
# Order to pick machine upgrades in (at the start, as boss rewards, and level-ups in the Workshop).
# By run clear points when started with it (act-1 runs, Results v18): Cooling Fins +26, Flywheel +25,
# Extra Hands +21, Frame +19, Heat Housing +18, Bigger Gear +15, Wide Hopper +7.
MACHINE_PRIORITY = ["cooling_fins", "flywheel", "extra_hands", "frame", "heat_housing", "bigger_gear", "hopper"]
# Workshop level-ups by the second level's gain (v18): Frame +12, Heat Housing +4, Flywheel +2.
LEVEL_PRIORITY = ["frame", "heat_housing", "cooling_fins", "extra_hands", "flywheel", "hopper", "bigger_gear"]


def machine_order(style=None):
    return MACHINE_PRIORITY
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
    "elites": "auto",       # auto (when HP >= elite_hp) | seek (unless HP < 40%) | avoid
    "rest": "auto",         # auto (heal below 60%) | heal | tinker
    "parts": "value",       # value (PART_VALUE > 0) | none (always scrap) | all (best offered, always)
    "remove_basics": False,  # Workshop: remove a Plate, then a Striker, when affordable
    "machine_first": False,  # Workshop: save for machine upgrades before buying attachments
    # Tunable thresholds (v17 policy search; the values here are the chosen defaults).
    "elite_hp": 0.7,         # auto: take an elite door at or above this HP fraction (v18: harder elites; v17 0.5)
    "rest_door_hp": 0.6,     # prefer a rest door below this HP fraction (v17; was 0.5)
    "heal_below": 0.6,       # at a rest site, heal below this HP fraction (else tinker)
    "workshop_cogs": 55,     # prefer a Workshop door with at least this many cogs
    "save_margin": 0,        # in a Workshop, skip other purchases if the best machine upgrade is
                             # at most this many cogs out of reach (save for it)
    "synergy": False,        # value parts by what the deck already holds (SYNERGY)
    "plan": False,           # expert: forecast fight costs and plan HP to the boss (clockwork.planner)
    "boss_margin": 1.5,      # plan: arrive with this many times the boss's forecast cost...
    "boss_extra": 5,         # ...plus this much HP
}
# The expert player's run decisions (with MCTS@200 fights): plans its route instead of fixed thresholds.
EXPERT_STYLE = {"plan": True}

# A part is worth more when its partner is already in the deck (or, for Spring, a Coil is held).
SYNERGY_BONUS = 6
SYNERGY = {
    Kind.LOADER: (Kind.PRIMER, Kind.ASSEMBLY), Kind.PRIMER: (Kind.LOADER,), Kind.ASSEMBLY: (Kind.LOADER,),
    Kind.SLIDER: (Kind.MAGNET,), Kind.MAGNET: (Kind.SLIDER,),
    Kind.MIRROR: (Kind.HAMMER, Kind.AMPLIFIER), Kind.AMPLIFIER: (Kind.HAMMER, Kind.MIRROR),
    Kind.COOLANT: (Kind.HAMMER, Kind.COUPLER),
}


def part_value(run, kind, style=None):
    style = style or DEFAULT_STYLE
    value = PART_VALUE.get(kind, 0)
    if style.get("synergy"):
        kinds = {c["kind"] for c in run.cards}
        if any(k in kinds for k in SYNERGY.get(kind, ())):
            value += SYNERGY_BONUS
        if kind == Kind.SPRING and (Mod.COIL in run.inventory or any(Mod.COIL in c["mods"] for c in run.cards)):
            value += SYNERGY_BONUS
    return value


def choose_door(run, style=DEFAULT_STYLE):
    doors = run.doors
    frac = run.hp / run.max_hp()
    order = []
    if style["elites"] == "seek" and frac >= 0.4 or style["elites"] == "auto" and frac >= style["elite_hp"]:
        order.append("elite")
    if frac < style["rest_door_hp"]:
        order.append("rest")
    if run.cogs >= style["workshop_cogs"]:
        order.append("workshop")
    order += ["fight", "rest", "workshop"] + (["elite"] if style["elites"] != "avoid" else []) + ["boss"]
    for t in order:
        if t in doors:
            return doors.index(t)
    return 0


def fights_left(run, option="fight"):
    """Normal fights the planner assumes before the boss after taking `option` now. Door map: one per
    stop (the last stop before a boss is always a rest site or a Workshop). Hours map: as many as the
    hours left after `option` allow."""
    if run.map == "hours":
        from .run_mode import HOUR_COST
        return max(0, run.hours_left() - HOUR_COST.get(option, 0)) // HOUR_COST["fight"]
    return max(0, run.stops - run.stop - 2)


def boss_need(run, style, f):
    from . import planner
    return planner.boss_need(f, run, style["boss_margin"], style["boss_extra"])


def choose_door_planned(run, style):
    """Expert: take the most rewarding door whose projected HP at the boss still covers it."""
    from . import planner
    f = planner.forecast(run)
    need = boss_need(run, style, f)
    proj = lambda option: planner.projected_boss_hp(run, option, fights_left(run, option), f)
    ok = {
        "elite": run.hp > f["elite_worst"] + 3 and proj("elite") >= need,
        "workshop": run.cogs >= style["workshop_cogs"] and proj("workshop") >= need,
        "fight": run.hp > 2 * f["fight"] and proj("fight") >= need,
    }
    order = [t for t in ("elite", "workshop", "fight") if ok[t]]
    order += ["rest", "workshop", "fight", "elite", "boss"]
    for t in order:
        if t in run.doors:
            return run.doors.index(t)
    return 0


def rest_planned(run, style):
    from . import planner
    f = planner.forecast(run)
    return planner.projected_boss_hp(run, "tinker", fights_left(run, "rest"), f) < boss_need(run, style, f) + 5


def shop(run, style=DEFAULT_STYLE):
    o = run.offer
    if style.get("plan"):
        from . import planner
        from .run_mode import REPAIR
        f = planner.forecast(run)
        while (run.cogs >= REPAIR[1] and run.hp < run.max_hp() - 10
               and planner.projected_boss_hp(run, "workshop", fights_left(run, "workshop"), f)
               < boss_need(run, style, f)):
            run.buy("repair")
    elif run.hp < 0.5 * run.max_hp():
        while run.cogs >= 25 and run.hp < run.max_hp() - 10:
            run.buy("repair")
    machines = sorted(range(len(o["machines"])), key=lambda i: LEVEL_PRIORITY.index(o["machines"][i]["key"]))
    for i in machines:
        if not o["machines"][i]["sold"] and run.cogs >= o["machines"][i]["price"]:
            run.buy("machine", i)
            break
    reserve = 90 if style["machine_first"] and len(run.machine) < 2 else 0
    unsold = [o["machines"][i] for i in machines if not o["machines"][i]["sold"]]
    if style["save_margin"] and unsold and run.cogs < unsold[0]["price"] <= run.cogs + style["save_margin"]:
        reserve = run.cogs + 1        # nearly there: buy nothing else, save for it
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
    parts = sorted(range(len(o["parts"])), key=lambda i: -part_value(run, Kind(o["parts"][i]["kind"]), style))
    for i in parts:
        item = o["parts"][i]
        if (not item["sold"] and run.cogs - item["price"] >= reserve and style["parts"] != "none"
                and part_value(run, Kind(item["kind"]), style) > 0):
            run.buy("part", i)
    run.leave_workshop()


def pick_machine(run, style=None):
    """The offered machine upgrade to choose (start or boss reward), by MACHINE_PRIORITY."""
    offered = run.offer.get("machines", [])
    return min(offered, key=machine_order(style).index) if offered else ""


def step(run, agent_name, style):
    """Make the run's next decision (or play its next fight)."""
    attach_all(run)
    if run.phase == "start":
        run.choose_start(pick_machine(run, style))
    elif run.phase == "boss_reward":
        run.choose_boss_reward(pick_machine(run, style))
    elif run.phase == "doors":
        run.choose_door(choose_door_planned(run, style) if style.get("plan") else choose_door(run, style))
    elif run.phase == "fight":
        play_fight(run, agent_name)
    elif run.phase == "reward":
        parts = sorted(run.offer["parts"], key=lambda p: -part_value(run, Kind(p), style))
        best = parts[0] if part_value(run, Kind(parts[0]), style) > 0 or style["parts"] == "all" else ""
        if style["parts"] == "none":
            best = ""
        run.take_reward(part=best, attachment=best_mod(run, run.offer.get("attachments", [])), scrap=not best)
    elif run.phase == "rest":
        planned = style.get("plan") and rest_planned(run, style)
        heal = {"heal": True, "tinker": False}.get(
            style["rest"], planned if style.get("plan") else run.hp < style["heal_below"] * run.max_hp())
        run.rest("heal" if heal else "tinker")
    elif run.phase == "workshop":
        shop(run, style)


def simulate_run(deck, seed, agent_name="mcts@50", rules=None, growth=None, style=None, machine=None, boss=None,
                 acts=None, map="doors"):
    """Play a whole run. `style` overrides DEFAULT_STYLE keys. `machine` replaces the starting choice
    with these machine upgrades (a list; () for none). `acts` shortens or lengthens the run."""
    style = {**DEFAULT_STYLE, **(style or {})}
    run = Run(deck, seed, rules=rules or DEFAULT_RULES, growth=growth, boss=boss, map=map,
              **({} if acts is None else {"acts": acts}))
    if machine is not None:
        run.choose_start("")
        run.machine = list(machine)
        run.hp = run.max_hp()
    while run.phase not in ("won", "lost"):
        step(run, agent_name, style)
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

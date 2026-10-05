"""Write Database.md: every part, attachment, enemy, machine upgrade and run number, generated
from the simulator so it always matches the rules.

    python sim/build_database.py

tests/test_database.py fails if Database.md is out of date.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "sim"))

from clockwork import run_mode as RM  # noqa: E402
from clockwork.config import DEFAULT_RULES as R  # noqa: E402
from clockwork.decks import DECKS, deck_list  # noqa: E402
from clockwork.describe import enemy_rows, mod_fits_text, mod_texts, part_texts  # noqa: E402
from clockwork.parts import MOD_RARITY, Kind, Mod, specs_for  # noqa: E402

OUT = os.path.join(ROOT, "Database.md")


def table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(out)


def targets_table():
    from clockwork.targets import TARGETS, status
    rows = []
    for area, metric, target, rng, latest, source in TARGETS:
        st = status(rng, latest)
        mark = {"on target": "✅ on target", "partly off": "⚠️ partly off", "off target": "❌ off target"}.get(st, "")
        rows.append((area, metric, target, latest, mark, source))
    return table(["Area", "Metric", "Target", "Latest", "Status", "Source"], rows)


def build() -> str:
    specs = specs_for(R.part_overrides)
    parts = part_texts(R)
    lines = [
        "# Clockwork database",
        "",
        "Every part, attachment, enemy and machine upgrade with its current numbers. **Generated** from the "
        "simulator by `python sim/build_database.py`; don't edit by hand (a test fails when it is stale). "
        "Rules and reasoning: Rules.md, Rules-Decisions.md, Run-Design.md; measurements: "
        "AI-Playtesting-Roadmap.md.",
        "",
        "## Balance targets",
        "",
        "What each number is tuned toward, and the latest measurement (from the roadmap results named in "
        "Source; `sim/clockwork/targets.py`). Casual = MCTS@50, careless = greedy, expert = MCTS@200.",
        "",
        targets_table(),
        "",
        "## Basics",
        "",
        table(["Rule", "Value"], [
            ("Player HP", R.player_hp),
            ("Gear slots", R.gear_size),
            ("Parts offered per turn / visible in the queue", f"{R.offered_per_turn} / {R.queue_visible}"),
            ("Installs per turn", R.installs_per_turn),
            ("Crank Power per turn (after the free crank)", R.crank_power),
            ("Heat per trigger", R.heat_per_trigger),
            ("Overheat at", f"{R.overheat_at} Heat: the turn stops, Heat goes to 0, next turn is dead; "
                            "Heat past the limit is forgiven"),
            ("Crank direction", "one direction per turn, chosen when installing ends"),
            ("Max attachments per part", R.max_attachments),
        ]),
        "",
        "## Parts",
        "",
        "Tier decides how often a part shows up as a reward and its Workshop price.",
        "",
    ]
    rows = []
    for k in Kind:
        sp = specs[k]
        tier = RM.PART_TIER.get(k, "starter")
        price = RM.PART_PRICE[tier] if tier in RM.PART_PRICE else "-"
        heat = R.heat_per_trigger + sp.extra_heat if sp.triggers else 0
        rows.append((f"**{k.value}**", tier, price, heat, parts[k]))
    lines += [table(["Part", "Tier", "Price", "Heat per trigger", "Effect"], rows), ""]

    lines += ["## Attachments", "",
              "Items with a rarity. Attached permanently to one part copy (up to "
              f"{R.max_attachments} per part, no duplicates); unattached ones can be sold for half price. "
              "Value = HP kept per fight on its best host (studies, Results v11/v12).", ""]
    from clockwork.run_policy import MOD_HOSTS, MOD_VALUE
    rows = []
    for rarity in ("common", "uncommon", "rare"):
        for m in Mod:
            if MOD_RARITY[m] != rarity:
                continue
            best = MOD_HOSTS.get(m, [])
            rows.append((f"**{m.value}**", rarity, mod_fits_text(m), RM.MOD_PRICE[rarity], mod_texts(R)[m],
                         f"+{MOD_VALUE[m]}" + (f" ({best[0].value})" if best else "")))
    lines += [table(["Attachment", "Rarity", "Fits", "Price", "Effect", "Value"], rows), ""]

    lines += ["## Enemies", "",
              f"In a run, enemies grow through the district: HP and attacks × (1 + {RM.GROWTH} × stop/{RM.STOPS}), "
              f"so the boss is ×{1 + RM.GROWTH:.2f}. Elites are fought at ×{RM.ELITE_SCALE} on top. "
              f"Each fight's HP also rolls ±{R.enemy_hp_jitter}. Cogs vary ±10%.", ""]
    for group, title in (("normal", "Normal"), ("elite", "Elites"), ("boss", "Bosses")):
        rows = [(f"**{e['name']}**", e["hp"], e["cogs"], e["pattern"], e["note"])
                for e in enemy_rows() if e["group"] == group]
        lines += [f"### {title}", "", table(["Enemy", "HP", "Cogs", "Pattern", "Tests"], rows), ""]

    lines += ["## Machine upgrades", "",
              "Permanent upgrades to the machine. Every Workshop sells all the ones you don't have; elites "
              f"have a {round(RM.ELITE_SALVAGE * 100)}% chance to let you salvage 1 of 2 for free.", "",
              table(["Upgrade", "Price", "Effect"], [(f"**{n}**", p, t) for n, t, p in RM.MACHINE.values()]), "",
              "Candidates (simulator only, not sold): " +
              "; ".join(f"{n}: {t}" for n, t in RM.MACHINE_CANDIDATES.values()) + ".", ""]

    lines += ["## Run", "", table(["Rule", "Value"], [
        ("Stops", f"{RM.STOPS} door choices, then the boss (picked at the start from: "
                  f"{', '.join(RM.BOSS_POOL)})"),
        ("Doors", "stops 1-2 are fights; then 3 doors weighted " +
                  ", ".join(f"{k} {v:g}" for k, v in RM.DOOR_WEIGHTS.items()) +
                  "; the last stop offers a rest site or a Workshop"),
        ("After a win", f"heal {R.heal_between_fights} HP, loot cogs, pick 1 of 3 parts (or scrap for "
                        f"{RM.SCRAP_VALUE} cogs, or skip)"),
        ("Part reward tiers", ", ".join(f"{t} {w}" for t, w in RM.TIER_WEIGHT.items()) + " (weights)"),
        ("Elite loot", f"a part from the {'/'.join(RM.ELITE_PART_TIERS)} tiers, 1 of {RM.ELITE_ATTACHMENTS} "
                       f"uncommon/rare attachments, {round(RM.ELITE_SALVAGE * 100)}% chance of a free machine "
                       "upgrade (1 of 2)"),
        ("Rest site", f"heal {RM.REST_HEAL}, or tinker: take both offered common attachments"),
        ("Workshop", f"3 parts, 2 uncommon/rare attachments, every machine upgrade you lack; repair "
                     f"{RM.REPAIR[0]} HP for {RM.REPAIR[1]}; remove a part for {RM.REMOVE_PRICE} "
                     f"(+{RM.REMOVE_STEP} each time)"),
    ]), ""]

    rows = []
    for name, d in DECKS.items():
        counts = {}
        for k, mods in deck_list(d):
            label = k.value + "".join("+" + m.value for m in mods)
            counts[label] = counts.get(label, 0) + 1
        rows.append((f"**{name}**", ", ".join(f"{n}× {k}" for k, n in counts.items())))
    lines += ["## Test decks", "", "`starter` is the run's starting deck; the others are fixed test decks "
              "(the starter plus 4 parts).", "", table(["Deck", "Parts"], rows), ""]
    return "\n".join(lines)


def main():
    with open(OUT, "w") as f:
        f.write(build())
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

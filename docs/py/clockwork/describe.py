"""Plain-language descriptions of parts, attachments, enemies and machine upgrades, built from
the live numbers so the playtest page and Database.md always match the simulator."""
from .config import DEFAULT_RULES
from .enemies import ENEMIES, EnemySpec
from .parts import COUNTERWEIGHT_BLOCK, MOD_FITS, SHARPENED_DAMAGE, Kind, Mod, specs_for


def _pct(x):
    return f"{round(x * 100)}%"


def _also(spec) -> str:
    """'Deal 2 damage. ' / 'Gain 3 Block. ' for parts whose main effect is something else."""
    out = ""
    if spec.damage:
        out += f"Deal {spec.damage} damage. "
    if spec.block:
        out += f"Gain {spec.block} Block. "
    return out


def part_texts(rules=DEFAULT_RULES) -> dict:
    s = specs_for(rules.part_overrides)
    return {
        Kind.STRIKER: f"Deal {s[Kind.STRIKER].damage} damage.",
        Kind.PLATE: f"Gain {s[Kind.PLATE].block} Block.",
        Kind.SPRING: _also(s[Kind.SPRING]) + "Crank again for free, continuing in the direction the trigger "
                     "came from. Extra Heat: +1 for the 1st Spring in a chain, +2 for the 2nd, +3 for the 3rd...",
        Kind.MIRROR: "Acts exactly as the part directly opposite it (attachments included). Can't copy a Mirror.",
        Kind.AMPLIFIER: f"Passive: neighbours' damage and Block +{_pct(rules.amplifier_bonus)}. Never triggers.",
        Kind.COUPLER: _also(s[Kind.COUPLER]) + "Triggers its left neighbour, then its right one. Can't trigger "
                      "a Coupler." + (f" +{s[Kind.COUPLER].extra_heat} Heat." if s[Kind.COUPLER].extra_heat else ""),
        Kind.LOADER: _also(s[Kind.LOADER]) + f"Installs the next {rules.loader_loads} queue parts into empty "
                     "slots. If the gear is full, one replaces the part opposite the Loader.",
        Kind.COOLANT: f"Remove {s[Kind.COOLANT].cooling} Heat.",
        Kind.HAMMER: f"Deal {s[Kind.HAMMER].damage} damage. +{s[Kind.HAMMER].extra_heat} Heat.",
        Kind.MAGNET: _also(s[Kind.MAGNET]) + "Pulls the parts 2 slots away into the slots next to it (swapping "
                     f"if occupied). +{rules.magnet_block_per_pull} Block per part pulled.",
        Kind.PRIMER: f"Deal {s[Kind.PRIMER].damage} damage, or {s[Kind.PRIMER].fresh_damage} if it was "
                     "installed this turn.",
        Kind.ASSEMBLY: (f"Deal {s[Kind.ASSEMBLY].damage} damage, +" if s[Kind.ASSEMBLY].damage else "Deal ")
                       + f"{s[Kind.ASSEMBLY].per_install_damage} per part installed this turn.",
        Kind.SLIDER: f"Deal {s[Kind.SLIDER].damage} damage, +{s[Kind.SLIDER].moved_bonus} if a Magnet moved "
                     "it this turn.",
        Kind.BOILER: f"Deal {s[Kind.BOILER].damage} damage, +{s[Kind.BOILER].heat_damage} per point of Heat "
                     f"(after its own). +{s[Kind.BOILER].extra_heat} Heat.",
    }


def mod_texts(rules=DEFAULT_RULES) -> dict:
    return {
        Mod.SHARPENED: f"+{SHARPENED_DAMAGE} damage when it triggers.",
        Mod.COUNTERWEIGHT: f"+{COUNTERWEIGHT_BLOCK} Block when it triggers.",
        Mod.BRACING: f"+{rules.bracing_damage} damage and +{rules.bracing_block} Block when it triggers. "
                     "Immune to Jam, Rust and Unscrew.",
        Mod.HEAT_SINK: "Its triggers cost 1 less Heat.",
        Mod.COIL: f"The part this Spring's crank triggers also deals {rules.coil_damage} damage.",
        Mod.POLISH: f"The copy's damage and Block +{_pct(rules.polish_bonus)}.",
        Mod.CLAMP: "The first part it pulls is triggered.",
        Mod.FEEDER: f"Loads {rules.feeder_extra_loads} more part, into the next slots to come up instead of "
                    "random ones, and the loaded parts trigger right away.",
        Mod.GOVERNOR: "Its triggers add no Heat.",
        Mod.OVERDRIVE: f"Its damage and Block +{_pct(rules.overdrive_bonus)} (adds to Amplifiers).",
        Mod.KICKBACK: "After it triggers, the part that would come up next this turn triggers too "
                      "(the gear doesn't turn).",
        Mod.ECHO: ("The first time it triggers each turn, it triggers again." if rules.echo_per_turn == 1 else
                   f"The first time it triggers each turn, it triggers {rules.echo_per_turn} more times."),
    }


def mod_fits_text(mod: Mod) -> str:
    return MOD_FITS[mod].value if mod in MOD_FITS else "any part"


# What each enemy is for: the design question it asks the player.
ENEMY_NOTES = {
    "dummy": "Plain attacker: the baseline.",
    "spiker": "Telegraphed big hit every 3rd turn: tests Block timing.",
    "enrager": "Attacks grow every turn: tests burst damage.",
    "saboteur": "Messes with the machine (jam, wind back, unscrew).",
    "clock_tower": "No attacks; strikes on every 4th crank of the fight, after the part that comes up. "
                   "Tests doing more with fewer cranks.",
    "furnace": "Heats your machine every turn, a big stoke every 3rd: tests Heat management.",
    "dismantler": "Takes your machine apart: tests rebuilding and Bracing.",
    "iron_colossus": "Armor on every hit: tests big single hits over many small ones.",
    "pendulum": "Forces the turn direction (odd turns clockwise, even counter-clockwise): tests layouts "
                "that work both ways.",
    "overclocker": "Adds Heat to your machine.",
    "rust_golem": "Rusts the part at the top: it deals and blocks less for the rest of the fight.",
    "pickpocket": "Unscrews a part every turn.",
    "jammer_prime": "Jams 2 parts every other turn.",
}


def _action_text(act, growth):
    kind = act[0]
    if kind == "attack":
        return f"attack {act[1]}" + (f" (+{growth} per turn)" if growth else "")
    if kind == "jam":
        return f"jam a part ({act[1]} turns)"
    if kind == "wind_back":
        return "wind back (gear turns 1 step counter-clockwise)"
    if kind == "unscrew":
        return "unscrew a part"
    if kind == "overclock":
        return f"+{act[1]} Heat to your machine"
    if kind == "rust":
        return f"rust the top part (-{act[1]} damage/Block this fight)"
    return str(act)


def enemy_pattern_text(spec: EnemySpec) -> str:
    turns = []
    for intent in spec.pattern:
        turns.append(", ".join(_action_text(a, spec.attack_growth) for a in intent) or "nothing")
    if all(t == "nothing" for t in turns):
        text = "No regular attacks."
    elif len(turns) == 1:
        text = f"Every turn: {turns[0]}."
    else:
        text = " ".join(f"Turn {i + 1}: {t}." for i, t in enumerate(turns)) + " Then repeats."
    extras = []
    if spec.chime_every:
        extras.append(f"Strikes for {spec.chime_damage} on every {spec.chime_every}th crank (Springs count)")
    if spec.crank_limit:
        extras.append(f"{spec.crank_limit} cranks in the whole fight")
    if spec.armor:
        extras.append(f"Armor {spec.armor}: every hit on it deals {spec.armor} less")
    if spec.swing:
        extras.append("Swing: odd turns must crank clockwise, even turns counter-clockwise")
    return text + "".join(f" {e}." for e in extras)


def enemy_group(name: str) -> str:
    from .enemies import BOSSES, ELITES
    return "boss" if name in BOSSES else "elite" if name in ELITES else "normal"


def enemy_rows():
    return [{"name": n, "group": enemy_group(n), "hp": e.hp, "cogs": e.cogs, "pattern": enemy_pattern_text(e),
             "note": ENEMY_NOTES.get(n, "")} for n, e in ENEMIES.items()]

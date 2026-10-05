"""Part definitions (Rules.md §4, Rules-Decisions.md)."""
from dataclasses import dataclass, replace
from functools import lru_cache
from enum import Enum
from typing import Optional


class Kind(str, Enum):
    STRIKER = "Striker"
    PLATE = "Plate"
    SPRING = "Spring"
    MIRROR = "Mirror"
    AMPLIFIER = "Amplifier"
    COUPLER = "Coupler"
    LOADER = "Loader"
    COOLANT = "Coolant"
    HAMMER = "Hammer"
    MAGNET = "Magnet"
    PRIMER = "Primer"
    ASSEMBLY = "Assembly"
    SLIDER = "Slider"

    def __str__(self) -> str:
        return self.value


class Mod(str, Enum):
    """Attachments. A part can hold several (up to rules.max_attachments, no duplicates).
    Generic ones fit any part; specific ones fit one part kind (MOD_FITS)."""
    # common
    SHARPENED = "Sharpened"        # +2 damage when it triggers
    COUNTERWEIGHT = "Counterweight"  # +2 Block when it triggers
    BRACING = "Bracing"            # +1 damage and +1 Block; immune to Jam, Rust and Unscrew
    # uncommon
    HEAT_SINK = "Heat Sink"        # its triggers cost 1 less Heat
    COIL = "Coil"        # Spring: the part its crank triggers also deals coil_damage
    POLISH = "Polish"    # Mirror: the copy's damage/Block gets +polish_bonus (adds to Amplifiers)
    CLAMP = "Clamp"      # Magnet: the first part it pulls is triggered
    FEEDER = "Feeder"    # Loader: loads 1 more part, into the next slots to come up; loaded parts trigger
    # rare
    GOVERNOR = "Governor"          # its triggers add no Heat
    ECHO = "Echo"                  # the first time it triggers each turn, it triggers again

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PartSpec:
    damage: int = 0
    block: int = 0
    extra_heat: int = 0        # on top of the per-trigger Heat
    cooling: int = 0
    triggers: bool = True      # False = passive, never triggers (no effect, no Heat)
    fresh_damage: int = 0      # replaces `damage` on the first trigger after being installed
    per_part_damage: int = 0   # extra damage per occupied gear slot (itself included)
    per_install_damage: int = 0  # extra damage per part installed this turn (by hand or Loader)
    moved_bonus: int = 0       # extra damage if a Magnet moved it this turn


SPECS = {
    Kind.STRIKER: PartSpec(damage=6),
    Kind.PLATE: PartSpec(block=6),
    Kind.SPRING: PartSpec(block=3),          # extra Heat depends on its place in the chain; +3 Block (v15)
    Kind.MIRROR: PartSpec(),
    Kind.AMPLIFIER: PartSpec(triggers=False),
    Kind.COUPLER: PartSpec(extra_heat=2),                  # balance pass v5 (was +0)
    Kind.LOADER: PartSpec(block=3),                        # +3 Block (v15)
    Kind.COOLANT: PartSpec(cooling=3),
    Kind.HAMMER: PartSpec(damage=10, extra_heat=3),    # Rules.md: 15/+2; v3: 9/+4; v15: 10/+3
    Kind.MAGNET: PartSpec(),
    # Payoff parts (sim v4 proposals)
    # Primer: fresh_damage only if it triggers on the turn it was installed.
    # Balance pass v5 values; first proposals were Primer 4/18 and Assembly 2 per part.
    Kind.PRIMER: PartSpec(damage=2, fresh_damage=8),       # pairs with Loader (Feeder) / placement
    Kind.ASSEMBLY: PartSpec(per_install_damage=3),         # pairs with Loader
    Kind.SLIDER: PartSpec(damage=5, moved_bonus=3),        # pairs with Magnet (moved bonus was 6)
}

MOD_FITS = {Mod.COIL: Kind.SPRING, Mod.POLISH: Kind.MIRROR, Mod.CLAMP: Kind.MAGNET, Mod.FEEDER: Kind.LOADER}
MOD_RARITY = {
    Mod.SHARPENED: "common", Mod.COUNTERWEIGHT: "common", Mod.BRACING: "common",
    Mod.HEAT_SINK: "uncommon", Mod.COIL: "uncommon", Mod.POLISH: "uncommon", Mod.CLAMP: "uncommon",
    Mod.FEEDER: "uncommon", Mod.GOVERNOR: "rare", Mod.ECHO: "rare",
}
SHARPENED_DAMAGE = 2
COUNTERWEIGHT_BLOCK = 2


def fits(mod: "Mod", kind: "Kind") -> bool:
    return MOD_FITS.get(mod, kind) == kind
# Coil damage, Polish bonus and the Amplifier bonus live in RulesConfig (sweepable).



@dataclass(frozen=True)
class Part:
    uid: int
    kind: Kind
    mods: tuple = ()          # attachments, sorted by name (a single Mod is accepted too)

    def __post_init__(self):
        mods = self.mods
        if mods is None:
            mods = ()
        elif isinstance(mods, Mod):
            mods = (mods,)
        object.__setattr__(self, "mods", tuple(sorted(mods, key=lambda m: m.value)))

    def __str__(self) -> str:
        return f"{self.kind}{''.join('+' + m.value for m in self.mods)}#{self.uid}"


@lru_cache(maxsize=None)
def specs_for(overrides: tuple) -> dict:
    """SPECS with overrides applied, e.g. (("Hammer", "damage", 10), ("Hammer", "extra_heat", 3))."""
    specs = dict(SPECS)
    for kind_name, field_name, value in overrides:
        kind = Kind(kind_name)
        specs[kind] = replace(specs[kind], **{field_name: value})
    return specs

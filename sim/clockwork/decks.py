"""Fixed test decks: the starter bag plus 4 parts, roughly a deck a few fights into a run."""
from .parts import MOD_FITS, Kind as K, Mod

STARTER = {K.STRIKER: 4, K.PLATE: 3, K.SPRING: 1}


def _plus(extra):
    deck = dict(STARTER)
    for kind, n in extra.items():
        deck[kind] = deck.get(kind, 0) + n
    return deck


DECKS = {
    "starter": dict(STARTER),
    "spring_chain": _plus({K.SPRING: 2, K.COOLANT: 1, K.HAMMER: 1}),
    "copy_loop": _plus({K.COUPLER: 2, K.MIRROR: 2}),
    "big_hit": _plus({K.HAMMER: 2, K.AMPLIFIER: 2}),
    "sustain": _plus({K.COOLANT: 2, K.COUPLER: 1, K.SPRING: 1}),
    "utility": _plus({K.LOADER: 2, K.MAGNET: 2}),
}


def deck_list(deck):
    """Expand {Kind: count} or {(Kind, Mod): count} into a list of (kind, mod) in a stable order."""
    out = []
    for key, n in deck.items():
        kind, mod = key if isinstance(key, tuple) else (key, None)
        if mod is not None and MOD_FITS[mod] != kind:
            raise ValueError(f"{mod} does not fit {kind}")
        out += [(kind, mod)] * n
    return out


# Probe decks: the starter plus one or two parts, to measure what a single pick is worth.
# Kept out of DECKS so tuning and the main experiment matrix are unaffected.
PROBE_DECKS = {
    "plus_hammer": _plus({K.HAMMER: 1}),
    "plus_amplifier": _plus({K.AMPLIFIER: 1}),
    "plus_coolant": _plus({K.COOLANT: 1}),
    "plus_coupler": _plus({K.COUPLER: 1}),
    "plus_mirror": _plus({K.MIRROR: 1}),
    "plus_loader": _plus({K.LOADER: 1}),
    "plus_magnet": _plus({K.MAGNET: 1}),
    "plus_spring": _plus({K.SPRING: 1}),
    "plus_hammer_amp": _plus({K.HAMMER: 1, K.AMPLIFIER: 1}),
    "plus_2hammer": _plus({K.HAMMER: 2}),
    "plus_hammer_coolant": _plus({K.HAMMER: 1, K.COOLANT: 1}),
    # v4 payoff parts and attachments
    "plus_primer": _plus({K.PRIMER: 1}),
    "plus_assembly": _plus({K.ASSEMBLY: 1}),
    "plus_slider": _plus({K.SLIDER: 1}),
    "plus_loader_primer": _plus({K.LOADER: 1, K.PRIMER: 1}),
    "plus_loader_assembly": _plus({K.LOADER: 1, K.ASSEMBLY: 1}),
    "plus_magnet_slider": _plus({K.MAGNET: 1, K.SLIDER: 1}),
    "coil_starter": {K.STRIKER: 4, K.PLATE: 3, (K.SPRING, Mod.COIL): 1},
    "plus_coil_spring": _plus({(K.SPRING, Mod.COIL): 1}),
    "plus_polish_mirror": _plus({(K.MIRROR, Mod.POLISH): 1}),
    "plus_clamp_magnet": _plus({(K.MAGNET, Mod.CLAMP): 1}),
    "plus_clamp_magnet_slider": _plus({(K.MAGNET, Mod.CLAMP): 1, K.SLIDER: 1}),
    "plus_feeder_loader_primer": _plus({(K.LOADER, Mod.FEEDER): 1, K.PRIMER: 1}),
}

ALL_DECKS = {**DECKS, **PROBE_DECKS}

"""Fixed test decks: the starter bag plus 4 parts, roughly a deck a few fights into a run."""
from .parts import Kind as K

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
    """Expand {Kind: count} into a list of kinds in a stable order."""
    return [kind for kind, n in deck.items() for _ in range(n)]

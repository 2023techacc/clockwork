"""Exhaustive search over the rest of the current turn.

Shared by the greedy agent (pick the best end-of-turn state) and the loop finder
(best single turn from a fixed layout).
"""
from typing import Iterator, List, Tuple

from .engine import State, apply, legal_actions


def gear_key(s: State) -> tuple:
    return tuple(p.kind if p is not None else None for p in s.gear)


def install_plans(s: State) -> List[Tuple[list, State]]:
    """Every distinct gear reachable with this turn's installs, as (actions, state)."""
    out, seen = [], set()
    frontier = [([], s)]
    while frontier:
        acts, cur = frontier.pop()
        key = gear_key(cur)
        if key in seen:
            continue
        seen.add(key)
        out.append((acts, cur))
        for a in legal_actions(cur):
            if a[0] == "install":
                nxt = cur.clone()
                apply(nxt, a)
                frontier.append((acts + [a], nxt))
    return out


def crank_outcomes(s: State, acts: list) -> Iterator[Tuple[list, State]]:
    """Every way to spend the remaining Crank Power (crank phase), as (actions, state before end_turn)."""
    yield acts, s
    if s.result is not None:
        return
    for a in legal_actions(s):
        if a[0] in ("crank", "crank_back"):
            nxt = s.clone()
            apply(nxt, a)
            yield from crank_outcomes(nxt, acts + [a])


def turn_outcomes(s: State) -> Iterator[Tuple[list, State]]:
    """Every distinct way to play out the rest of this turn. States are clones; `s` is untouched."""
    if s.phase == "install":
        for acts, cur in install_plans(s.clone()):
            nxt = cur.clone()
            apply(nxt, ("end_install",))
            yield from crank_outcomes(nxt, acts + [("end_install",)])
    elif s.phase == "crank":
        yield from crank_outcomes(s.clone(), [])

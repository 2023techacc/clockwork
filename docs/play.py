"""Bridge between the browser page and the Clockwork simulator (runs inside Pyodide).

Every call returns a JSON string describing the whole screen, so the page keeps no game state of
its own and always follows the simulator's rules exactly. Run mode uses clockwork.run_mode, the
same run logic the simulator's automated runs use.
"""
import json

from clockwork import engine
from clockwork.config import DEFAULT_RULES as R
from clockwork.decks import DECKS, deck_list
from clockwork.enemies import ENEMIES
from clockwork.engine import CCW, CW, apply, legal_actions, new_fight
from clockwork.parts import COUNTERWEIGHT_BLOCK, MOD_RARITY, SHARPENED_DAMAGE, SPECS, Kind, Mod
from clockwork.run_mode import MACHINE, STOPS, Run

MODE = None         # "fight" (single fight) or "run"
RUN = None          # run_mode.Run in run mode
STATE = None        # engine state of the fight on screen
SETUP = {}
ACTIONS = []        # every action of the current fight, so it can be replayed exactly
LOG_SEEN = 0
FIGHT_RECORDED = False

NODE_TEXT = {
    "fight": "Fight: an ordinary enemy. Loot cogs, then pick a part.",
    "elite": "Elite: a dangerous machine-wrecker. More cogs, a part and an attachment.",
    "workshop": "Workshop: buy parts, attachments and machine upgrades; remove parts; repair.",
    "rest": f"Rest: heal, or tinker for a common attachment.",
    "boss": "Boss: the Clock Tower.",
}


def _describe_parts():
    s = {k: SPECS[k] for k in Kind}
    pct = lambda x: f"{round(x * 100)}%"
    return {
        "Striker": f"Deal {s[Kind.STRIKER].damage} damage.",
        "Plate": f"Gain {s[Kind.PLATE].block} Block.",
        "Spring": "Crank again for free, continuing in the direction the trigger came from. "
                  "Extra Heat: +1 for the 1st Spring in a chain, +2 for the 2nd, +3 for the 3rd...",
        "Mirror": "Acts exactly as the part directly opposite it (attachments included). Can't copy a Mirror.",
        "Amplifier": f"Passive: neighbours' damage and Block +{pct(R.amplifier_bonus)}. Never triggers.",
        "Coupler": f"Triggers its left neighbour, then its right one. Can't trigger a Coupler. "
                   f"+{s[Kind.COUPLER].extra_heat} Heat.",
        "Loader": f"Installs the next {R.loader_loads} queue parts into empty slots. If the gear is full, "
                  "one replaces the part opposite the Loader.",
        "Coolant": f"Remove {s[Kind.COOLANT].cooling} Heat.",
        "Hammer": f"Deal {s[Kind.HAMMER].damage} damage. +{s[Kind.HAMMER].extra_heat} Heat.",
        "Magnet": f"Pulls the parts 2 slots away into the slots next to it (swapping if occupied). "
                  f"{R.magnet_block_per_pull} Block per part pulled.",
        "Primer": f"Deal {s[Kind.PRIMER].damage} damage, or {s[Kind.PRIMER].fresh_damage} if it was "
                  "installed this turn.",
        "Assembly": f"Deal {s[Kind.ASSEMBLY].per_install_damage} damage per part installed this turn.",
        "Slider": f"Deal {s[Kind.SLIDER].damage} damage, +{s[Kind.SLIDER].moved_bonus} if a Magnet moved "
                  "it this turn.",
        "+Sharpened": f"(any part) +{SHARPENED_DAMAGE} damage when it triggers.",
        "+Counterweight": f"(any part) +{COUNTERWEIGHT_BLOCK} Block when it triggers.",
        "+Bracing": "(any part) Immune to Jam, Rust and Unscrew.",
        "+Heat Sink": "(any part) Its triggers cost 1 less Heat.",
        "+Coil": f"(Spring) The part this Spring's crank triggers also deals {R.coil_damage} damage.",
        "+Polish": f"(Mirror) The copy's damage and Block +{pct(R.polish_bonus)}.",
        "+Clamp": "(Magnet) The first part it pulls is triggered.",
        "+Feeder": "(Loader) Loads into the next slot to come up instead of a random one.",
        "+Governor": "(any part) Its triggers add no Heat.",
        "+Echo": "(any part) The first time it triggers each turn, it triggers again.",
    }


def options():
    decks = {name: [k.value + "".join("+" + m.value for m in mods) for k, mods in deck_list(d)]
             for name, d in DECKS.items()}
    enemies = {name: {"hp": e.hp, "crank_limit": e.crank_limit, "chime_every": e.chime_every,
                      "chime_damage": e.chime_damage, "elite": e.elite, "cogs": e.cogs}
               for name, e in ENEMIES.items()}
    return json.dumps({"decks": decks, "enemies": enemies, "parts": _describe_parts(), "nodes": NODE_TEXT,
                       "rarity": {m.value: r for m, r in MOD_RARITY.items()},
                       "rules": {"overheat_at": R.overheat_at, "crank_power": R.crank_power,
                                 "installs": R.installs_per_turn, "player_hp": R.player_hp,
                                 "hp_jitter": R.enemy_hp_jitter, "heal": R.heal_between_fights,
                                 "max_attachments": R.max_attachments, "stops": STOPS}})


# ---------------------------------------------------------------- single fight

def start(deck, enemy, seed):
    global MODE, RUN, SETUP
    MODE, RUN = "fight", None
    SETUP = {"mode": "fight", "deck": deck, "enemy": enemy, "seed": int(seed)}
    _begin_fight(DECKS[deck], enemy, int(seed), R, None)
    return view()


def _begin_fight(deck, enemy, seed, rules, start_hp):
    global STATE, ACTIONS, LOG_SEEN, FIGHT_RECORDED
    STATE = new_fight(deck, enemy, seed=seed, rules=rules, trace=True, start_hp=start_hp)
    ACTIONS, LOG_SEEN, FIGHT_RECORDED = [], 0, False


# ---------------------------------------------------------------- run

def start_run(deck, seed):
    global MODE, RUN, STATE, SETUP
    MODE, RUN, STATE = "run", Run(deck, int(seed)), None
    SETUP = {"mode": "run", "deck": deck, "seed": int(seed)}
    return view()


def choose_door(index):
    RUN.choose_door(int(index))
    if RUN.phase == "fight":
        _begin_fight(RUN.fight_deck(), RUN.enemy, RUN.fight_seed(), RUN.rules(), RUN.hp)
    return view()


def take_reward(part="", attachment="", scrap=False):
    RUN.take_reward(part=part, attachment=attachment, scrap=bool(scrap))
    return view()


def rest(choice, attachment=""):
    RUN.rest(choice, attachment)
    return view()


def buy(what, index=0):
    RUN.buy(what, int(index))
    return view()


def sell(index):
    RUN.sell_attachment(int(index))
    return view()


def remove(card_id):
    RUN.remove_card(int(card_id))
    return view()


def leave_workshop():
    RUN.leave_workshop()
    return view()


def attach(index, card_id):
    RUN.attach(int(index), int(card_id))
    return view()


# ---------------------------------------------------------------- fight actions

def _act(action):
    ACTIONS.append(list(action))
    apply(STATE, tuple(action))
    return view()


def install(hand_index, slot):
    """Install a hand part. Identical parts are interchangeable, so use the first copy."""
    part = STATE.hand[hand_index]
    first = next(i for i, p in enumerate(STATE.hand) if (p.kind, p.mods) == (part.kind, part.mods))
    return _act(("install", first, int(slot)))


def end_install(direction):
    acts = [a for a in legal_actions(STATE) if a[0] == "end_install"]
    if len(acts) == 1:          # dead turn after an Overheat: no direction to pick
        return _act(acts[0])
    return _act(("end_install", CW if direction == "cw" else CCW))


def crank():
    return _act(("crank",))


def end_turn():
    return _act(("end_turn",))


# ---------------------------------------------------------------- view

def _part(p, slot=None):
    if p is None:
        return None
    d = {"kind": p.kind.value, "mods": [m.value for m in p.mods]}
    if slot is not None:
        d["jammed"] = slot in STATE.jams
        d["rust"] = STATE.rust.get(p.uid, 0)
    return d


def _intent_text(act):
    if act[0] == "attack":
        return f"Attack {act[1]}"
    if act[0] == "jam":
        p = STATE.gear[act[1]]
        return f"Jam {p.kind.value if p else 'an empty slot'} ({act[2]} turns)"
    if act[0] == "wind_back":
        return "Wind Back (gear turns 1 step counter-clockwise)"
    if act[0] == "unscrew":
        p = STATE.gear[act[1]]
        return f"Unscrew {p.kind.value if p else 'a part'}"
    if act[0] == "overclock":
        return f"Overclock (+{act[1]} Heat to your machine)"
    if act[0] == "rust":
        return f"Rust the part at the top (-{act[1]} damage/Block this fight)"
    return str(act)


def _fight_view():
    global LOG_SEEN, FIGHT_RECORDED
    s = STATE
    if s is None:
        return None
    if MODE == "run" and s.result and not FIGHT_RECORDED and RUN.phase == "fight":
        RUN.finish_fight(s.result, s.hp, s.turn, list(ACTIONS))
        FIGHT_RECORDED = True
    legal = legal_actions(s)
    new_log = s.log[LOG_SEEN:]
    LOG_SEEN = len(s.log)
    n = len(s.gear)
    return {
        "turn": s.turn, "phase": s.phase, "result": s.result, "reason": s.reason,
        "hp": s.hp, "max_hp": s.rules.player_hp, "block": s.block,
        "heat": s.heat, "overheat_at": s.rules.overheat_at,
        "crank_power": s.crank_power, "installs_left": s.installs_left,
        "dead_turn": s.dead_turn, "locked": s.locked, "turn_direction": s.turn_direction,
        "enemy": {"name": s.enemy.name, "hp": max(0, s.enemy_hp), "max_hp": s.enemy_max_hp,
                  "intent": [_intent_text(a) for a in s.intent], "elite": s.enemy.elite,
                  "crank_limit": s.enemy.crank_limit, "cranks_used": s.cranks_used,
                  "chime_every": s.enemy.chime_every, "chime_damage": s.enemy.chime_damage},
        "gear": [_part(p, i) for i, p in enumerate(s.gear)],
        "top": s.top,
        "arrival": [(s.top - k) % n for k in range(n)],
        "hand": [_part(p) for p in s.hand],
        "next": [_part(p) for p in s.visible_queue()],
        "queue_size": len(s.queue), "discard_size": len(s.discard),
        "can_install": any(a[0] == "install" for a in legal),
        "can_pick_direction": ("end_install", CW) in legal,
        "can_end_install": any(a[0] == "end_install" for a in legal),
        "can_crank": ("crank",) in legal,
        "can_end_turn": ("end_turn",) in legal,
        "new_log": new_log,
        "summary": engine.summary(s) if s.result else None,
        "actions": ACTIONS,
    }


def view():
    fight = _fight_view()
    run = RUN.view() if RUN is not None else None
    if run is not None:
        screen = run["phase"]                       # doors | fight | reward | rest | workshop | won | lost
    else:
        screen = "fight"
    return json.dumps({"mode": MODE, "setup": SETUP, "screen": screen, "run": run, "fight": fight,
                       "machine_all": {k: {"name": v[0], "text": v[1]} for k, v in MACHINE.items()}})

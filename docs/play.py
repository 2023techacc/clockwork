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
from clockwork.describe import ENEMY_NOTES, enemy_pattern_text, mod_fits_text, mod_texts, part_texts
from clockwork.enemies import BOSSES
from clockwork.parts import MOD_RARITY
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
    "elite": "Elite: a dangerous machine-wrecker. High risk, high return: more cogs, a better part, "
             "1 of 3 attachments, and a 50% chance to salvage a free machine upgrade (1 of 2).",
    "workshop": "Workshop: buy parts, attachments and machine upgrades; remove parts; repair.",
    "rest": "Rest: heal, or tinker for two common attachments.",
    "boss": "Boss: the end of the district.",
}


def _describe_parts():
    out = {k.value: t for k, t in part_texts(R).items()}
    out.update({"+" + m.value: f"({mod_fits_text(m)}) {t}" for m, t in mod_texts(R).items()})
    return out


def options():
    decks = {name: [k.value + "".join("+" + m.value for m in mods) for k, mods in deck_list(d)]
             for name, d in DECKS.items()}
    enemies = {name: {"hp": e.hp, "crank_limit": e.crank_limit, "chime_every": e.chime_every,
                      "chime_damage": e.chime_damage, "elite": e.elite, "cogs": e.cogs, "boss": name in BOSSES,
                      "armor": e.armor, "swing": e.swing, "pattern": enemy_pattern_text(e),
                      "note": ENEMY_NOTES.get(name, "")}
               for name, e in ENEMIES.items()}
    return json.dumps({"decks": decks, "enemies": enemies, "bosses": BOSSES, "parts": _describe_parts(),
                       "nodes": NODE_TEXT,
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

def start_run(deck, seed, boss=""):
    global MODE, RUN, STATE, SETUP
    MODE, RUN, STATE = "run", Run(deck, int(seed), boss=boss or None), None
    SETUP = {"mode": "run", "deck": deck, "seed": int(seed), "boss": RUN.boss}
    return view()


def choose_door(index):
    RUN.choose_door(int(index))
    if RUN.phase == "fight":
        _begin_fight(RUN.fight_deck(), RUN.enemy_spec(), RUN.fight_seed(), RUN.rules(), RUN.hp)
    return view()


def take_reward(part="", attachment="", scrap=False, salvage=""):
    RUN.take_reward(part=part, attachment=attachment, scrap=bool(scrap), salvage=salvage)
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
                  "chime_every": s.enemy.chime_every, "chime_damage": s.enemy.chime_damage,
                  "armor": s.enemy.armor, "swing": s.enemy.swing},
        "gear": [_part(p, i) for i, p in enumerate(s.gear)],
        "top": s.top,
        "arrival": [(s.top - k) % n for k in range(n)],
        "hand": [_part(p) for p in s.hand],
        "next": [_part(p) for p in s.visible_queue()],
        "queue_size": len(s.queue), "discard_size": len(s.discard),
        "can_install": any(a[0] == "install" for a in legal),
        "can_pick_direction": ("end_install", CW) in legal or ("end_install", CCW) in legal,
        "can_cw": ("end_install", CW) in legal, "can_ccw": ("end_install", CCW) in legal,
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

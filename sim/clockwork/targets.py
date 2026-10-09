"""Balance targets: what each number is tuned toward, and the latest measurement.

Database.md shows this table. Measurements are expensive, so `latest` is copied in by hand from
the roadmap results named in `source`. Update it whenever a study re-measures the metric.
"Casual" = MCTS@50, "careless" = greedy, "expert" = MCTS@200 (AI-Playtesting-Roadmap.md).
"""

# area, metric, target text, (low, high) range or a judged status ("on target"/"off target"),
# latest value (number or text), source
TARGETS = [
    # Whole runs: 3 acts, starter deck (Acts-Design.md, decision 1: rising curve checked by skill)
    ("Runs", "Casual player clears act 1 (of runs that start it)", "about 90%", (85, 95), "93%", "v18 (150 runs)"),
    ("Runs", "Casual player clears act 2 (of runs that reach it)", "about 75%", (70, 80), "76%", "v18 (150 runs)"),
    ("Runs", "Casual player clears act 3 (of runs that reach it)", "about 55%", (50, 60), "58%", "v18 (150 runs)"),
    ("Runs", "Careless player clears a run", "about 10%", (5, 15), "14%", "v18 (200 runs)"),
    ("Runs", "Casual player clears a run", "about 35%", (30, 40), "41%", "v18 (150 runs)"),
    ("Runs", "Expert player clears a run", "about 70% (clearly above casual)", (65, 75), "73%", "v19 (60 runs; planned route, was 57% with the casual policy)"),
    ("Runs", "Day map (simulator): careless / casual / expert clear a run", "same as the door map (~10 / ~35 / ~70%)",
     "on target", "16% / 39% / 70%", "v21 (night market, 6-hour sleep, beds cost cogs)"),
    ("Choices", "Day map (simulator): a night out vs staying in", "a night out at least as good (the night tempts)",
     "on target", "41% vs 38%", "v21 (100 runs each)"),
    ("Economy", "Day map (simulator): cogs unspent at the first boss", "under 40", (0, 40), 47, "v21 (was 110)"),
    ("Runs", "HP when reaching each boss (casual)", "about 35", (32, 40), "37 / 36 / 37", "v18"),
    # Fights in a run
    ("Fights", "HP a normal fight costs (casual), act 1 / 2 / 3", "about 15, rising a little", (10, 17),
     "10.5 / 12.4 / 14.7", "v18"),
    ("Fights", "HP an elite costs (casual), act 1 / 2 / 3", "about 25 (high risk), rising", (20, 36),
     "24.6 / 29.4 / 35.0", "v18 (elites ×1.05, was ×0.9: 16 HP)"),
    ("Fights", "Boss beaten when reached (casual)", "act 1 ~93%, act 2 ~85%, act 3 ~75%; bosses of one act "
     "within ±5", "on target", "Clock Tower 93%, Pendulum 94% / Dismantler 85%, Furnace 89% / Iron Colossus 77%",
     "v18 (150 runs); v21c paired act-2 test: Dismantler 76% -> 83% at 78 HP, Furnace 83%"),
    ("Fights", "Veteran normal enemies: HP per fight at act-2 / act-3 strength", "no enemy far above the others",
     "on target", "Dummy 13.4 / 23.0, Spiker 14.3 / 23.5, Saboteur 14.8 / 23.7, Enrager 7.3 / 22.3",
     "v21c (Dummy veteran ×0.93; was 17.1 / 28.2)"),
    # Choices
    ("Choices", "Fighting elites when healthy vs avoiding them", "elites at least as good (high return)",
     "on target", "79% vs 70% (act 1)", "v18"),
    ("Choices", "Hunting elites at low HP (risk)", "should cost runs (high risk)", "on target",
     "elites from 50% HP: 64%, vs 79% from 70% (act 1)", "v18"),
    ("Choices", "Planning HP to the boss vs fixed HP thresholds (same casual fights)",
     "planning clearly better (skill pays off in the route, not only in fights)", "on target", "57% vs 39%",
     "v19 (120 runs)"),
    ("Choices", "Rest: always heal vs always tinker", "within 5 points of each other", "on target",
     "66% vs 63%", "v16 (300 runs each)"),
    ("Choices", "Run styles (route, rest, Workshop)", "no style more than 5 points above the base",
     "on target", "best: seek elites, always heal (+5)", "v15"),
    # Content
    ("Content", "One part pick (win-rate points over the starter, fights from 30 HP)",
     "+3 to +10; combo enablers (Spring, Mirror, Loader) may be slightly negative alone", (3, 10),
     "Magnet +9.5, Slider +8.1, Primer +7.7, Assembly +6.7, Amplifier +5.5, Coupler +5.4, Coolant +4.4", "v15"),
    ("Content", "One combo-enabler pick (same measure)", "−5 to +3", (-5, 3),
     "Mirror −1.7, Loader −2.8, Spring −3.5", "v15"),
    ("Content", "One common/uncommon attachment (HP kept per fight)", "+2.5 to +4", (2.5, 4),
     "Heat Sink +3.6, Coil +3.5, Bracing +3.5, Polish +3.4, Counterweight +3.3, Sharpened +3.0, Echo +3.0, "
     "Clamp +2.8, Feeder +2.8", "v16/v17 (Coil 6, Polish +40%, Echo now uncommon)"),
    ("Content", "One rare attachment (HP kept per fight)", "+4 to +6", (4, 6),
     "Governor +6.5, Kickback +5.0 (Plate +5.7, Striker +4.4), Overdrive +4.9", "v16 / v18"),
    ("Content", "One rare part pick (win-rate points, as above)", "+4 to +10 (elite loot should feel good)", (4, 10),
     "Boiler +5.7, Hammer +4.8", "v18 (Hammer 12/+1, Boiler 5 + 2/Heat)"),
    ("Content", "One machine upgrade (act-1 clear points, started with it vs none)",
     "+15 to +25, each a real choice", (15, 25),
     "Cooling Fins +26, Flywheel +25, Extra Hands +21, Frame +19, Heat Housing +18, Bigger Gear +15, "
     "Wide Hopper +7", "v18 (act 1, 200 runs)"),
    ("Content", "Strongest single turn, builds without rare attachments", "about half an act-1 boss's HP (≤ 55; a few "
     "over is accepted)", (0, 60), 50, "v18 (Heat Sink everything)"),
    ("Content", "Strongest single turn, builds with rare attachments", "about half an act-3 boss's HP (≤ 90)",
     (0, 90), 84, "v18 (Kickback + Overdrive Hammers; Echo Coupler + 3 Hammers 76)"),
    # Economy
    ("Economy", "Attachments per run (3 acts)", "4–8", (4, 8), 6.0, "v18"),
    ("Economy", "Machine upgrade levels per run", "3–5 (start, boss rewards, a level-up or two)", (3, 5), 3.8,
     "v18 (all runs, won or lost)"),
    ("Economy", "Cogs unspent when reaching the first boss", "under 40", (0, 40), 43, "v18"),
    # Fun proxies the simulator can measure (studies fun; casual player, 150 runs). Human ratings: playtests/.
    ("Fun (simulator)", "Fight length (turns): normal / boss", "4–8 / 6–12", (4, 12), "6.3 / 7.6", "v17"),
    ("Fun (simulator)", "Close wins (≤ 25% HP left): normal fights", "5–15% (rarely a scare)", (5, 15), "3%",
     "v17"),
    ("Fun (simulator)", "Close wins: elites / bosses", "15–30% / 30–50%", (15, 50), "20% / 45%", "v17"),
    ("Fun (simulator)", "Combo turns (4+ triggers)", "10–30% of turns", (10, 30), "18%", "v17"),
    ("Fun (simulator)", "Choice weight: best plan minus the median plan", "6 or more (choosing well matters)",
     (6, 99), 7.3, "v17"),
    ("Fun (simulator)", "Turns with only one good option", "under 25% (rarely forced)", (0, 25), "16%", "v17"),
    ("Fun (simulator)", "Build variety (entropy of the most-copied added part, 0–1)", "0.75 or more", (0.75, 1),
     0.64, "v17 (Magnet in 88 of 150 runs)"),
]


def status(target_range, latest):
    """'on target', 'off target' or '' when it can't be judged automatically."""
    if target_range is None:
        return ""
    if isinstance(target_range, str):       # judged by hand (comparisons)
        return target_range
    lo, hi = target_range
    if isinstance(latest, (int, float)):
        return "on target" if lo <= latest <= hi else "off target"
    # A list of values ("a +1, b +2" or "12–15"): judge every number in it.
    import re
    nums = [float(x.replace("−", "-")) for x in re.findall(r"[−+-]?\d+(?:\.\d+)?", latest)]
    if not nums:
        return ""
    inside = [lo <= n <= hi for n in nums]
    return "on target" if all(inside) else "partly off" if any(inside) else "off target"

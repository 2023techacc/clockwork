"""Balance targets: what each number is tuned toward, and the latest measurement.

Database.md shows this table. Measurements are expensive, so `latest` is copied in by hand from
the roadmap results named in `source`. Update it whenever a study re-measures the metric.
"Casual" = MCTS@50, "careless" = greedy, "expert" = MCTS@200 (AI-Playtesting-Roadmap.md).
"""

# area, metric, target text, (low, high) range or a judged status ("on target"/"off target"),
# latest value (number or text), source
TARGETS = [
    # Whole runs (starter deck, random boss)
    ("Runs", "Casual player clears a run", "65–70%", (65, 70), "69%", "v15"),
    ("Runs", "Careless player clears a run", "40–50%", (40, 50), "43%", "v15"),
    ("Runs", "Expert player clears a run", "85–90% (clearly above casual)", (85, 90), "87%", "v15"),
    ("Runs", "HP when reaching the boss (casual)", "about 35", (32, 40), 37, "v15"),
    # Fights in a run
    ("Fights", "HP a normal fight costs (casual)", "about 15", (12, 17), "12–14", "v15"),
    ("Fights", "HP an elite costs (casual)", "about 25 (high risk)", (20, 28), "19–23", "v15"),
    ("Fights", "Boss beaten when reached (casual)", "about 75%, every boss within ±5 of the others",
     (69, 80), "69–74%", "v15"),
    # Choices
    ("Choices", "Fighting elites when healthy vs avoiding them", "elites at least as good (high return)",
     "on target", "68% vs 57%", "v15"),
    ("Choices", "Rest: always heal vs always tinker", "within 5 points of each other", "off target",
     "73% vs 57%", "v15"),
    ("Choices", "Run styles (route, rest, Workshop)", "no style more than 5 points above the base",
     "on target", "best: seek elites, always heal (+5)", "v15"),
    # Content
    ("Content", "One part pick (win-rate points over the starter, fights from 30 HP)",
     "+3 to +10; combo enablers (Spring, Mirror, Loader) may be slightly negative alone", (3, 10),
     "Magnet +9.5, Slider +8.1, Primer +7.7, Assembly +6.7, Amplifier +5.5, Coupler +5.4, Coolant +4.4, "
     "Hammer +3.8", "v15"),
    ("Content", "One combo-enabler pick (same measure)", "−5 to +3", (-5, 3),
     "Mirror −1.7, Loader −2.8, Spring −3.5", "v15"),
    ("Content", "One common/uncommon attachment (HP kept per fight)", "+2.5 to +4", (2.5, 4),
     "Bracing +5.0, Counterweight +4.1, Sharpened +3.6, Coil +3.2, Heat Sink +2.9, Feeder +2.5, "
     "Polish +2.3, Clamp +2.0", "v11/v12 (before the v15 part pass)"),
    ("Content", "One rare attachment (HP kept per fight)", "+4 to +6", (4, 6), "Governor +5.5, Echo +3.5",
     "v11 (before the v15 part pass)"),
    ("Content", "One machine upgrade (run clear points, started with it)", "+7 to +16 by price", (7, 16),
     "Extra Hands +16, Heat Housing +15, Bigger Gear +8, Flywheel +7", "v12 (before the v15 part pass)"),
    ("Content", "Strongest single turn (any combo)", "about half the boss's HP or less (≤ 55)", (0, 55), 60,
     "v15 (Echo Coupler + Hammers)"),
    # Economy
    ("Economy", "Attachments per run", "2–4", (2, 4), 2.3, "v15"),
    ("Economy", "Machine upgrades per run", "about 1", (0.7, 1.5), 0.93, "v15"),
    ("Economy", "Cogs unspent when reaching the boss", "under 40", (0, 40), 35, "v15"),
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

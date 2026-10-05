"""Human playtest results: the fun survey and play stats from saved playtest reports.

Each report is the JSON the playtest page copies ("Copy report", or the block in a GitHub issue),
saved as playtests/<anything>.json. Database.md's Fun rows are filled from these files.
"""
import glob
import json
import os
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FOLDER = os.path.join(ROOT, "playtests")

# key, question (as on the page), target text, (low, high)
QUESTIONS = [
    ("fun", "How fun was it?", "4.0 or more", (4.0, 5.0)),
    ("tension", "How tense were the fights?", "3.5–4.5 (tense, not stressful)", (3.5, 4.5)),
    ("agency", "Did your choices matter?", "4.0 or more", (4.0, 5.0)),
    ("clarity", "Was it clear what happened and why?", "3.5 or more", (3.5, 5.0)),
    ("variety", "Did it feel different from your earlier runs?", "3.5 or more", (3.5, 5.0)),
    ("again", "How much do you want to play again right now?", "3.5 or more", (3.5, 5.0)),
]


def load(folder=FOLDER):
    reports = []
    for path in sorted(glob.glob(os.path.join(folder, "*.json"))):
        with open(path) as f:
            try:
                reports.append(json.load(f))
            except json.JSONDecodeError:
                continue
    return reports


def summary(reports):
    """Mean rating per question, number of answers, and play stats for finished runs."""
    out = {"reports": len(reports), "ratings": {}}
    for key, *_ in QUESTIONS:
        vals = [r["ratings"][key] for r in reports if isinstance(r.get("ratings"), dict) and key in r["ratings"]]
        out["ratings"][key] = (round(statistics.mean(vals), 2), len(vals)) if vals else (None, 0)
    runs = [r for r in reports if r.get("mode") == "run" and r.get("status") in ("won", "lost")]
    out["runs"] = len(runs)
    out["run_win_rate"] = round(sum(r["status"] == "won" for r in runs) / len(runs), 2) if runs else None
    minutes = [r["minutes"] for r in runs if r.get("minutes")]
    out["minutes_per_run"] = round(statistics.mean(minutes), 1) if minutes else None
    return out


def target_rows(reports=None):
    """Rows for the Database.md targets table (same shape as clockwork.targets.TARGETS)."""
    s = summary(load() if reports is None else reports)
    rows = []
    for key, question, target, rng in QUESTIONS:
        mean, n = s["ratings"][key]
        latest = f"{mean} (n={n})" if n else "no playtests yet"
        rows.append(("Fun (playtests)", f"“{question}” (1–5)", target, rng if n else None, latest,
                     f"{s['reports']} reports in playtests/"))
    rows.append(("Fun (playtests)", "Human players clear a run", "close to the casual AI (65–70%)",
                 (55, 80) if s["runs"] else None,
                 f"{round(s['run_win_rate'] * 100)}% (n={s['runs']})" if s["runs"] else "no playtests yet",
                 f"{s['runs']} finished runs"))
    rows.append(("Fun (playtests)", "Minutes per run", "20–40", (20, 40) if s["minutes_per_run"] else None,
                 s["minutes_per_run"] if s["minutes_per_run"] else "no playtests yet", "page timer"))
    return rows

# Playtest reports

Save each playtest report here as a `.json` file, then run `python sim/build_database.py`. The "Fun (playtests)" rows at the top of Database.md are filled from these files.

**How to get a report:** at the end of a run (or a single fight), answer the 6 quick ratings on the playtest page, write any notes, then press **Copy report** and paste it into a new file here, for example `playtests/2026-10-06-alex-run1.json`. A report sent with **Send as GitHub issue** contains the same JSON in its body; copy the block between the ```json lines.

**The ratings** (1 = not at all, 5 = very much):

| Question | Target |
|---|---|
| How fun was it? | 4.0 or more |
| How tense were the fights? | 3.5–4.5 (tense, not stressful) |
| Did your choices matter? | 4.0 or more |
| Was it clear what happened and why? | 3.5 or more |
| Did it feel different from your earlier runs? | 3.5 or more |
| How much do you want to play again right now? | 3.5 or more |

The report also records the time played and the number of decisions. Five or more reports per question make the averages worth reading; one tester's three runs count as three reports, so note who played in the file name.

# rn: a work's decisions are held to the five a sign-off shows only at the sign-off, after its task is done

## What happened

The session's learning reads: "rn.py decide keeps any number of decisions for a work, but rn.py
proposal refuses a sign-off for a work with more than 5, and a done task's work can no longer be
changed, so the design sign-off cannot be shown".

## Why it matters

Any user whose document needs more than five points settled reaches the design sign-off and cannot
be shown it. `rn.py proposal` stops, saying to settle the work's points again more simply and have it
made again, but by then the task that made the work is done, so `rn.py decide` on it is refused and
there is no way left to do that. The user cannot approve the design, and the documents turn already
made and read stop there with the session.

## What it should be

`rn.py decide` should hold a work's decisions to the same limit `rn.py proposal` does (`MOST` in
`scripts/proposal.py`), refusing a decision past it while the task is still open, so step 2 of
`skills/up/SKILL.md` settles the points more simply before turn makes the work, rather than step 5
finding out at the sign-off when the work can no longer be changed.

## Seen in

rn 0.9.0

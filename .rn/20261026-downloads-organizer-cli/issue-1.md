# rn: rn.py decide keeps a decision longer than a sign-off can show

## What happened

In a session, "rn.py decide keeps a decision of any length, but rn.py proposal refuses a sign-off
for one over 200 characters, and once its task has left the steering rn.py decide refuses to
shorten it, so the design sign-off cannot be shown".

## Why it matters

A user whose decision runs past 200 characters, with nothing telling them or the AI so when they
settle it, meets the limit only at the sign-off, after the work resting on it is made. By then the
task that made the work is done, so the one way rn gives to shorten the decision is closed, and the
user cannot see or approve the work they asked for.

## What it should be

`rn.py decide` should refuse a decision whose `<title>: <what it says>` is longer than the
characters a line of a sign-off holds (`LONGEST` in `scripts/proposal.py`), saying to settle it
again shorter, as `rn.py proposal` does. Step 2 of `/rn:up` asks for `--says` "short enough for the
proposal to show as one line" but gives no number, and only `rn.py proposal` checks it. A check in
`rn.py decide` would stop a long decision while its point is still open with the user, and no
sign-off would then meet one.

## Seen in

rn 0.9.0

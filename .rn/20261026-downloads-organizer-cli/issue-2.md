# rn: turn:up's hook refuses the first start of a run that the same call, sent again, starts

## What happened

turn:up's hook refused to start a run with "lane cannot check read_only on step 4 of up: {given} is
not given in what up started from", and the same call sent again ran.

## Why it matters

rn starts turn:up only at step 3 of `/rn:up`, which hands every work but the plan and the learnings
to turn:up, so any user of rn can meet this refusal on any such work. The call was not at fault, as
the same call ran when sent again, yet the refusal reads as a fault of the call, and step 3 says
nothing of sending it again: the work stops there, and the user waits, or has to find out alone
that the same call, sent again, goes on.

## What it should be

turn:up's hook should let a run's first start through, as it lets the same call through when it is
sent again. This is a change to turn, which rn depends on; it is met where step 3 of `/rn:up`
(`skills/up/SKILL.md`) starts the agent turn:up with the call's line as its whole prompt, so that
step's first start of turn:up runs.

## Seen in

rn 0.9.0

---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/5
stage: plan
signoff: none
artifact-language: English
conversation-language: Japanese
---

# Greet new contributors in the README

G1: A first-time contributor learns they are welcome to try things freely here, so they find it easy to join in.

## Acceptance criteria

- AC1: The README gains one line that tells a newcomer both that they are welcome and that they may try things freely, and its two existing lines stay as they are.

## Tasks

- [x] T1: Settle the wording of AC1 with the user, so the line added in the build stage can be checked against it. Serves G1.

  Completion criterion: AC1, as the user approves it at the plan sign-off, says both points and keeps the two existing lines of `README.md` unchanged, and a reader can check a line against it by reading `README.md`.

  - [x] 1. Read `README.md`, finding out what its two lines say and where a new line fits; confirm with the user that AC1 says what they want. The orchestrator, with the user.
  - [x] 2. Design the check of AC1 as work `plan`, kind `plan`, and check it by reading a sample line against both points and the two existing lines. turn, first run.
  - [x] 3. Trace the design on paper, or try it, against its checks. That run's first reader.
  - [x] 4. Make AC1 as work `plan`, kind `plan`, checked by reading it against the two points. turn, second run.

## Learnings

- L1: Call 0001's plan went back for B-2: the commit f9bf0c6 says "turn returned the plan with a Good for every item, but two fall short at their lines: B-2, the goal's reason has no criterion" (turn's words, quoted in the commit); for rn's makers: turn's check of B-2 would test each part of the goal's reason against a criterion before it claims a Good.
- L2: Call 0001 made T1 add the line to README.md in the plan stage, which the commit c49a817 says "the plan checklist's B-5 counts as a task for a stage not reached" (the orchestrator's words in the commit); for rn's makers: the making of a plan would hold its tasks to B-5 while writing them, as turn's check already asks.
- L3: Call 0002's T1 steps "name call 0002's own file as the path and "document" as the kind", which the commit 1c258e5 says "falls short of B-4's path and kind turn's calls are made on" (the orchestrator's words in the commit); for rn's makers: the making of a plan-stage task would name its work as `plan`, kind `plan`, with no path to a file of an earlier call, as B-4 asks.
- L4: Call 0003's T1 ended "Serves G1, reaching AC1.", which the commit 44a4de6 says "rn.py refuses by the plan checklist's F-1" (the orchestrator's words in the commit); for rn's makers: the making of a plan would end each task line "Serves <IDs>." alone, as F-1 asks.
- L5: At the plan sign-off the user sent the plan back with "the greeting should name the CONTRIBUTING file too" (the user's feedback, commit c1df59f). The decision "What L5 rests on" in call 0010 says the cause was that "the orchestrator saw the repository has no CONTRIBUTING file (git ls-files shows README.md alone; its conversation says so) and asked the user no point on whether the line should point to contribution guidance" (the orchestrator's decision); for the user's repository, at the plan stage: the plan checklist could ask which existing files the README line names, so the user settles that at the plan sign-off.

## Next

Step 3 of /rn:up on plan: settle how T1 covers AC1's link to CONTRIBUTING.md, then step 4 on plan again

## Open

- the greeting should name the CONTRIBUTING file too
- Call 0011's B-3 and B-7 fall short at .rn/20261024-greet-new-contributors/turn/0011-steering.md:12-19: T1's completion criterion says AC1 "says both points" and step 4 checks it "against the two points", leaving out AC1's link to CONTRIBUTING.md, and T1 stays ticked though AC1 changed

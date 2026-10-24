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

- [ ] T1: Settle the wording of AC1 with the user, so the line added in the build stage can be checked against it. Serves G1.

  Completion criterion: AC1, as the user approves it at the plan sign-off, says both points and keeps the two existing lines of `README.md` unchanged, and a reader can check a line against it by reading `README.md`.

  - [ ] 1. Read `README.md`, finding out what its two lines say and where a new line fits; confirm with the user that AC1 says what they want. The orchestrator, with the user.
  - [ ] 2. Design the check of AC1 as work `plan`, kind `plan`, and check it by reading a sample line against both points and the two existing lines. turn, first run.
  - [ ] 3. Trace the design on paper, or try it, against its checks. That run's first reader.
  - [ ] 4. Make AC1 as work `plan`, kind `plan`, checked by reading it against the two points. turn, second run.

## Next

Step 5 of /rn:up on T1: step 1, read README.md and confirm with the user that AC1 says what they want

## Open

None.

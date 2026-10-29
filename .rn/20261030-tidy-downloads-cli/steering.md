---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/19
stage: ux
signoff: none
artifact-language: English
conversation-language: Japanese
---

# CLI tool to tidy the Downloads folder

G1: A command-line tool that sorts the files directly under the user's Downloads folder into folders by kind (images, documents, archives and so on), because those files are scattered and the user cannot easily find the one they look for; it only moves files and never deletes anything, so no file is lost by tidying.

## Acceptance criteria

- AC1: Run with nothing added, the tool shows, for each file directly under Downloads, the folder it would move it to, and afterwards every file is where it was before.
- AC2: Run with the option that tells it to move, the tool moves each file directly under Downloads, other than one AC3 keeps in place, into the folder of its kind (images, documents, archives and so on), and each file of no known kind into one folder for those.
- AC3: The tool only moves files: after any run, every file that was in Downloads before is still in Downloads with the same name and the same contents, and none is overwritten. A file whose name is already taken in the folder it would move to stays where it was, and the tool names it in its output.
- AC4: After any run, every file and folder that was inside a subfolder of Downloads before it is where it was, with the same name and contents.
- AC5: AC1 to AC4 hold when the tool is run on macOS and when it is run on Linux.
- AC6: The README says how to install the tool and how to use it, and the project's tests check each of AC1 to AC4.

## Tasks

- T1: The UX of the tool, at `.rn/20261030-tidy-downloads-cli/ux.md`, approved at the ux sign-off. Serves AC1, AC2, AC3, AC4.

  Completion criterion: the UX says, for the user tidying their Downloads, how they run the tool to see what it would move and to move, what it shows them in each case, the kinds and the folder each kind goes to, and what they see for a file kept in place, each scene ending with every file still in Downloads; every item of the ux checklist holds on it, as turn's first user reads it.

  - [x] 1. Settle with the user each point of use the UX rests on that the goal and the criteria leave open, such as the command's name, the kinds and their folder names, and which folder it tidies when none is named. The orchestrator, with the user.
  - [ ] 2. Make the UX from the plan and the points settled in action 1, `.rn/20261030-tidy-downloads-cli/ux.md` as a ux work. turn.

- T2: The tool's README, rewriting `README.md`, approved at the ux sign-off. Serves AC6.

  Completion criterion: from the README alone, a newcomer can tell what the tool does for them and whether it is for them, and follow, in one example from the UX, its use from seeing what it would move to moving the files; every item of the readme checklist holds on it, as turn's first user reads it.

  - [ ] 1. Make the README from the UX made in T1, `README.md` as a readme work. turn.

## Next

Step 4 of /rn:up on T1: action 2, have the UX made

## Open

None.

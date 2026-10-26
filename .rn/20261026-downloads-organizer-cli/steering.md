---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/10
stage: design
signoff: none
artifact-language: English
conversation-language: Japanese
---

# CLI tool to organize the Downloads folder

G1: A command-line tool that moves the files directly in the Downloads folder into folders by kind, such as images, documents and archives, without deleting, renaming or overwriting any file, and can undo its last run, so that the user can easily find the file they want in a cluttered Downloads folder when they run it by hand.

## Acceptance criteria

- AC1: Told to move, the tool moves each file directly in the folder it is run on, the Downloads folder unless another is named, into the folder of its kind, such as images, documents and archives, and each file of no known kind, such as one with no extension or an unfamiliar one, into an Other folder.
- AC2: Files inside subfolders are not moved, and each subfolder is left where it was.
- AC3: After a run, every file that was there before is still there under its own name, and no file's content has changed.
- AC4: Where a file of the same name is already in the folder of its kind, the tool leaves the file where it is and reports it.
- AC5: Run without being told to move, the tool shows each file it would move and where, and moves nothing.
- AC6: The tool works on both macOS and Linux.
- AC7: A README says how to install the tool and how to use it.
- AC8: The repository's tests check AC1 to AC6 and AC9 by running the tool on a test folder of mixed files and subfolders, never on the real Downloads folder, and pass.
- AC9: Told to undo, the tool moves each file that its last run which moved files in that folder moved back to where it was; where a file of the same name is already there, it leaves the file in the folder of its kind and reports it; and it removes each folder of a kind that run made once that folder is empty, leaving each folder that was there before or still holds a file.

## Tasks

- T1: The UX, `docs/ux.md`. Serves G1.

  Completion criterion: `docs/ux.md` shows whom the tool is for, the goal they reach with it, the key results in order of priority, and the scenes of looking at what would move, moving and undoing that AC1 to AC5 and AC9 give, so that every item of the UX checklist holds, as a first reader in the user's place finds.

  - [x] 1. The key results for G1 and their order of priority. The orchestrator, with the user.
  - [ ] 2. The UX, from the plan and the key results settled in action 1, `docs/ux.md` as a ux work. turn.

- T2: The README, the repository's `README.md` rewritten for the tool. Serves AC7.

  Completion criterion: from `README.md` alone, a newcomer can tell whom the tool is for and what they gain, as `docs/ux.md` has it, and can follow how to install it and how to use it to a first result, so that every item of the README checklist holds, as a first reader in a newcomer's place finds.

  - [ ] 1. How the tool is installed on macOS and Linux. The orchestrator, with the user.
  - [ ] 2. The README, from `docs/ux.md` and the way of installing settled in action 1, `README.md` as a readme work. turn.

- T3: The architecture, `docs/architecture.md`. Serves AC1, AC2, AC3, AC4, AC5, AC6, AC8 and AC9.

  Completion criterion: from `docs/architecture.md`, whoever builds the tool can tell the user stories drawn from `docs/ux.md`, the parts that take them on, the technology of each, where the record that undo reads is kept, and how each part and story is checked on a test folder, never the real Downloads folder, so that every item of the architecture checklist holds, as a first reader in a builder's place finds.

  - [ ] 1. The language the tool is written in, and where the record that undo reads is kept. The orchestrator, with the user.
  - [ ] 2. The architecture, from `docs/ux.md`, `README.md` and what action 1 settled, `docs/architecture.md` as an architecture work. turn.

## Next

Step 4 of /rn:up on T1: action 2, have turn make docs/ux.md

## Open

None.

# CLI tool to organize the Downloads folder

G1: A command-line tool, for macOS and Linux, that sorts the files in the Downloads folder into folders by type when the user runs it, so the user can find the file they are looking for quickly; it deletes nothing, it moves files only when the user tells it to, and when the user tells it to undo, it puts the files it moved in its last run that moved files back where they were.

## Acceptance criteria

- AC1: On macOS and on Linux, the tool run plainly on a Downloads folder holding files lists each file it would move with the folder it would go to, and the names, number and content of everything in Downloads are the same after the run as before.
- AC2: On macOS and on Linux, the tool told to move puts each file directly in Downloads into the folder named for its type, by the types and the extensions of each that the user approves at the ux sign-off.
- AC3: After the tool moves files, every file that was in Downloads before is still there, in Downloads or one of its folders, with the same content, and none is overwritten.
- AC4: After the tool moves files, each type's folder holds only files of that type, so a user who knows the type of the file they want finds it by opening that one folder.
- AC5: Where a file of the same name is already in the folder a file would go to, the tool leaves that file where it was, under its own name, and tells the user which file it left and why.
- AC6: The repository's README tells how to install the tool and how to use it, and a reader who follows it on macOS or Linux installs the tool and runs it plainly, told to move, and told to undo.
- AC7: The repository holds tests that check AC1 to AC5, AC8 and AC9, and they pass on macOS and on Linux.
- AC8: On macOS and on Linux, the tool told to undo puts each file it moved in its last run that moved files back where it was before that run, under the same name and with the same content.
- AC9: Where a file moved in that last run cannot be put back, because a file of the same name is now where it was or it is no longer where the run put it, the undo leaves that file as it is, deletes and overwrites nothing, puts back the other files, and tells the user which files it did not put back and why.

## Tasks

- T1: The UX of the tool, approved at the ux sign-off. Serves AC1, AC2, AC4, AC5, AC8 and AC9.

  Completion criterion: read whole, the UX shows the user each scene of using the tool, run plainly, told to move and told to undo, with what they type and what the tool shows them, the clashes of AC5 and AC9 included, and names each type's folder with the extensions that go into it, so the user can approve them at the ux sign-off and whoever builds the tool builds each scene from it alone.

  - [ ] 1. Settle with the user the command's name, how the user tells it to move and to undo, and the types with the folder name and the extensions of each. The orchestrator, with the user.
  - [ ] 2. Write the UX from the plan and the answers of action 1, `.rn/20261028-organize-downloads-cli/ux.md` as a ux work. turn.

- T2: The tool's section of README.md, drafted from the UX. Serves AC6.

  Completion criterion: read whole by someone who has never seen the tool, the section tells them whom the tool is for and what they gain, shows one run on a Downloads folder from running it plainly to moving the files, and tells how to install it and how to run it plainly, told to move and told to undo, each as the UX of T1 says, with the README's first two lines kept.

  - [ ] 1. Write the tool's section of README.md from the UX of T1, `README.md` as a readme work. turn.

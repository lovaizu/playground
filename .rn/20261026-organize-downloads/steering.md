---
rn: 0.9.0
pr: https://github.com/lovaizu/playground/pull/9
stage: plan
signoff: none
artifact-language: English
conversation-language: Japanese
---

# Downloads folder organizer CLI

G1: A command-line tool that organizes the Downloads folder, because files pile up in it so the wanted file cannot be found; the tool is to make it findable again.

## Acceptance criteria

- AC1: Told to move, on a test Downloads holding files of many types, the tool moves each file directly in it into a folder for its type (images, documents, archives, installers, ...), the type decided by its extension, and a file whose extension matches no type, or that has none, into an Other folder.
- AC2: Files in folders inside Downloads, files whose names start with `.`, and downloads still in progress (`.crdownload`, `.part`, `.download`) are left in place, not moved.
- AC3: A file whose name is already taken in its destination folder is left in Downloads unmoved, and the tool shows on screen that it was left.
- AC4: After a run, no file has been deleted, renamed or overwritten: every file that was there is either where it was or in its destination folder under the same name, with the same content.
- AC5: Run with nothing given, the tool only shows what it would move and moves nothing.
- AC6: A README gives how to install the tool and how to use it.
- AC7: Tests check AC1 to AC5, and GitHub Actions runs them on both Linux and macOS, passing on both.

## Next

Step 5 of /rn:up on plan: stop at the plan sign-off

## Open

None.

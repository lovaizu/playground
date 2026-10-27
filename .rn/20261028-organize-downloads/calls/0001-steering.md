# Command-line tool to organize the Downloads folder

G1: A command-line tool, run on macOS or Linux, that sorts the files in the user's Downloads folder into folders by kind of file, so the user can find the file they need quickly instead of searching one long list, without ever losing a file or changing its name.

## Acceptance criteria

- AC1: Run with no option, the tool shows, for each file directly in Downloads, the folder it would move to, and moves nothing: after the run, every file and folder in Downloads is where it was.
- AC2: Run with the option that tells it to move, the tool moves each file directly in Downloads into a folder inside Downloads named for the file's kind in plain words, such as images or documents, every file of the same kind into the same folder, and each file to the folder the preview showed for it.
- AC3: After any run, every file that was in Downloads before it is still there, in Downloads or in a folder of its kind, with the same name and the same contents.
- AC4: When a file of the same name is already in the folder a file would move to, the tool leaves that file where it is, overwriting and renaming nothing, and shows that it left it, both in the preview and when moving.
- AC5: Every folder in Downloads before a run, and all that is inside it, is unchanged after the run.
- AC6: The tool organizes once each time the user runs the command and leaves no process running after it ends.
- AC7: AC1 to AC6 hold on macOS and on Linux.

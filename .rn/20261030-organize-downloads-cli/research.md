# Research for the sort-downloads architecture

T4's architecture (`docs/architecture.md`) has three choices left open, and this research answers
each on checked facts:

1. Which language lets the tool be one downloaded file that runs on macOS and Linux with nothing
   else installed, as the README's install steps promise (one file fetched from one URL, then
   `chmod +x`)?
2. How does the tool move a file into its type folder on each OS without ever overwriting a file of
   the same name there (AC2, KR1.1), while telling the user each file's outcome (AC1, KR1.3)?
3. Where can the tests of AC1, AC2 and AC3 run on both macOS and Linux (AC4, AC6)?

## Answer

1. **POSIX shell (`#!/bin/sh`), using only POSIX utilities.** macOS 15 and 26 and every Linux
   that follows the Filesystem Hierarchy Standard has `/bin/sh` and the utilities the tool needs
   (`ln`, `rm`, `mkdir`, `pwd`); one text file serves both OSes and every CPU, so the README's
   single download URL works as written. Python, Perl and bash beyond POSIX are not assured on both,
   and a compiled program is one file per OS and CPU.
2. **Never `mv`. Move each file in four steps:**
   1. Check that `TYPE/NAME` is not already there (`[ -e ]` or `[ -L ]`), and give the
      `already exists` line if it is.
   2. Make the type folder with `mkdir`, or give `TYPE is not a folder` where that name is a file.
   3. Make a second name for the file in the type folder with `ln -P SRC TYPE/NAME`. This is a hard
      link: one file with two names. It is refused, and nothing is replaced, if `TYPE/NAME` exists by
      then.
   4. Remove the old name with `rm -f SRC`.

   A failure at step 3 leaves the file where it was, and gives the `cannot move:` line. A failure at
   step 4 is undone by `rm -f TYPE/NAME`. At no moment is any file replaced, and an interruption
   between steps 3 and 4 leaves one file under two names, not a lost one.
3. **GitHub Actions on this public repository**, on the GitHub-hosted runners `ubuntu-24.04`
   (GNU coreutils), `ubuntu-26.04` (the Ubuntu whose own coreutils is now the Rust one) and
   `macos-latest` (macOS 26). These runners are free and unlimited for public repositories. This repository already ran jobs on
   `ubuntu-latest` and `macos-latest` on 2026-10-26. The tests can be a plain POSIX sh script that
   needs nothing installed, run with `HOME` set to a temporary folder so that AC3's `~/Downloads`
   is never the real one.

The findings below bear these out, with their sources at the end; what they leave open is under
[Not settled](#not-settled).

## 1. Language

"POSIX" is the IEEE/Open Group standard for Unix-like systems; its Shell and Utilities volume
defines `sh` and commands such as `ln` and `mkdir` with the same behaviour on every system that
conforms [S1].

| Option | macOS | Linux | One file for both OSes |
|---|---|---|---|
| POSIX sh script | macOS 15 Sequoia and 26 Tahoe are registered as UNIX 03 and as Commands and Utilities V4, the certification of POSIX Shell and Utilities (Issue 6) [S2] | FHS 3.0 requires `/bin/sh` as a "POSIX compatible command shell", and `ln`, `mv`, `mkdir`, `rm`, `sed` in `/bin` [S3] | Yes: one text file, any CPU |
| bash features beyond POSIX | `/bin/bash` on the macOS 26 runner is 3.2.57 [S11] | bash 5.2.21 on the Ubuntu 24.04 runner [S10]; Debian's policy lets `/bin/sh` scripts assume only POSIX.1-2017 plus a few named extras, so a bash script must name `#!/bin/bash` [S4] | Yes, but bash 3.2 and 5.x differ in what they accept |
| Python 3 | Apple removed Python 2.7 in macOS 12.3 [S5]; since Catalina Apple says scripting runtimes "such as Python, Ruby, and Perl" may not be included by default in future macOS [S6] | Not among the FHS's required commands [S3] | Yes, where installed |
| Perl | Same Apple notice as Python [S6] | Not among the FHS's required commands [S3] | Yes, where installed |
| Compiled program (such as Go or Rust) | Runs with nothing installed | Runs with nothing installed | No: one build per OS and CPU, while the README gives one URL (README.md:122, 129) |

The POSIX sh option is the only one that the standards guarantee on both OSes, and that keeps the
one URL. Writing to POSIX alone also keeps the script working where `/bin/sh` is dash, as on Debian
and Ubuntu: the Ubuntu runners have dash 0.5.12 [S10, S12].

Facts the tool's other needs rest on, all POSIX.1-2024:

- `~` is replaced by the value of `HOME` [S1 §2.6.1], so the tool finds `~/Downloads` from `HOME`,
  and a test can point `HOME` elsewhere.
- `pwd -P` prints the folder's full name with no symbolic links in it [S1 pwd], the form the UX's
  first line gives (`/home/me/Downloads`, `/Users/me/Downloads`).
- A `*` pattern lists names "sorted according to the collating sequence in effect in the current
  locale" [S1 §2.14.3]. The locale is the user's language setting, such as `en_US.UTF-8`, and it
  sets the "name order" the UX lists files in; see [Not settled](#not-settled).

## 2. Moving without overwriting

### What each command does when the name is taken

| Way | What happens if `TYPE/NAME` exists | Source |
|---|---|---|
| `mv SRC TYPE/NAME` (POSIX) | The existing file is removed and replaced; POSIX `mv` has only `-i` and `-f`, no option to refuse | [S1 mv], [S1 rename()] |
| `mv -n` on macOS 26 | Checks with `access(to, F_OK)`, then, if the name is free, calls `rename()`: a file made between the check and the rename is replaced. A skipped file exits 0 with no message, so the tool cannot tell a move from a skip | [S7 mv.c:264-276, 314] |
| `mv -n` with GNU coreutils | Since 8.30 (2018) it refuses atomically (in one step no other program can come between) using the kernel's `renameat2`. Its exit status when it skips has changed: nonzero in 9.2 to 9.4, with a message from 9.3, back to 0 and silent in 9.5. GNU's own NEWS says "The -n,--no-clobber option is best avoided due to platform differences" | [S8 lines 1145-1147, 1173-1176, 1365-1366, 1462-1465, 2077-2082] |
| `ln SRC TYPE/NAME` (POSIX) | Without `-f`, ln "shall write a diagnostic message to standard error, do nothing more", and exits nonzero. Underneath, `link()` fails with `EEXIST` when the new name exists, so nothing is replaced even if the name appears after any check | [S1 ln], [S1 link()] |

`ln` refuses on both OSes:

- **macOS 26.5** ships `file_cmds-479` [S9]. Its `ln` removes an existing target only with `-f` or
  `-i` (ln.c:307-319). Otherwise it calls `linkat()` straight away, so a taken name fails
  (ln.c:354-355).
- **GNU coreutils**: "Normally ln does not replace existing files" [S13].

`mv -n` is not used because of its race on macOS and its exit status, which changes from one
version to another. Linux distributions ship different coreutils: Ubuntu 24.04 has 9.4 (nonzero
on skip) [S14], Debian 13 has 9.7 (0 on skip) [S15], and Ubuntu has provided its core utilities
from the Rust coreutils since 25.10 [S16].

### Points the four steps must keep

- **A directory at `TYPE/NAME`.** If `TYPE/NAME` is a directory, both `ln` and `mv` put the file
  inside it instead of failing:
  - POSIX: "The second synopsis form shall be assumed when the final operand names an existing
    directory" [S1 ln].
  - macOS appends the source's name (ln.c:259-263).
  - GNU does the same unless `-T` is given [S13], and macOS `ln` has no `-T`.

  So step 1's check `[ -e "$dest" ] || [ -L "$dest" ]` is needed: it also catches a broken
  symbolic link. If a directory appears between the check and `ln`, the file lands one folder
  deeper, but still nothing is replaced.
- **A symbolic link in the folder.** Give `-P`:
  - macOS `ln` follows a symbolic-link source unless `-P` is given (ln.c:98-99, 355).
  - GNU defaults to `-P` only where the system supports hard links to symbolic links [S13].

  With `ln -P` the link itself is moved, not the file it points to, on both OSes [S1 ln: `-L|-P`].
- **When `ln` fails for another reason.** `link()` also fails on these, and each becomes a
  `cannot move:` line with the file left where it was [S1 link(), S17]:
  - `EXDEV`: the type folder is on another filesystem, such as a mount point.
  - `EPERM`: the filesystem does not support hard links, or Linux's `protected_hardlinks` setting
    refuses a file the user does not own.
  - `EACCES`: no write permission.
- **Removing the old name without a question.** `rm` without `-f` asks before removing a
  read-only file when standard input is a terminal [S1 rm, step 3], so step 4 uses `rm -f`, as the
  UX says the tool asks nothing.
- **Names starting with `-`.** The tool passes each file by its full path, which starts with `/`,
  so such a name is never read as an option.
- **No overwrite at all.** POSIX `rename()` replaces an existing `new` [S1 rename()], and no POSIX
  utility offers a rename that refuses. On Linux, `renameat2(RENAME_NOREPLACE)` refuses atomically
  but needs filesystem support (ext4 since Linux 3.15, btrfs and tmpfs since 3.17, xfs since 4.0)
  [S18]. Neither can be called from sh, so `ln` then `rm` is the one way on both OSes in which
  nothing is ever replaced.

## 3. Where the tests run

| Runner label | System | What it has | Source |
|---|---|---|---|
| `ubuntu-latest`, `ubuntu-24.04` | Ubuntu 24.04.5, image 20261026 | bash 5.2.21, dash 0.5.12, GNU coreutils 9.4, shellcheck 0.9.0 | [S10], [S14] |
| `ubuntu-26.04` | Ubuntu 26.04.1, image 20261026 | bash 5.3.9, dash 0.5.12; coreutils listed as `9.5-1ubuntu2+0.0.0~ubuntu25`, not a GNU release number; whether the runner's `ln` is the Rust one is not checked | [S12], [S16] |
| `macos-latest`, `macos-26` | macOS 26.6.2 arm64, image 20261013 | bash 3.2.57 | [S11] |

- Runner labels are the names a GitHub Actions workflow asks for in `runs-on`. GitHub's runner
  images list `ubuntu-latest` as Ubuntu 24.04 and `macos-latest` as macOS 26 Arm64, and say the
  `-latest` labels "point towards the newest stable OS version available" [S21]. GitHub's runners
  reference lists `macos-15`, `macos-26-intel` and `ubuntu-26.04` among the other labels, and says
  "Use of the standard GitHub-hosted runners is free and unlimited on public repositories" [S19].
- `lovaizu/playground` is public (`gh repo view lovaizu/playground --json visibility` prints
  `PUBLIC`). Actions is enabled on it: run 40417827302 on 2026-10-26 passed jobs on
  `ubuntu-latest` and `macos-latest` [S20]. That run came from an earlier attempt whose workflow
  is no longer in the repository; the tests need a workflow file of their own under
  `.github/workflows/`.
- No test framework is in the images' lists ([S10], [S11]; bats-core is not there). A test script
  in POSIX sh needs nothing installed:
  - It runs on all three runners as it would on a user's machine.
  - It builds the trial folder of AC1 in a `mktemp -d` folder.
  - It compares the printed lines with the UX's.
  - It compares each file's name and content before and after a run (AC2).
  - It sets `HOME` to a temporary folder holding a `Downloads` folder, to check AC3 without touching
    the runner's own.
- `ubuntu-26.04` is in the list for the Rust coreutils Ubuntu now ships (see
  [2. Moving without overwriting](#2-moving-without-overwriting)). `ubuntu-latest` alone would test
  only GNU's `ln`, `rm` and `mkdir`, and the tests can print `ln --version` on that runner to show
  which `ln` they tried.

## Not settled

- **What `ln`'s error says, for the `cannot move: REASON` line.**
  - macOS `ln` writes `ln: TARGET: <system message>`, using `warn()` (ln.c:356).
  - GNU's wording was not read from its source here.
  - Ubuntu 26.04's Rust `ln` was not read at all.

  Whether the last `: ` part is the same system message, such as `Permission denied`, on all three
  is settled by a test on each runner that makes the type folder read-only and reads the line.
  Lower-casing that text to `permission denied`, as the UX shows, is the tool's own step.
- **Whether the Rust coreutils' `ln` refuses a taken name and has `-P`, as POSIX says.** Its
  source and manual were not read. Settled by the same tests on the `ubuntu-26.04` runner.
- **The name order of the list.** It follows the locale [S1 §2.14.3], so a user's `en_US.UTF-8`
  and the C locale (byte order, upper case before lower) can order `Report.pdf` and `notes`
  differently. How macOS and glibc order the same names under the same locale was not compared.
  For the UX's single "name order" and tests that pass on both OSes, the architecture decides
  whether the tool sets `LC_ALL=C` for sorting. The UX does not say, so this is a point for the
  user if it changes what they see.
- **Whether a stock macOS 26 without Apple's Command Line Tools has a working `python3` or
  `perl`.** No Apple page read here says so, and the macOS runner is not a stock system: it has
  Xcode Command Line Tools installed [S11]. This matters only if a language other than sh is chosen.
- **A file left under two names.** If a run stops between `ln` and `rm`, the file sits under both
  names, and the next run gives it `TYPE/NAME already exists`. POSIX.1-2024's `test -ef` tells two
  names of one file [S1 test], so the tool could tell this case apart. Whether macOS 26's `sh`
  (certified to POSIX Issue 6, while `-ef` came into `test` later [S1 test, Rationale]) and dash accept `-ef` was not tried. Settled by a
  test on each runner.
- **Which filesystems refuse hard links.** `link()` gives `EPERM` where the filesystem lacks them
  [S17]; which ones a user's Downloads may sit on, such as a FAT USB drive, was not checked. The
  tool still replaces nothing there: the file stays, with a `cannot move:` line.

## Sources

Read on 2026-10-30.

- S1: POSIX.1-2024 (IEEE Std 1003.1-2024), Shell and Utilities and System Interfaces.
  - Shell: https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html, §2.6.1
    Tilde Expansion and §2.14.3 Patterns Used for Filename Expansion.
  - `ln`: https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ln.html
  - `mv`: https://pubs.opengroup.org/onlinepubs/9799919799/utilities/mv.html
  - `rm`: https://pubs.opengroup.org/onlinepubs/9799919799/utilities/rm.html
  - `pwd`: https://pubs.opengroup.org/onlinepubs/9799919799/utilities/pwd.html
  - `test`: https://pubs.opengroup.org/onlinepubs/9799919799/utilities/test.html
  - `link()`: https://pubs.opengroup.org/onlinepubs/9799919799/functions/link.html
  - `rename()`: https://pubs.opengroup.org/onlinepubs/9799919799/functions/rename.html
- S2: The Open Group, register of Apple's certified products, listing macOS 15.0 Sequoia and 26.0
  Tahoe under UNIX 03 and Commands and Utilities V4: https://www.opengroup.org/openbrand/register/apple.htm.
  The registration, 29-Aug-2025: https://www.opengroup.org/openbrand/register/brand3727.htm. What
  Commands and Utilities V4 covers (Shell and Utilities, Issue 6):
  https://www.opengroup.org/openbrand/register/cxm4.htm
- S3: Filesystem Hierarchy Standard 3.0, `/bin` requirements:
  https://refspecs.linuxfoundation.org/FHS_3.0/fhs/ch03s04.html
- S4: Debian Policy 4.7.4.1 (2026-03-31), §10.4 Scripts:
  https://www.debian.org/doc/debian-policy/ch-files.html
- S5: Apple, macOS Monterey 12.3 release notes:
  https://developer.apple.com/documentation/macos-release-notes/macos-12_3-release-notes
- S6: Apple, macOS Catalina 10.15 release notes, Scripting Language Runtimes:
  https://developer.apple.com/documentation/macos-release-notes/macos-catalina-10_15-release-notes
- S7: Apple `mv` source, file_cmds-479:
  https://github.com/apple-oss-distributions/file_cmds/blob/file_cmds-479/mv/mv.c. Apple `ln`
  source, the `ln.c` lines cited above:
  https://github.com/apple-oss-distributions/file_cmds/blob/file_cmds-479/ln/ln.c
- S8: GNU coreutils NEWS (9.12 being the latest release, 2026-09-14):
  https://github.com/coreutils/coreutils/blob/master/NEWS
- S9: Apple open source release list for macOS 26.5, giving `file_cmds-479`:
  https://github.com/apple-oss-distributions/distribution-macOS/blob/macos-265/release.json
- S10: Ubuntu 24.04 runner image:
  https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md
- S11: macOS 26 arm64 runner image:
  https://github.com/actions/runner-images/blob/main/images/macos/macos-26-arm64-Readme.md
- S12: Ubuntu 26.04 runner image:
  https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2604-Readme.md
- S13: GNU coreutils manual, `ln` invocation:
  https://www.gnu.org/software/coreutils/manual/html_node/ln-invocation.html
- S14: Launchpad, coreutils in Ubuntu 24.04 (9.4-3ubuntu6.3):
  https://launchpad.net/ubuntu/noble/+source/coreutils
- S15: Debian 13 package coreutils (9.7-3): https://packages.debian.org/trixie/coreutils
- S16: Ubuntu 25.10 release notes, "The core utilities of the operating system are now provided by
  the rust-coreutils package": https://discourse.ubuntu.com/t/questing-quokka-release-notes/59220.
  rust-coreutils 0.10.0 in Ubuntu 26.04:
  https://launchpad.net/ubuntu/resolute/+source/rust-coreutils
- S17: Linux man-pages 6.19, link(2): https://man7.org/linux/man-pages/man2/link.2.html
- S18: Linux man-pages, rename(2), `RENAME_NOREPLACE`:
  https://man7.org/linux/man-pages/man2/rename.2.html
- S19: GitHub Docs, GitHub-hosted runners reference:
  https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- S20: This repository's Actions run 40417827302:
  https://github.com/lovaizu/playground/actions/runs/40417827302
- S21: actions/runner-images README, Available Images table and the `-latest` labels:
  https://github.com/actions/runner-images/blob/main/README.md

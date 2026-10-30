---
name: license
version: 1
made_from:
  checklist: 1
  usability: 1
---

# License

A LICENSE file is read by anyone who has the work and wants to use, copy, change or share it, such
as someone taking the code into their own project or packaging it for others. From it alone they
learn the exact terms under which they may do so, and whose copyright those terms are given under.

A LICENSE serves by being a licence the reader can know by its name: its standard text unchanged,
the one the SPDX License List, the shared list of licences with their names, identifiers and texts,
gives, so the terms are those every copy of that licence gives and the reader, or a tool that reads
licences, takes them from the name; filled in only at its copyright line, which says who holds the
work and since when; and the licence the README names, so a reader sent from the README finds the
terms it promised. As the text is the licence's own, how it is worded is not judged, only that it
is that text.

## Format

### F-1: Shape

Scope: whole

Does the LICENSE follow this template, as plain text?

```text
<The licence's title, as the first line of its standard text gives it>

<The licence's standard text, word for word, with the year and holder filled in at its copyright
line>
```

Where the standard text has no title, as the BSD licences', the title is the licence's full name
in the SPDX License List, such as `BSD 3-Clause "New" or "Revised" License`. Where the standard
text keeps no copyright line for the work, as the GNU GPL's, whose one copyright line is the Free
Software Foundation's for the licence itself, the line `Copyright (c) <year> <holder>` stands
first, with a blank line after it.

Why: a reader looks for the licence at the top and for the copyright line where that licence
always keeps it, and finds each there only when every LICENSE puts it there; a title on the first
lines lets them tell the licence before reading any term; and a copyright line set apart from a
copyright line the text holds for the licence itself is not taken for the work's.

## Benefit

### B-1: Which licence, at a glance

Scope: its part

From the file's first lines, before any term, can the reader tell which licence the work is under,
by the name they would look it up by?

Signs: the title names the licence, and its version where it has versions, such as
`GNU GENERAL PUBLIC LICENSE` with `Version 3, 29 June 2007` under it.

Why: a reader who knows the licence by name takes its terms from the name and need not read on; one
who cannot tell it reads the whole text to find out, or takes it for another licence.

### B-2: The exact terms, those of the standard text

Scope: its part

Can the reader take the terms in the file as exactly those of the licence it names, with no term
added, dropped or changed?

Tried by: the file compared word by word, line breaks and spaces aside, with the licence's text in
the SPDX License List, as
`diff <(tr -s '[:space:]' '\n' < LICENSE) <(curl -fsSL https://raw.githubusercontent.com/spdx/license-list-data/main/text/<SPDX ID>.txt | tr -s '[:space:]' '\n')`,
run from the folder that holds the file, `<SPDX ID>` being the licence's identifier in that list,
such as `MIT`, and every difference it prints read.

Signs: the only differences are the year and holder at the copyright line, the title where the
standard text has none, and the copyright line set first where the standard text keeps none for the
work, as F-1 gives them; no placeholder of the copyright line F-1 fills in, such as MIT's `<year>`
or `<copyright holders>`, is left, while one elsewhere in the standard text, such as `<year>` and
`<name of author>` in the GNU GPL's appendix on how to apply it, is part of that text and stays.

Why: a term changed, even by a word, makes the file a licence of its own, whose terms the reader
cannot take from the name and which tools that read licences no longer recognize, so each reader
must read it whole and may still read it wrong.

### B-3: Whose copyright, and since when

Scope: its part

From the copyright line, can the reader tell who holds the copyright in the work and from what
year, so they know who gives them the terms and whose notice they keep with each copy they share?

Tried by: the copyright line read, and its year compared with the year of the repository's first
commit, as `git log --reverse --format=%ad --date=format:%Y | head -1` prints it.

Signs:
- the year is that of the repository's first commit, or a range from it to the year of a later
  change, such as `2024-2026`;
- the holder is a name the reader can look up, such as a person's name, an organisation's
  name or the account that owns the repository.

Why: the licence is given by whoever holds the copyright, and most licences ask that the copyright
notice go with each copy; a reader who cannot tell the holder cannot keep the notice right, and
cannot tell whom to ask for what the licence does not give.

### B-4: The licence the README names

Scope: its part

Can a reader who comes from the README's License section find in the file the licence that section
names?

Tried by: the README's License section read, its link to the file followed from where the README is
shown, and the licence the section names compared with the title at the file's top.

Signs: the README's link opens this file; the name the README gives, such as `MIT License`, is the
file's title or the licence's name or identifier in the SPDX License List, such as `MIT`.

Why: the reader decides from the README that the work's terms suit them; a LICENSE giving another
licence leaves them unable to tell which terms hold, and following one breaks the other.

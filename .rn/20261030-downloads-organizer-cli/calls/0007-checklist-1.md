---
name: readme
version: 1
made_from:
  checklist: 1
  usability: 1
---

# README

A README is read by someone meeting the product for the first time, with only what a newcomer has.
From it alone they decide whether the product is for them, and if it is, get to their first result
with it. Someone joining those who build it reaches the architecture and development documents from
it.

A README tells a newcomer what the product's UX holds for them before anything they must do: the
idea the product rests on, what it does that gives its benefits where other ways of doing the same
work do not; whom it is for and what they gain, from the UX's users, goals and benefits; one of the
UX's scenes as the example, the one account of using the product from starting to the result; and
what the benefits give that doing the work by hand or with another tool does not. What follows
takes a reader who has decided from there to their first result, each step one they can follow with
what they have and each statement one they find holds when they try it. What lies beyond the first
result, such as fuller use, goes in a page reached from Documentation.

## Format

### F-1: Shape

Scope: whole

Does the README follow this template, headings included?

```markdown
# <Product name>

<The idea the product rests on, in one sentence; then what the reader gains, with the kind of
thing that gives it, and whom it is for, in one or two sentences; under no heading>

## Example

<Using it on one piece of work, from starting to the result, with what the product gives back>

## Why <product name>

<What only this product gives, set against the other ways of doing the same work>

## Requirements

- <Each thing that must be in place beforehand, said as what it is>

  <Why it is needed, where the reader would not know>

## Installation

<How to install, then the first use, as in the example>

## Documentation

<Where fuller use and what changed in each version are written>

## Development

<A link to the entrance to the architecture and development>

## License
```

Each section opens with its main point. A list item is one sentence understood alone, with its
explanation, where it needs one, after a blank line and indented under it; no item is set in bold.

Why: a reader looks for requirements, installation or the license under the headings READMEs
commonly give them, and finds each where they look only when every README puts it there; the
opening sits right under the name, where the reader looks first, and begins with the idea, as it is
what sets the product apart; the example comes before installation, so the reader sees using it
before deciding to install it; why to choose it follows the example, so the reader weighs it against
the use they have just seen; and the way on for those who build it stands apart from Documentation,
so a user does not read through links they do not use. The reader skims the items alone and reads
an explanation only where they need it; bold on every item marks nothing out.

## Benefit

### B-1: Whether it is for them

Scope: its part

From the opening, can the reader tell whether the product is for them?

Signs:
- the first sentence gives the idea by which the product gives what other ways of doing the same
  work do not, beyond what it does;
- what the reader gains is said with the kind of thing that gives it, such as a tool run from their
  editor, in place of how the product works;
- whom it is for is said, so the reader can place themselves without working it out.

Why: the reader decides from the opening whether to read on; one shown only what the product does
takes it for any tool that does the same, and one who cannot place themselves leaves a product that
would have served them.

### B-2: Using it on their own work

Scope: its part

From the example, can the reader picture using the product on their own work, from starting to the
result, with what they do and what they get back?

Signs:
- the example is on work of the reader's kind, and runs to the result;
- what the product gives back is shown as the reader gets it, not described;
- where several act in turn, such as the reader, the product and its agents, who does what and what
  passes between them is told in the order it happens.

Why: a reader who can picture it decides on what they will actually get; an example on work of
another kind, or one without what the product gives back, is read as someone else's story.

### B-3: Why this one

Scope: its part

From Why, can the reader tell what the product gives them that doing the work by hand, or with
another tool, does not?

Signs: the benefits only this product gives come first, and one every way of doing the work gives,
such as not losing work, comes, if at all, after them.

Why: what only this product gives is the reason to choose it; what every way gives does not decide
the choice, and placed first it hides what does.

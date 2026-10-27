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

### B-6: Each part taken in on one reading

Scope: each part

Can the reader take in each part reading it once from the top, without going back or ahead and
without guessing?

Signs:
- each term the reader may not know, such as a plain word used in a sense of its own or a name taken
  from another product, is shown by a sentence, an example or a figure where it is first used;
- each sentence rests on words, reasons and steps that come before it, and on no link the reader
  must follow first;
- each idea is given whole, such as a case named with what happens in it;
- each thing is in the form that fits it, such as a command in a block to copy, and values side by
  side in a table.

Why: a reader stopped goes back or ahead, or reads on with a guess, and acts on a picture of the
product that differs from the product where the guess is wrong.

### B-7: Each sentence needed, once

Scope: whole

Does each sentence give the reader something toward deciding or their first result that no other
sentence of the README gives them?

Signs:
- each thing is said in one part, such as the gain in the opening alone and not again in Why, the
  example's steps in Example alone and not again in Installation, and a figure only for what the
  example does not tell;
- each part is meant for the reader, not for someone else such as a reviewer, and tells of the
  product, not of what the README is or does;
- each sentence says what holds, not the history of how a decision was reached;
- fuller use is left to the page Documentation reaches;
- a comparison or an example is given only for an idea the reader does not already hold, and each
  word gives something.

Why: a reader who has skimmed a run of repeats skims the one new point among them too, and two
places that say one thing come to disagree as one of them changes; each part beyond the subject
buries those the reader needs.

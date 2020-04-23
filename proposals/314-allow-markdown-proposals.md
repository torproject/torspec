```
Filename: 314-allow-markdown-proposals.md
Title: Allow Markdown for proposal format.
Author: Nick Mathewson
Created: 23 April 2020
Status: Open
```

# Introduction

This document proposes a change in our proposal format: to allow
Markdown.

## Motivation

Many people, particularly researchers, have found it difficult to
write text in the format that we prefer.  Moreover, we have often
wanted to add more formatting in proposals, and found it nontrivial
to do so.

Markdown is an emerging "standard" (albeit not actually a
standardized one), and we're using it in several other places.  It
seems like a natural fit for our purposes here.

# Details

We should pick a particular Markdown dialect.  "CommonMark" seems like a
good choice, since it's the basis of what github and gitlab use.

We should also pick a particular tool to use for validating Markdown
proposals.

We should continue to allow text proposals.

We should continue to require headers for our proposals, and do so
using the format at the head of this document: wrapping the headers
inside triple backticks.


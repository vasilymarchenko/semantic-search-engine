---
name: capture
description: >
  Capture and save insights, summaries, Q&A, or code snippets from the current
  conversation into the Obsidian knowledge vault. Always asks what to save and
  confirms before writing. Use when the user wants to store something from the
  session — a concept, a realization, a code pattern, or a session summary.
---

# Capture — Save to Knowledge Vault

You are saving knowledge from the current conversation into the user's Obsidian knowledge vault.
Always ask before acting — the user decides what gets stored and how.

The vault uses three folders:
- **Sessions/** — date-based diary entries, one per working session
- **Concepts/** — evergreen topic notes, reusable and updatable over time
- **Snippets/** — code patterns with explanation and context for when to use them

---

## Phase 1 — Ask what to capture

Ask the user two questions before doing anything else:

**1. What type of note?**
- **Quick insight** — a single concept, realization, or takeaway (goes to `Concepts/`)
- **Session summary** — structured overview of this working session (goes to `Sessions/`)
- **Full Q&A / explanation** — full explanation preserved as reference material (goes to `Concepts/`)
- **Code snippet** — a code pattern with context (goes to `Snippets/`)

**2. What content to include?**
- Everything from this conversation
- A specific part — ask them to describe which part
- Claude's summary of the key points

Do not proceed until the user answers both questions.

---

## Phase 2 — Explore the vault

Run these in parallel before drafting anything:
- `list_directory` on `/` to understand current folder structure and existing notes
- `list_all_tags` to see which tags are already in use

This informs where to place the note and which tags to reuse.

---

## Phase 3 — Determine title and location

Based on type, propose a title and path:

| Type | Folder | Filename pattern |
|------|--------|------------------|
| Session summary | `Sessions/` | `YYYY-MM-DD-<topic-slug>.md` |
| Quick insight | `Concepts/` | `<topic-slug>.md` |
| Full Q&A | `Concepts/` | `<topic-slug>.md` |
| Code snippet | `Snippets/` | `<topic-slug>.md` |

Use today's date. Slugify the topic: lowercase, hyphens, no special characters.

Show the proposed title and full path to the user. Ask them to confirm or adjust before writing anything.

---

## Phase 4 — Search for related notes

Use `search_notes` to find existing notes on the same topic.

If a related note exists:
- Ask: update it, or create a new note linking to it?
- If updating: use `patch_note` instead of `write_note`

If no related notes found: proceed to create a new note.

---

## Phase 5 — Propose tags

Prefer tags from the existing list (Phase 2). Propose 2–5 tags total.
Add new tags only when no existing tag fits.

Show the proposed tags and ask the user to confirm or adjust.

---

## Phase 6 — Write the note

Format the note per its type (see formats below). Then:
- `write_note` to create a new note
- `patch_note` to append to or update an existing note

After writing, tell the user exactly what was saved and where (full vault path).

---

## Note formats

### Session summary

```
---
date: YYYY-MM-DD
tags: [session, topic1, topic2]
type: session
---

# YYYY-MM-DD — <Topic>

## What we worked on
<2–3 sentences of context>

## Key insights
- <insight>
- <insight>

## Open questions
- <question, if any>

## Related
[[concept-slug]] | [[other-note]]
```

### Concept / Full Q&A

```
---
date: YYYY-MM-DD
tags: [topic1, topic2]
type: concept
---

# <Concept Title>

## Summary
<One-paragraph overview>

## Details
<Full explanation, preserved faithfully from the conversation>

## See also
[[related-concept]] | [[YYYY-MM-DD-session]]
```

### Code snippet

```
---
date: YYYY-MM-DD
tags: [python, topic, pattern-name]
type: snippet
---

# <Pattern Name>

## When to use
<What problem this solves and when to reach for it>

## Code
```python
<code>
```

## Why it works
<Explanation of the key idea>

## See also
[[related-concept]]
```

### Quick insight

```
---
date: YYYY-MM-DD
tags: [topic]
type: insight
---

# <Insight — stated as a claim or realization>

<Explanation in 2–5 sentences>

## Source
Captured from [[YYYY-MM-DD-session]] or described inline.
```

---

## Backlinks

Always include `[[backlinks]]` to:
- Related concept or snippet notes mentioned in the conversation
- The session note this insight came from (or vice versa — session notes link to concepts)
- Any note explicitly referenced during the conversation

Use Obsidian `[[note-name]]` syntax — filename slug only, no path, no `.md` extension.
When creating a concept from a session, go back and add a link to the session note too (`patch_note`).

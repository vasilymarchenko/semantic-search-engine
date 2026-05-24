---
name: explain
description: Explain Python code — project, PR, class, or function — for a senior C# developer learning Python
---

Explain the following to a senior .NET/C# developer who is learning Python: $ARGUMENTS

If $ARGUMENTS is empty, explain the most recent code Claude wrote or discussed (the last
code block or file touched in this conversation — not something mentioned only in passing).

Detect the scope automatically: project, PR, class, function, or concept.
If the scope is ambiguous, state your assumption in one sentence before explaining.

---

## Structure

Choose the template based on scope:

### For code artifacts (project, PR, class, function)

1. **Why this exists** — business need or problem it solves; plain language only, no code
   snippets in this section
2. **What it does** — how it solves it, in plain language
3. **C# equivalent** — closest .NET analog for the overall design; if none exists, say so
   explicitly and explain why (Python's model may have no C# counterpart)
4. **Python specifics** — for each non-obvious pattern used, give all of the following:
   - **What it is** — one sentence
   - **Why Python does it this way** — the design reasoning; what problem this solves
     that the C# approach does not (or handles differently)
   - **C# equivalent** — use C# syntax, not pseudocode; if no equivalent exists, say so
   - **C# instinct to avoid** — the thing a C# developer will try first that won't work
     or won't be idiomatic here; skip this sub-bullet only if there is genuinely no trap
   - **When to reach for it** — one sentence: what signal tells you to use this pattern

### For abstract concepts (GIL, event loop, duck typing, decorators as a concept, etc.)

1. **What it is** — one sentence definition
2. **Why Python needs it** — the problem it solves or the design philosophy behind it
3. **C# equivalent or contrast** — what C# does instead, or why C# doesn't need this
4. **Practical implication** — what changes about how you write code because of this concept

---

## Rules

- In sections 1–2 (Why / What): lead with purpose. Mechanics belong in section 4.
- Skip Python fundamentals a senior C# dev already knows: OOP, async/await intent,
  dependency injection, SOLID, garbage collection basics.
- "Non-obvious" means: syntax or behavior that differs from C# in a way that would
  surprise a .NET developer. If a Python pattern maps cleanly to a C# construct with
  no gotchas, skip it.
- For large scope (project or PR with more than ~5 files): summarize recurring patterns
  once — do not enumerate every file or every line.
- Each Gotcha sub-bullet applies per pattern. If a pattern has no trap for a C# dev,
  omit only that sub-bullet — the rest of the pattern explanation stays.

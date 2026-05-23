---
name: explain
description: Explain Python code — project, PR, class, or function — for a senior C# developer learning Python
---

Explain the following to a senior .NET/C# developer who is learning Python: $ARGUMENTS

If $ARGUMENTS is empty, explain the most recent code Claude wrote or discussed.
Detect the scope automatically: project, PR, class, function, or concept.

Structure:
1. **Why this exists** — business need or problem it solves; no code yet
2. **What it does** — how it solves it, in plain language
3. **C# equivalent** — closest .NET analog for the overall design; if none, say so
4. **Python specifics** — explain each non-obvious Python pattern used:
   - What it is
   - C# equivalent or why C# has no equivalent
   - Gotcha for a .NET dev (skip if none)

Rules:
- Lead with purpose, not mechanics
- Skip fundamentals they already know (OOP, async, DI, SOLID, GC basics)
- Use C# syntax in comparisons, not pseudocode
- For large scope (project/PR), summarize patterns — don't enumerate every line

# Lessons Protocol

**Location:** `.claude/lessons/LESSONS.md`
**Rule:** After any mistake, correction by the user, or failed approach — write a lesson entry before the session ends.

---

## When to Write a Lesson

Write an entry whenever:
- The user corrects something I did wrong
- An approach fails and a better one is found
- A tool call produces an unexpected result and a workaround is discovered
- I repeat a mistake that was previously corrected
- A quality gate blocks progress and the root cause is a recurring pattern

Do NOT write a lesson for:
- One-off project-specific decisions (those go in session logs)
- Speculation — only confirmed failures and confirmed corrections
- Anything already captured in CLAUDE.md or a rule file

---

## How to Write a Lesson

Append to `.claude/lessons/LESSONS.md`, most recent first, using this format:

```markdown
### YYYY-MM-DD — [category]
**Mistake:** [What went wrong — be specific, not vague]
**Correction:** [What the right approach is]
**Prevention:** [A concrete action or check that prevents recurrence]
```

**Good example:**
```markdown
### 2026-03-03 — workflow
**Mistake:** Modified files in the wrong order — edited the downstream doc before the source doc, creating an inconsistency.
**Correction:** Always modify the source of truth first (paper/main.tex or the defining rule file), then propagate.
**Prevention:** Before any multi-file edit, identify which file is authoritative and start there.
```

**Bad example (too vague):**
```markdown
### 2026-03-03 — workflow
**Mistake:** Made an error.
**Correction:** Be more careful.
**Prevention:** Pay attention.
```

---

## Reading Lessons

At the start of every session, read `.claude/lessons/LESSONS.md` before beginning work.
If a task involves a category with past lessons (e.g., `latex`, `code`), re-read those entries before starting.

---

## Relationship to MEMORY.md and [LEARN] Tags

| System | Purpose | Scope |
|--------|---------|-------|
| `[LEARN]` tags in MEMORY.md | Generic patterns useful across all projects | Project-agnostic |
| `.claude/lessons/LESSONS.md` | Project-specific mistakes and corrections | This project only |
| Session logs | Detailed per-session narrative | Ephemeral / archival |

When a lesson is generic enough to help any user of this template, also add a `[LEARN:category]` entry to MEMORY.md.

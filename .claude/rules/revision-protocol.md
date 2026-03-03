# Revision Protocol — R&R Cycle (Rule 18)

**When referee reports arrive, `/respond-to-referee` classifies each comment and routes it to the right agent.**

## Comment Classification

| Classification | What It Means | Routed To |
|---------------|---------------|-----------|
| **NEW ANALYSIS** | Requires new estimation or data work | Coder (main Claude) → debugger |
| **CLARIFICATION** | Text revision sufficient | economics-paper-writer → academic-proofreader |
| **DISAGREE** | Diplomatic pushback needed | Flagged for User review |
| **MINOR** | Typos, formatting | economics-paper-writer |

## The R&R Flow

```
Referee reports arrive (real, not simulated)
        │
        ▼
   /respond-to-referee classifies each comment
        │
        ├── NEW ANALYSIS → Coder (main Claude) → debugger → economics-paper-writer updates
        ├── CLARIFICATION → economics-paper-writer → academic-proofreader
        ├── DISAGREE → User decides → diplomatic response drafted
        └── MINOR → economics-paper-writer
        │
        ▼
   Revised paper → academic-proofreader → academic-editor re-checks
        │
        ▼
   Response letter produced
```

## Rules

- This uses the same agents but in a targeted way — not a full pipeline restart
- Each comment gets its own routing — a single referee report may trigger multiple agent pairs
- The response letter maps each referee comment to the specific change made
- DISAGREE items are always flagged for user review — Claude never autonomously pushes back on referees
- The research-orchestrator tracks which comments are resolved and which are pending

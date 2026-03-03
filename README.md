# cloco — Research Orchestration for Economics with Claude Code

> **A multi-agent, quality-gated research pipeline for economics papers — from idea to submission — built on top of Claude Code.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Built with Claude](https://img.shields.io/badge/Built%20with-Claude%20Code-blueviolet)](https://claude.ai/code)
[![Upstream: clo-author](https://img.shields.io/badge/Upstream-clo--author-blue)](https://hsantanna88.github.io/clo-author/)

---

## Lineage & Credits

> Built on top of [**clo-author**](https://hsantanna88.github.io/clo-author/) by Hugo Sant'Anna,
> which is itself a fork of [**claude-code-my-workflow**](https://github.com/pedrohcgs/claude-code-my-workflow)
> by Pedro H.C. Sant'Anna (Emory University).
>
> Extended for financial economics research at **Paris Dauphine University – PSL**
> by [Juan F. Imbet](https://github.com/jfimbet).

This project would not exist without the pioneering infrastructure work from both upstream projects. The core orchestration philosophy, agent-critic pairing pattern, and quality-gate system originate there.

---

## What This Is

Economics research pipelines are fragmented: literature review in one tool, data analysis in another, writing in a third, with no systematic quality enforcement across stages. Claude Code makes it possible to build an autonomous contractor that manages the full research lifecycle — dispatching specialized agents, enforcing quality gates, and tracking every decision.

`cloco` extends the upstream infrastructure with four project-type-aware pipelines (`empirical`, `theory`, `structural`, `empirical+theory`), two new specialist agents (`econ-finance-theorist` and `structural-estimation-expert`), type-specific scoring weights so a pure theory paper isn't penalized for lacking data, two new skills (`/theory-model`, `/structural-estimation`), and a lessons protocol that captures project-specific corrections and prevents recurring mistakes.

---

## Architecture at a Glance

```
/interview-me  →  Research Spec + Domain Profile
       │
       ├─ [empirical]────────── /find-data ──── /identify ──────────────────────────┐
       ├─ [theory]───────────── /theory-model ───────────────────────────────────────┤
       ├─ [structural]────────── /find-data ─── /theory-model ─── /structural-est ──┤
       └─ [empirical+theory] ── /find-data ─── /theory-model ─── /identify ─────────┘
                                                                          │
                                              /data-analysis  (if not pure theory)
                                                                          │
                                                                   /draft-paper
                                                                          │
                                                     /paper-excellence → /review-paper
                                                                          │
                                                                      /submit
```

Every creator agent is paired with a critic. Every artifact must score ≥ 80 before advancing. Nothing ships below the gate threshold.

---

## Four Research Pipelines

### A — Empirical

```
Research Spec
    ├── academic-librarian  ──[parallel]──  explorer
    │         ↓ academic-editor               ↓ data-quality-surveyor
    └──────── causal-strategist
                    ↓ econometrics-critic
              Coder (main Claude)
                    ↓ debugger
              economics-paper-writer
                    ↓ academic-proofreader
              blind-peer-referee ×2
                    ↓ academic-editor
              replication-verifier  →  submit
```

### B — Theory

```
Research Spec
    ├── academic-librarian  ──[no data needed]
    │         ↓ academic-editor
    └──────── econ-finance-theorist
                    ↓ econometrics-critic
              economics-paper-writer
                    ↓ academic-proofreader
              blind-peer-referee ×2
                    ↓ academic-editor  →  submit
```

### C — Structural

```
Research Spec
    ├── academic-librarian  ──[parallel]──  explorer
    │         ↓ academic-editor               ↓ data-quality-surveyor
    ├──────── econ-finance-theorist
    │               ↓ econometrics-critic
    └──────── structural-estimation-expert
                    ↓ econometrics-critic
              Coder (main Claude)
                    ↓ debugger
              economics-paper-writer  →  replication-verifier  →  submit
```

### D — Empirical + Theory

```
Research Spec
    ├── academic-librarian  ──[parallel]──  explorer
    │         ↓ academic-editor               ↓ data-quality-surveyor
    ├──────── econ-finance-theorist   ──[parallel]──  causal-strategist
    │               ↓ econometrics-critic                  ↓ econometrics-critic
    └─────────────────────────────────────────────────────
              Coder (main Claude)  →  economics-paper-writer  →  submit
```

---

## 31 Skills

| Category | Skill | What It Does |
|----------|-------|-------------|
| **Pipeline** | `/new-project [topic]` | Full pipeline: idea → paper (orchestrated) |
| | `/interview-me [topic]` | Interactive research interview → spec + domain profile |
| **Literature** | `/lit-review [topic]` | Librarian + Editor: literature search + synthesis |
| | `/research-ideation [topic]` | Research questions + strategies |
| **Theory & Structural** | `/theory-model [question]` | Theorist + Econometrician: formal model design |
| | `/structural-estimation [spec]` | Structural expert + Econometrician: estimation design |
| **Data & Strategy** | `/find-data [question]` | Explorer + Surveyor: data discovery + assessment |
| | `/identify [question]` | Strategist + Econometrician: identification strategy |
| | `/pre-analysis-plan [spec]` | Strategist: draft PAP (AEA/OSF/EGAP) |
| **Analysis & Writing** | `/data-analysis [dataset]` | Coder + Debugger: end-to-end analysis |
| | `/draft-paper [section]` | Writer: draft paper sections + humanizer pass |
| | `/compile-latex [file]` | 3-pass XeLaTeX + bibtex |
| **Quality & Review** | `/econometrics-check [file]` | Econometrician: 4-phase causal inference audit |
| | `/review-code [file]` | Debugger: code quality review (standalone) |
| | `/proofread [file]` | Proofreader: 6-category manuscript review |
| | `/paper-excellence [file]` | Multi-agent parallel review + weighted score |
| | `/review-paper [file]` | 2 Referees + Editor: simulated peer review |
| | `/validate-bib` | Cross-reference citations vs bibliography |
| **Submission** | `/target-journal [paper]` | Editor: journal targeting + submission strategy |
| | `/respond-to-referee [report]` | Revision routing per revision-protocol |
| | `/audit-replication [dir]` | Verifier: 10-check submission audit |
| | `/data-deposit` | Coder + Verifier: AEA replication package |
| | `/submit [journal]` | Final gate: score ≥ 95, all components ≥ 80 |
| **Presentations** | `/create-talk [format]` | Storyteller + Discussant: Beamer/Quarto talk from paper |
| | `/visual-audit [file]` | Slide layout audit |
| **Infrastructure** | `/commit [msg]` | Stage, commit, PR, merge |
| | `/humanizer [file]` | Strip 24 AI writing patterns |
| | `/journal` | Research journal timeline |
| | `/context-status` | Session health + context usage |
| | `/learn` | Extract session discoveries into skills |
| | `/deploy` | Quarto render + GitHub Pages sync |

---

## 16 Agents

| Agent | Role | Paired Critic |
|-------|------|--------------|
| `research-orchestrator` | Master controller — manages the dependency graph, dispatches agents, enforces quality gates | — |
| `academic-librarian` | Systematic literature search across top journals, NBER, SSRN, RePeC | `academic-editor` |
| `academic-editor` | Literature critique + peer review dispatcher | — |
| `blind-peer-referee` | Simulated adversarial referee — two instances per paper | — |
| `explorer` | Data discovery and feasibility assessment | `data-quality-surveyor` |
| `data-quality-surveyor` | Data quality critique: validity, sample, identification fit | — |
| `causal-strategist` | Identification strategy design: DiD, IV, RDD, event study | `econometrics-critic` |
| `econ-finance-theorist` | Formal economic/finance model builder — equilibrium, proofs, LaTeX | `econometrics-critic` |
| `structural-estimation-expert` | Structural model design + estimation strategy (MLE, GMM, SMM) | `econometrics-critic` |
| `econometrics-critic` | Reviews causal design, theory models, and structural estimation | — |
| `Coder` (main Claude) | R / Python / Stata analysis scripts | `debugger` |
| `debugger` | Code quality: 12-category audit — reproducibility, alignment, polish | — |
| `economics-paper-writer` | Paper drafting with anti-hedging, effect sizes, econometric notation | `academic-proofreader` |
| `academic-proofreader` | Manuscript polish: 6-category review — structure, claims, writing, grammar | — |
| `storyteller` | Beamer / Quarto presentation builder derived from `paper/main.tex` | `discussant` |
| `discussant` | Slide quality review: layout, paper fidelity, narrative arc | — |
| `replication-verifier` | Replication audit: compilation, script execution, output freshness | — |

---

## Governance: 22 Rules

The `.claude/rules/` directory contains the operational rules Claude follows:

| Rule File | What It Governs |
|-----------|----------------|
| `adversarial-pairing.md` | Every creator has a paired critic; critics never edit |
| `dependency-graph.md` | Phases activate by dependency, not sequence |
| `domain-profile.md` | Field-specific conventions, journals, data sources |
| `exploration-fast-track.md` | Fast-track protocol for exploratory work |
| `exploration-folder-protocol.md` | `explorations/` folder conventions and quality gate (60/100) |
| `lessons-protocol.md` | Append-only lessons log for project-specific corrections |
| `meta-governance.md` | Generic vs specific content — what commits, what stays local |
| `orchestrator-protocol.md` | Contractor mode: dependency loop, verification, limits |
| `pdf-processing.md` | Rules for reading and extracting content from PDFs |
| `plan-first-workflow.md` | Enter plan mode for non-trivial tasks; requirements spec |
| `quality-gates.md` | Score thresholds: 80 (commit), 90 (PR), 95 (submission) |
| `research-journal.md` | Append-only agent log after every agent invocation |
| `revision-protocol.md` | R&R cycle: classify referee comments, route to agents |
| `scoring-protocol.md` | Weighted aggregation formula; type-specific weight tables |
| `separation-of-powers.md` | Critics never create; creators can't self-score |
| `session-logging.md` | Three log triggers: post-plan, incremental, end-of-session |
| `session-reporting.md` | `SESSION_REPORT.md` — consolidated append-only operations log |
| `severity-gradient.md` | Critics calibrate severity by phase: Discovery → Peer Review |
| `single-source-of-truth.md` | `paper/main.tex` is authoritative; talks derive from it |
| `standalone-access.md` | Any skill can run standalone, bypassing the pipeline |
| `table-generator.md` | Standards for generating LaTeX/Markdown tables from code |
| `three-strikes.md` | Worker-critic pairs: max 3 rounds, then escalate |

---

## Hooks

The `.claude/hooks/` directory contains Python/shell hooks that enforce workflow discipline:

| Hook | Trigger | Purpose |
|------|---------|---------|
| `context-monitor.py` | Tool call | Warns when context is approaching compression threshold |
| `log-reminder.py` | Tool call | Reminds Claude to update session logs proactively |
| `notify.py` | Tool call | Desktop notification on long-running agent completions |
| `post-compact-restore.py` | Post-compact | Restores context after auto-compression |
| `post-merge.sh` | Post-merge | Runs quality report generation after branch merge |
| `pre-compact.py` | Pre-compact | Saves MEMORY.md + session log before compression |
| `protect-files.py` | File write | Blocks writes to protected files (e.g., `paper/main.tex`) |
| `quality-gate.py` | Commit | Blocks commits with aggregate score below 80 |
| `verify-reminder.py` | Tool call | Reminds Claude to verify outputs after implementation |

---

## Quality Gates & Scoring

### Gates

| Score | Gate | Condition |
|-------|------|-----------|
| ≥ 95 | Submission | All individual components ≥ 80 |
| ≥ 90 | PR | Weighted aggregate |
| ≥ 80 | Commit | Weighted aggregate |
| 60 | Exploration | `explorations/` folder — advisory only |
| < 80 | Blocked | Must fix before advancing |

### Type-Specific Scoring Weights

The orchestrator reads `project_type` from the research spec and applies the matching weight column. Missing components are excluded and remaining weights are renormalized.

| Component | Source Agent | Empirical | Theory | Structural | Emp+Theory |
|-----------|-------------|:---------:|:------:|:----------:|:----------:|
| Literature coverage | `academic-editor` | 10% | 15% | 10% | 10% |
| Data quality | `data-quality-surveyor` | 10% | — | 10% | 10% |
| Theory model | `econometrics-critic` | — | 40% | 15% | 10% |
| Identification validity | `econometrics-critic` | 25% | — | — | 20% |
| Structural estimation | `econometrics-critic` | — | — | 20% | — |
| Code quality | `debugger` | 15% | — | 15% | 15% |
| Paper quality | blind-peer-referee avg | 25% | 30% | 20% | 25% |
| Manuscript polish | `academic-proofreader` | 10% | 15% | 5% | 5% |
| Replication readiness | `replication-verifier` | 5% | — | 5% | 5% |
| **Total** | | **100%** | **100%** | **100%** | **100%** |

---

## Quick Start

**Prerequisites:**
- [Claude Code](https://claude.ai/code): `npm install -g @anthropic/claude-code`
- [GitHub CLI](https://cli.github.com): `gh auth login`
- LaTeX distribution (for paper compilation): TeX Live or MiKTeX

**Steps:**

```bash
# 1. Clone the repository
git clone https://github.com/jfimbet/cloco && cd cloco

# 2. Open CLAUDE.md and fill in your project details
#    Replace [Your Project Name] and [Your Institution]

# 3. Fill in .claude/rules/domain-profile.md with your field,
#    target journals, data sources, and identification strategies

# 4. Start Claude Code
claude

# 5. Begin your research session
/interview-me [your research topic]
```

That's it. The orchestrator will guide you through the rest.

---

## Folder Structure

```
cloco/
├── CLAUDE.md                       # Project instructions for Claude
├── README.md                       # This file
├── SESSION_REPORT.md               # Consolidated append-only operations log
├── .gitignore
├── .claude/
│   ├── agents/                     # 16 agent definitions
│   ├── skills/                     # 31 skill definitions
│   ├── rules/                      # 22 governance rules
│   ├── hooks/                      # Workflow enforcement hooks
│   ├── lessons/
│   │   └── LESSONS.md              # Project-specific corrections (append-only)
│   └── agent-memory/               # Per-agent persistent memory
├── paper/
│   ├── main.tex                    # Single source of truth
│   ├── references.bib
│   ├── sections/
│   ├── figures/
│   ├── tables/
│   └── appendix/
├── code/                           # Analysis scripts (R, Python, Stata)
├── data/
│   ├── raw/
│   └── processed/
├── talks/                          # Beamer / Quarto presentations
├── output/                         # Intermediate results and logs
├── replication/                    # Replication package
├── quality_reports/
│   ├── session_logs/               # Per-session logs
│   ├── plans/                      # Approved implementation plans
│   ├── specs/                      # Requirements specifications
│   └── research_journal.md         # Agent-level research history
├── templates/                      # Session log, quality report templates
└── master_supporting_docs/         # Reference papers and data documentation
```

---

## Customization

### 1. Fill in your domain profile

Edit `.claude/rules/domain-profile.md`:
- **Field** — your primary field and adjacent subfields
- **Target journals** — ranked by tier
- **Common data sources** — with access and quirk notes
- **Identification strategies** — the ones your field uses
- **Field conventions** — notation, clustering, welfare analysis expectations

### 2. Adjust quality thresholds

Edit `.claude/rules/quality-gates.md` to raise or lower gate thresholds for your standards. The defaults (80/90/95) are conservative.

### 3. Set your project type

When you run `/interview-me`, Claude will ask for your project type. This sets the scoring weight column used throughout the pipeline. You can also set it manually in the research spec.

### 4. Local settings

Machine-specific settings (LaTeX paths, personal tool preferences) go in `.claude/settings.local.json` (gitignored) or `.claude/state/personal-memory.md` (gitignored). These stay local — the repo only commits generic patterns.

---

## License

MIT License. See [LICENSE](LICENSE) for details.

The upstream projects ([clo-author](https://hsantanna88.github.io/clo-author/) and [claude-code-my-workflow](https://github.com/pedrohcgs/claude-code-my-workflow)) are also MIT licensed.

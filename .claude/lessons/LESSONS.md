# Lessons Learned

Append-only log of mistakes, corrections, and prevention strategies.
Read this at the start of every session. Never edit or delete past entries.

---

## Format

```
### YYYY-MM-DD — [Category]
**Mistake:** What went wrong or what was done incorrectly.
**Correction:** What the right approach is.
**Prevention:** Concrete rule or check to avoid repeating this.
```

Categories: `workflow` · `tools` · `writing` · `econometrics` · `code` · `latex` · `agents` · `planning`

---

<!-- New lessons go below this line, most recent first -->

### 2026-03-17 — code
**Mistake:** When porting Python estimation code to Julia, used a simplified "monotonicity proxy" penalty instead of porting the actual restriction implementations. This produced fake results (0% gain) and wasted a full test run.
**Correction:** When porting code across languages, replicate the exact logic from the source. Read the actual Python restriction classes and translate them 1:1, using the same data_context keys, the same correlation-based formulas, the same sign conventions.
**Prevention:** Before writing any cross-language port, list every function that needs porting, read its source, and translate it literally. Never substitute a "simplified version" unless explicitly asked.

### 2026-03-17 — writing
**Mistake:** Used `\paragraph{}` and `\textbf{}` headers throughout paper sections (empirical.tex, estimation.tex). This creates a choppy, list-like structure that reads like documentation, not like a natural academic paper.
**Correction:** Write flowing prose with natural transitions between topics. Introduce new topics with a sentence, not a bold label. For example, instead of `\paragraph{Returns.} We obtain monthly stock returns...`, write `We obtain monthly stock returns from CRSP...` or use a transitional sentence to move between topics.
**Prevention:** Before writing any paper section, check: does this read like a published economics paper or like a technical manual? Never use `\paragraph{}` in the data or results sections. Reserve `\paragraph{}` only for estimation/methodology sections where enumerated approaches are genuinely needed (e.g., "Approach 1", "Approach 2").

### 2026-03-16 — tools
**Mistake:** Tried to run Python directly without activating conda first. Conda is not initialized in the default bash shell.
**Correction:** Before any Python command, initialize conda and activate the correct environment:
```bash
eval "$('/c/Users/jimbet/AppData/Local/anaconda3/Scripts/conda.exe' 'shell.bash' 'hook')" && conda activate base
```
**Prevention:** Always run the conda init + activate command before any Python/pip invocation. Check LESSONS.md at session start for this rule.

---
name: optimize-code
description: "Optimize a script for speed: parallelize loops, vectorize, reduce allocations, exploit GPU/SIMD, cache computations. Reads the input file, produces an optimized copy. Supports Julia, Python, R."
argument-hint: "<input_file> [output_file]"
allowed-tools: ["Read", "Write", "Grep", "Glob", "Bash", "Agent"]
---

# Optimize Code for Speed

Accept a source file, analyze it for performance bottlenecks, and produce an optimized version.

## Arguments

- `$ARGUMENTS` format: `<input_file> [output_file]`
- If `output_file` is omitted, default to `<input_file_stem>_optimized.<ext>` in the same directory.

## Workflow

### Phase 1: Profile & Diagnose

Read the input file and identify the language (Julia, Python, R, etc.).

Build a **bottleneck inventory** by scanning for these patterns:

#### Julia-specific
| Pattern | Symptom | Priority |
|---------|---------|----------|
| `for i in 1:n` over large n without `@threads`/`@simd` | Serial loop | HIGH |
| `push!` in hot loop (growing arrays) | Repeated allocation | HIGH |
| Type-unstable containers (`Any[]`, untyped `Dict`) | Dynamic dispatch | HIGH |
| Allocating temporaries inside loops (`zeros(n)`, `similar()`) | GC pressure | MEDIUM |
| `hcat`/`vcat` in loop (builds matrix column-by-column) | O(n²) copy | HIGH |
| Repeated identical computation across iterations | Missing cache/memo | MEDIUM |
| Global variables used in hot path | Type instability | HIGH |
| Missing `@inbounds` on safe indexed loops | Bounds-check overhead | LOW |
| `Array` operations that could use `@views` | Unnecessary copies | MEDIUM |
| Kernel/matrix ops that could run on GPU | Underusing hardware | MEDIUM |
| Independent iterations that could be `Threads.@threads` | Underusing cores | HIGH |
| `sort`/`sortperm` called repeatedly on same data | Redundant work | MEDIUM |
| Broadcasting with `.=` instead of allocating new array | Allocation | MEDIUM |

#### Python-specific
| Pattern | Symptom | Priority |
|---------|---------|----------|
| Python `for` loop over array elements | Use numpy vectorization | HIGH |
| `append()` in loop | Pre-allocate with numpy | MEDIUM |
| Repeated `pd.concat` in loop | Collect then concat once | HIGH |
| No `numba.jit` on numeric hot loops | Missing JIT | HIGH |
| `apply()` row-wise on DataFrame | Vectorize with numpy | MEDIUM |
| No `joblib.Parallel` for independent iterations | Underusing cores | MEDIUM |
| Redundant `.copy()` calls | Unnecessary allocation | LOW |

#### R-specific
| Pattern | Symptom | Priority |
|---------|---------|----------|
| `for` loop with `rbind`/`c()` growing objects | Pre-allocate | HIGH |
| `apply` family where vectorized alternative exists | Use vectorized op | MEDIUM |
| No `data.table` for large group-by operations | Use data.table | MEDIUM |
| Missing `Rcpp` for tight numeric loops | Bottleneck in R | HIGH |
| No `future`/`parallel` for independent tasks | Underusing cores | MEDIUM |

### Phase 2: Optimization Strategy

For each bottleneck found, classify the fix:

1. **Parallelize** — `@threads`, `Threads.@spawn`, `@distributed`, `pmap`, `joblib.Parallel`
2. **Vectorize** — replace scalar loops with matrix/broadcast ops
3. **Pre-allocate** — replace `push!`/`append` with pre-sized arrays
4. **Cache/Memoize** — compute once, reuse (e.g., kernel matrices, sort indices)
5. **GPU offload** — move large matrix ops to CuArray/torch.cuda
6. **Reduce allocation** — `@views`, in-place operations (`.=`, `mul!`, `ldiv!`)
7. **Type-stabilize** — add type annotations, avoid `Any` containers
8. **Algorithm change** — better asymptotic complexity (e.g., avoid O(n²) when O(n log n) exists)

Rank fixes by **expected speedup × implementation safety**. Prioritize:
- Safe, high-impact changes first (pre-allocate, vectorize, cache)
- Parallel changes second (need to verify independence)
- Algorithm changes last (highest risk of introducing bugs)

### Phase 3: Generate Optimized File

Write the optimized file to `output_file`. Follow these rules:

1. **Preserve correctness** — the optimized file MUST produce identical outputs to the original. When in doubt, keep the original.
2. **Add comments** — mark every optimization with `# OPT: <description>` so the user can review.
3. **Keep structure** — maintain the same function signatures, section organization, and variable names where possible. Don't refactor beyond what's needed for speed.
4. **Benchmark hooks** — add timing instrumentation around the optimized sections:
   - Julia: `@time` or `@elapsed` blocks
   - Python: `time.perf_counter()` pairs
   - R: `system.time()` blocks
5. **Fallback safety** — for GPU operations, keep CPU fallback. For threading, ensure thread-safe access.

#### Julia-specific optimizations to apply:

```julia
# Pre-allocate instead of push!
result = Vector{Float64}(undef, n)  # OPT: pre-allocate
for i in 1:n
    result[i] = compute(i)
end

# @threads for independent iterations
Threads.@threads for i in 1:n  # OPT: parallelize independent loop
    result[i] = expensive_fn(i)
end

# @views to avoid copies
@views X_sub = X[mask, :]  # OPT: view instead of copy

# @inbounds for safe indexed loops
@inbounds for i in 1:n  # OPT: skip bounds check (loop range verified)
    y[i] = X[i, :] .* w
end

# In-place operations
mul!(ZtZ, Z', Z)  # OPT: in-place matrix multiply
ldiv!(cholesky(A), b)  # OPT: in-place solve

# Cache repeated computations
# OPT: cache — computed once, used N times
cached_result = expensive_computation()
for i in 1:n
    use(cached_result)
end

# Type-stable containers
result = Dict{Int, Float64}()  # OPT: typed dict (was Dict())

# Broadcast fusion
@. y = a * x + b  # OPT: fused broadcast (single allocation)
```

### Phase 4: Report

After writing the optimized file, print a summary:

```
Optimization Report: <input_file> → <output_file>
═══════════════════════════════════════════════════

Bottlenecks found: N
Optimizations applied: M

| # | Line(s) | Type | Description | Est. Speedup |
|---|---------|------|-------------|-------------|
| 1 | 150-180 | Parallelize | @threads on CD grid search | 8-16x |
| 2 | 320-340 | Pre-allocate | Replace push! with pre-sized Vector | 2-3x |
| ...

Unchanged sections: [list sections left as-is and why]

To verify correctness:
  1. Run original:   julia <input_file>
  2. Run optimized:  julia <output_file>
  3. Compare outputs: diff output/cv_results.csv output/cv_results_opt.csv
```

### Phase 5: Correctness Guard

Before finishing, verify:
- [ ] All function signatures unchanged
- [ ] All output file paths unchanged (or parameterized)
- [ ] Random seed preserved in same position
- [ ] No data races in parallel sections (each thread writes to independent indices)
- [ ] GPU operations have CPU fallback
- [ ] No global mutable state accessed from @threads without locks

If any check fails, revert that specific optimization and note it in the report.

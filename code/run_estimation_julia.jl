"""
GPU + multicore Bayesian optimization for Theory-KRR — Julia implementation.
Uses Nystrom approximation for speed regardless of data size.

Run:
    julia --threads=auto code/run_bayesian_cv.jl

Exploits:
  - CUDA GPU for kernel computation
  - Julia native threads for parallel grid search and BO trials
  - Nystrom low-rank approximation: O(n·m²) instead of O(n³)
"""

using LinearAlgebra
using Statistics
using Parquet2
using DataFrames
using CUDA
using Optim
using ProgressMeter
using Random
using Printf
using Dates
using JSON
using GLMNet

include("restrictions_julia.jl")

# ════════════════════════════════════════════════════════════════════
#  Configuration
# ════════════════════════════════════════════════════════════════════

const PANEL_PATH = "data/processed/panel_monthly.parquet"
const LAMBDA_STAT = 1e-4
const NYSTROM_M = 500  # number of landmark points

# Read config from .env file (matching Python's code/config.py)
function _read_env()
    env = Dict{String,String}()
    env_path = joinpath(@__DIR__, "..", ".env")
    if isfile(env_path)
        for line in readlines(env_path)
            line = strip(line)
            (isempty(line) || startswith(line, '#')) && continue
            '=' in line || continue
            k, v = split(line, '=', limit=2)
            env[strip(k)] = strip(v)
        end
    end
    return env
end

const _ENV = _read_env()
const TEST_MODE = lowercase(get(_ENV, "TEST_MODE", "true")) in ("true", "1", "yes")
const TEST_MAX_STOCKS_PER_MONTH = parse(Int, get(_ENV, "TEST_MAX_STOCKS_PER_MONTH", "200"))
const TEST_MAX_ROLLING_WINDOWS = parse(Int, get(_ENV, "TEST_MAX_ROLLING_WINDOWS", "3"))

# GKX-style 3-way split parameters
const VAL_YEARS = 12       # 12-year validation window (matching GKX)
const OOS_START_YEAR = 1987  # first OOS year (matching GKX)
const REBALANCE_FREQ = 12  # annual rebalancing (months)

const GROUP_NAMES = Dict(
    0 => "consumption", 1 => "production", 2 => "intermediary",
    3 => "information", 4 => "demand", 5 => "volatility",
    6 => "behavioral", 7 => "macro",
)

const SELECTED_CHARS = ["streversal", "ik", "roe", "leverage", "bm", "roa", "gp"]

# ════════════════════════════════════════════════════════════════════
#  Hardware detection
# ════════════════════════════════════════════════════════════════════

function detect_hardware()
    println("=" ^ 60)
    println("  HARDWARE DETECTION")
    println("=" ^ 60)
    println("  Julia:       v$(VERSION)")
    println("  Threads:     $(Threads.nthreads())")
    println("  CPU cores:   $(Sys.CPU_THREADS)")
    ram_gb = Sys.total_memory() / 1e9
    println("  RAM:         $(round(ram_gb, digits=0)) GB")
    println("  Nystrom m:   $(NYSTROM_M) landmarks")

    has_gpu = CUDA.functional()
    if has_gpu
        dev = CUDA.device()
        println("  GPU:         $(CUDA.name(dev))")
        vram = CUDA.totalmem(dev) / 1e9
        println("  VRAM:        $(round(vram, digits=1)) GB")
        t0 = time()
        a = CUDA.randn(Float64, 2000, 2000)
        _ = a * a'
        CUDA.synchronize()
        println("  GPU bench:   2000x2000 matmul in $(@sprintf("%.4f", time()-t0))s")
    else
        println("  GPU:         NOT AVAILABLE")
    end
    println("=" ^ 60)
    println()
    return has_gpu
end

# ════════════════════════════════════════════════════════════════════
#  Data loading
# ════════════════════════════════════════════════════════════════════

function load_panel()
    df = DataFrame(Parquet2.Dataset(PANEL_PATH))
    if TEST_MODE
        println("  [TEST_MODE] Subsampling to $TEST_MAX_STOCKS_PER_MONTH stocks/month")
        Random.seed!(42)
        df = combine(groupby(df, :yyyymm)) do g
            n = min(nrow(g), TEST_MAX_STOCKS_PER_MONTH)
            g[randperm(nrow(g))[1:n], :]
        end
    end
    return df
end

# ════════════════════════════════════════════════════════════════════
#  Kernel functions
# ════════════════════════════════════════════════════════════════════

function median_heuristic(X::Matrix{Float64}; subsample::Int=5000)
    n = size(X, 1)
    if n > subsample
        idx = randperm(n)[1:subsample]
        X = X[idx, :]
    end
    dists = Float64[]
    for i in 1:size(X,1), j in (i+1):size(X,1)
        push!(dists, sqrt(sum((X[i,:] .- X[j,:]).^2)))
    end
    return median(dists)
end

function _sq_dists(X::Matrix{Float64}, Y::Matrix{Float64})
    norms_x = sum(X.^2, dims=2)
    norms_y = sum(Y.^2, dims=2)
    return norms_x .+ norms_y' .- 2 * X * Y'
end

function gaussian_rbf(X::Matrix{Float64}, Y::Matrix{Float64}; sigma::Float64=1.0)
    gamma = 1.0 / (2.0 * sigma^2)
    return exp.(-gamma .* _sq_dists(X, Y))
end

function gaussian_rbf_gpu(X::Matrix{Float64}, Y::Matrix{Float64}; sigma::Float64=1.0)
    gamma = 1.0 / (2.0 * sigma^2)
    X_gpu = CuArray{Float64}(X)
    Y_gpu = CuArray{Float64}(Y)
    norms_x = sum(X_gpu.^2, dims=2)
    norms_y = sum(Y_gpu.^2, dims=2)
    sq_dists = norms_x .+ norms_y' .- 2 * X_gpu * Y_gpu'
    K_gpu = exp.(-gamma .* sq_dists)
    return Array(K_gpu)
end

# ════════════════════════════════════════════════════════════════════
#  Nystrom approximation
# ════════════════════════════════════════════════════════════════════

"""
Nystrom features: Z = K_nm @ K_mm^{-1/2}, shape (n, m).

KRR with Nystrom:
  K ≈ Z @ Z'
  (K + nλI)α = y  →  α ≈ Z @ (Z'Z + nλI_m)^{-1} @ Z' @ y

  Equivalently, solve the m×m system:
    β = (Z'Z + nλI_m)^{-1} Z' y     (m×m solve)
    predictions = Z_new @ β           (cheap)
"""
struct NystromFeatures
    Z_tr::Matrix{Float64}     # (n_tr, m) training features
    Z_val::Matrix{Float64}    # (n_val, m) validation features
    sigma::Float64
    m::Int
    landmarks::Matrix{Float64}
end

function compute_nystrom(
    X_tr::Matrix{Float64}, X_val::Matrix{Float64};
    sigma::Float64=1.0, m::Int=500, has_gpu::Bool=false,
)
    n = size(X_tr, 1)
    m_actual = min(m, n)

    # Select landmarks uniformly at random from training data
    idx = randperm(n)[1:m_actual]
    landmarks = X_tr[idx, :]

    # Compute kernel blocks
    if has_gpu
        K_nm = gaussian_rbf_gpu(X_tr, landmarks; sigma=sigma)      # n × m
        K_mm = gaussian_rbf_gpu(landmarks, landmarks; sigma=sigma)  # m × m
        K_vm = gaussian_rbf_gpu(X_val, landmarks; sigma=sigma)      # n_val × m
    else
        K_nm = gaussian_rbf(X_tr, landmarks; sigma=sigma)
        K_mm = gaussian_rbf(landmarks, landmarks; sigma=sigma)
        K_vm = gaussian_rbf(X_val, landmarks; sigma=sigma)
    end

    # K_mm^{-1/2} via eigendecomposition
    eig = eigen(Symmetric(K_mm))
    vals = max.(eig.values, 1e-10)  # numerical stability
    K_mm_inv_sqrt = eig.vectors * Diagonal(1.0 ./ sqrt.(vals)) * eig.vectors'

    # Nystrom features
    Z_tr = K_nm * K_mm_inv_sqrt    # (n, m)
    Z_val = K_vm * K_mm_inv_sqrt   # (n_val, m)

    return NystromFeatures(Z_tr, Z_val, sigma, m_actual, landmarks)
end

# ════════════════════════════════════════════════════════════════════
#  KRR with Nystrom (fast: m×m solve instead of n×n)
# ════════════════════════════════════════════════════════════════════

function nystrom_krr_solve(Z::Matrix{Float64}, y::Vector{Float64}, λ::Float64)
    n = length(y)
    m = size(Z, 2)
    # β = (Z'Z + nλI_m)^{-1} Z' y — this is an m×m system
    ZtZ = Z' * Z
    A = ZtZ + n * λ * I(m)
    Zty = Z' * y
    β = cholesky(Symmetric(A)) \ Zty
    return β
end

function nystrom_predict(Z::Matrix{Float64}, β::Vector{Float64})
    return Z * β
end

# ════════════════════════════════════════════════════════════════════
#  Baseline models (GKX horse race)
# ════════════════════════════════════════════════════════════════════

"""Fit OLS and predict. Returns predicted values on X_test."""
function fit_predict_ols(X_tr, y_tr, X_te)
    n, p = size(X_tr)
    X1 = hcat(ones(n), X_tr)
    beta = X1 \ y_tr
    return hcat(ones(size(X_te, 1)), X_te) * beta
end

"""Fit Ridge (closed-form) with CV over λ grid. Returns test predictions."""
function fit_predict_ridge(X_tr, y_tr, X_val, y_val, X_te)
    n, p = size(X_tr)
    X1 = hcat(ones(n), X_tr)
    Xv1 = hcat(ones(size(X_val, 1)), X_val)
    Xt1 = hcat(ones(size(X_te, 1)), X_te)
    best_mse = Inf
    best_beta = zeros(p + 1)
    for log_lam in range(-4, 2, length=20)
        lam = 10.0^log_lam
        # Don't penalize intercept
        D = lam * I(p + 1)
        D[1, 1] = 0.0
        beta = (X1' * X1 + n * D) \ (X1' * y_tr)
        mse = mean((y_val .- Xv1 * beta).^2)
        if mse < best_mse
            best_mse = mse
            best_beta = beta
        end
    end
    return Xt1 * best_beta
end



"""Fit Lasso via GLMNet with CV. Returns test predictions."""
function fit_predict_lasso(X_tr, y_tr, X_val, y_val, X_te)
    # GLMNet wants Float64 matrices
    path = glmnet(X_tr, y_tr; alpha=1.0)
    # Pick λ by validation MSE
    best_mse = Inf
    best_idx = 1
    for j in 1:length(path.lambda)
        beta = path.betas[:, j]
        a0 = path.a0[j]
        pred_val = X_val * beta .+ a0
        mse = mean((y_val .- pred_val).^2)
        if mse < best_mse
            best_mse = mse
            best_idx = j
        end
    end
    beta = path.betas[:, best_idx]
    a0 = path.a0[best_idx]
    return X_te * beta .+ a0
end

"""Fit Elastic Net via GLMNet (alpha=0.5) with CV. Returns test predictions."""
function fit_predict_elasticnet(X_tr, y_tr, X_val, y_val, X_te)
    path = glmnet(X_tr, y_tr; alpha=0.5)
    best_mse = Inf
    best_idx = 1
    for j in 1:length(path.lambda)
        beta = path.betas[:, j]
        a0 = path.a0[j]
        pred_val = X_val * beta .+ a0
        mse = mean((y_val .- pred_val).^2)
        if mse < best_mse
            best_mse = mse
            best_idx = j
        end
    end
    beta = path.betas[:, best_idx]
    a0 = path.a0[best_idx]
    return X_te * beta .+ a0
end

# ════════════════════════════════════════════════════════════════════
#  Managed portfolios
# ════════════════════════════════════════════════════════════════════

const EXTRA_COLS = [
    "cons_growth", "mktrf", "rf", "cay", "hkm_capital_ratio",
    "hkm_risk_factor", "sentiment", "ebp", "vix", "realized_var",
    "term_spread", "default_spread", "grcapx", "LRreversal",
    "me", "ForecastDispersion", "IdioVol3F",
]

function build_managed_portfolios(df::DataFrame, chars::Vector{String})
    months = sort(unique(df.yyyymm))
    char_syms = Symbol.(chars)
    # All columns to carry: chars + extra (macro, restriction inputs)
    all_carry = vcat(char_syms, [Symbol(c) for c in EXTRA_COLS if hasproperty(df, Symbol(c))])
    all_carry = unique(all_carry)

    out_yyyymm = Int[]
    out_port_id = String[]
    out_port_ret = Float64[]
    out_cols = Dict(s => Float64[] for s in all_carry)

    function _push_row!(ym, pid, ret, mdf_sub)
        push!(out_yyyymm, ym)
        push!(out_port_id, pid)
        push!(out_port_ret, ret)
        for s in all_carry
            if hasproperty(mdf_sub, s)
                v = collect(skipmissing(mdf_sub[!, s]))
                push!(out_cols[s], isempty(v) ? 0.0 : mean(v))
            else
                push!(out_cols[s], 0.0)
            end
        end
    end

    for m in months
        mdf = df[df.yyyymm .== m, :]
        nrow(mdf) == 0 && continue

        ret_vals = collect(skipmissing(mdf.RET))
        isempty(ret_vals) && continue
        _push_row!(m, "MKT_EW", mean(ret_vals), mdf)

        for (c, s) in zip(chars, char_syms)
            hasproperty(mdf, s) || continue
            col = mdf[!, s]
            valid_mask = .!ismissing.(col) .& .!isnan.(coalesce.(col, NaN))
            valid_idx = findall(valid_mask)
            length(valid_idx) < 25 && continue

            vals = Float64.(coalesce.(col[valid_idx], 0.0))
            rets = Float64.(coalesce.(mdf.RET[valid_idx], 0.0))
            perm = sortperm(vals)
            qsize = length(perm) ÷ 5

            for q in 1:5
                lo = (q-1)*qsize + 1
                hi = q == 5 ? length(perm) : q*qsize
                qidx = perm[lo:hi]
                _push_row!(m, "$(c)_Q$(q)", mean(rets[qidx]), mdf[valid_idx[qidx], :])
            end
        end
    end

    result = DataFrame(:yyyymm => out_yyyymm, :port_id => out_port_id, :port_ret => out_port_ret)
    for s in all_carry
        result[!, s] = out_cols[s]
    end
    return result
end

# ════════════════════════════════════════════════════════════════════
#  Theory-KRR with Nystrom + L-BFGS (uses real restrictions)
# ════════════════════════════════════════════════════════════════════

function theory_nystrom_fit(
    Z::Matrix{Float64}, y::Vector{Float64}, X::Matrix{Float64},
    λ::Float64, mu_groups::Dict{Int,Float64},
    restrictions::Vector{RestrictionDef}, dc::Dict{String,Vector{Float64}};
    maxiter::Int = 200,
)
    n = length(y)
    m = size(Z, 2)

    β_init = nystrom_krr_solve(Z, y, λ)

    has_active = any(v > 1e-10 for v in values(mu_groups))
    !has_active && return β_init

    # Collect active restrictions with their mu values
    active = Tuple{RestrictionDef, Float64}[]
    for r in restrictions
        g = get(FAMILY_TO_GROUP, r.family, -1)
        mu = get(mu_groups, g, 0.0)
        mu > 1e-10 && push!(active, (r, mu))
    end
    isempty(active) && return β_init

    function obj(β)
        f_hat = Z * β
        residual = y .- f_hat
        loss = dot(residual, residual)
        loss += n * λ * dot(β, β)
        for (r, mu) in active
            try
                loss += mu * r.penalty_fn(f_hat, X, dc)
            catch
            end
        end
        return loss
    end

    function grad!(G, β)
        f_hat = Z * β
        residual = y .- f_hat
        G .= -2.0 .* (Z' * residual) .+ 2.0 * n * λ .* β
        for (r, mu) in active
            try
                g_r = r.gradient_fn(f_hat, X, dc)
                G .+= mu .* (Z' * g_r)
            catch
            end
        end
    end

    result = optimize(obj, grad!, β_init, LBFGS(),
                      Optim.Options(iterations=maxiter, g_tol=1e-6, show_trace=false))
    return Optim.minimizer(result)
end

# ════════════════════════════════════════════════════════════════════
#  Evaluation function (Nystrom)
# ════════════════════════════════════════════════════════════════════

"""
Evaluate a μ configuration by running short L-BFGS on training data,
then computing validation MSE. No Newton approximation — true objective.
"""
function eval_config_lbfgs(
    nys::NystromFeatures, y_tr::Vector{Float64}, y_val::Vector{Float64},
    X_tr::Matrix{Float64}, λ::Float64,
    mu_groups::Dict{Int,Float64},
    restrictions::Vector{RestrictionDef}, dc::Dict{String,Vector{Float64}},
    β_init::Vector{Float64};
    maxiter::Int = 15,
)
    has_active = any(v > 1e-10 for v in values(mu_groups))

    if !has_active
        # Pure KRR — just use β_init (should already be KRR solution)
        pred = nystrom_predict(nys.Z_val, β_init)
        return mean((y_val .- pred).^2)
    end

    # Collect active restrictions
    active = Tuple{RestrictionDef, Float64}[]
    for r in restrictions
        g = get(FAMILY_TO_GROUP, r.family, -1)
        mu = get(mu_groups, g, 0.0)
        mu > 1e-10 && push!(active, (r, mu))
    end

    n = length(y_tr)
    Z = nys.Z_tr

    function obj(β)
        f_hat = Z * β
        residual = y_tr .- f_hat
        loss = dot(residual, residual) + n * λ * dot(β, β)
        for (r, mu) in active
            try; loss += mu * r.penalty_fn(f_hat, X_tr, dc); catch; end
        end
        return loss
    end

    function grad!(G, β)
        f_hat = Z * β
        residual = y_tr .- f_hat
        G .= -2.0 .* (Z' * residual) .+ 2.0 * n * λ .* β
        for (r, mu) in active
            try
                g_r = r.gradient_fn(f_hat, X_tr, dc)
                G .+= mu .* (Z' * g_r)
            catch; end
        end
    end

    result = optimize(obj, grad!, β_init, LBFGS(),
                      Optim.Options(iterations=maxiter, g_tol=1e-6, show_trace=false))
    β_opt = Optim.minimizer(result)
    pred = nystrom_predict(nys.Z_val, β_opt)
    return mean((y_val .- pred).^2)
end

# ════════════════════════════════════════════════════════════════════
#  Predefined mu configurations
# ════════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════════
#  Main
# ════════════════════════════════════════════════════════════════════

function main()
    has_gpu = detect_hardware()
    Random.seed!(42)

    print("[1/5] Loading panel... ")
    t0 = time()
    panel = load_panel()
    @printf("done (%.1fs, %d rows)\n", time()-t0, nrow(panel))

    print("[2/5] Setting up features and restrictions... ")
    t0 = time()
    chars = [c for c in SELECTED_CHARS if hasproperty(panel, Symbol(c))]
    months = sort(unique(panel.yyyymm))
    restrictions = build_all_restrictions()
    @printf("done (%.1fs, %d chars, %d restrictions, %d months)\n",
            time()-t0, length(chars), length(restrictions), length(months))

    # ── GKX-style 3-way split: train | validation (12yr) | test (1yr) ──
    last_year = maximum(months) ÷ 100
    test_years = OOS_START_YEAR:last_year
    if TEST_MODE && length(test_years) > TEST_MAX_ROLLING_WINDOWS
        test_years = (last_year - TEST_MAX_ROLLING_WINDOWS + 1):last_year
        println("[3/5] [TEST_MODE] Last $(TEST_MAX_ROLLING_WINDOWS) windows: $(first(test_years))-$(last_year)")
    else
        println("[3/5] GKX protocol: OOS $(OOS_START_YEAR)-$(last_year), " *
                "$(VAL_YEARS)yr validation, annual rebalancing")
    end
    println("      $(length(test_years)) test windows\n")

    # ── Accumulators for OOS predictions across all windows ──
    all_models = ["hist_mean", "ols", "ridge", "lasso", "elastic_net", "krr", "best_tikrr"]
    oos_realized_all = Dict{String, Vector{Float64}}()
    oos_pred_all = Dict{String, Vector{Float64}}()
    # Monthly long-short returns for Sharpe ratio (per model, per test month)
    ls_returns_all = Dict{String, Vector{Float64}}()
    for m in all_models
        oos_realized_all[m] = Float64[]
        oos_pred_all[m] = Float64[]
        ls_returns_all[m] = Float64[]
    end
    window_results = []  # for cv_window_results.json

    for (w_idx, test_year) in enumerate(test_years)
        println("=" ^ 60)
        @printf("  WINDOW %d/%d — Test year: %d\n", w_idx, length(test_years), test_year)
        println("=" ^ 60)

        # 3-way split boundaries (yyyymm format)
        test_start = test_year * 100 + 1
        test_end   = test_year * 100 + 12
        val_start  = (test_year - VAL_YEARS) * 100 + 1
        val_end    = (test_year - 1) * 100 + 12

        train_df = panel[panel.yyyymm .< val_start, :]
        val_df   = panel[(panel.yyyymm .>= val_start) .& (panel.yyyymm .<= val_end), :]
        test_df  = panel[(panel.yyyymm .>= test_start) .& (panel.yyyymm .<= test_end), :]

        if nrow(train_df) < 1000 || nrow(val_df) == 0 || nrow(test_df) == 0
            println("  SKIP (insufficient data)")
            continue
        end

        train_start_yr = minimum(train_df.yyyymm) ÷ 100
        @printf("  Train: %6d obs (%d-%d)\n", nrow(train_df), train_start_yr, val_start÷100 - 1)
        @printf("  Val:   %6d obs (%d-%d)\n", nrow(val_df), val_start÷100, val_end÷100)
        @printf("  Test:  %6d obs (%d)\n", nrow(test_df), test_year)

        # ── [a] Build managed portfolios (separate for train, val) ──
        print("  [a] Building managed portfolios... ")
        t0 = time()
        port_train = build_managed_portfolios(train_df, chars)
        port_val   = build_managed_portfolios(val_df, chars)
        @printf("done (%.1fs, %d train / %d val)\n",
                time()-t0, nrow(port_train), nrow(port_val))

        # Extract feature matrices
        X_tr_in  = hcat([Float64.(coalesce.(port_train[!, Symbol(c)], 0.0)) for c in chars]...)
        y_tr_in  = Float64.(coalesce.(port_train.port_ret, 0.0))
        X_val_in = hcat([Float64.(coalesce.(port_val[!, Symbol(c)], 0.0)) for c in chars]...)
        y_val_in = Float64.(coalesce.(port_val.port_ret, 0.0))

        n_tr = length(y_tr_in)
        n_val = length(y_val_in)
        @printf("  [b] Train: %d portfolios, Val: %d portfolios\n", n_tr, n_val)

        # Build data_context for restrictions (training data only)
        dc_keys = ["cons_growth", "mktrf", "rf", "cay", "hkm_capital_ratio",
                    "hkm_risk_factor", "sentiment", "ebp", "vix", "realized_var",
                    "term_spread", "default_spread",
                    "ik", "roe", "leverage", "roa", "gp", "ag", "rd_intensity",
                    "bm", "grcapx", "Mom12m", "streversal", "LRreversal",
                    "me", "ForecastDispersion", "IdioVol3F"]
        dc_tr = Dict{String,Vector{Float64}}()
        for k in dc_keys
            s = Symbol(k)
            if hasproperty(port_train, s)
                dc_tr[k] = Float64.(coalesce.(port_train[!, s], 0.0))
            end
        end
        # Add yyyymm for monthly aggregation in time-series penalties
        if hasproperty(port_train, :yyyymm)
            dc_tr["yyyymm"] = Float64.(port_train.yyyymm)
        end

        # ── [c] Compute Nystrom features ──
        m_used = min(NYSTROM_M, n_tr)
        @printf("  [c] Nystrom features (n=%d, m=%d)... ", n_tr, m_used)
        t0 = time()
        sigma = median_heuristic(X_tr_in)
        nys = compute_nystrom(X_tr_in, X_val_in; sigma=sigma, m=m_used, has_gpu=has_gpu)
        nys_time = time() - t0
        mem_mb = (sizeof(nys.Z_tr) + sizeof(nys.Z_val)) / 1e6
        @printf("done (%.2fs, %.0f MB) %s\n", nys_time, mem_mb,
                has_gpu ? "[GPU]" : "[CPU]")

        # ── [d] KRR baseline (Nystrom) ──
        print("  [d] KRR baseline (Nystrom)... ")
        t0 = time()
        β_krr = nystrom_krr_solve(nys.Z_tr, y_tr_in, LAMBDA_STAT)
        krr_pred = nystrom_predict(nys.Z_val, β_krr)
        krr_mse = mean((y_val_in .- krr_pred).^2)
        krr_time = time() - t0
        @printf("Val MSE = %.8f  (%.3fs, %dx%d solve)\n", krr_mse, krr_time, m_used, m_used)

        # ── [e] Cross-validate λ on plain KRR ──
        print("  [e] Cross-validating λ... ")
        t0_lam = time()
        lambda_grid = [1e-6, 1e-5, 1e-4, 1e-3, 1e-2]
        best_lambda = LAMBDA_STAT
        best_lambda_mse = krr_mse
        for lam_try in lambda_grid
            β_try = nystrom_krr_solve(nys.Z_tr, y_tr_in, lam_try)
            pred_try = nystrom_predict(nys.Z_val, β_try)
            mse_try = mean((y_val_in .- pred_try).^2)
            if mse_try < best_lambda_mse
                best_lambda_mse = mse_try
                best_lambda = lam_try
            end
        end
        @printf("done (%.2fs, best λ=%.1e, MSE=%.8f)\n",
                time()-t0_lam, best_lambda, best_lambda_mse)

        # Recompute KRR baseline with best λ
        β_krr = nystrom_krr_solve(nys.Z_tr, y_tr_in, best_lambda)
        krr_pred = nystrom_predict(nys.Z_val, β_krr)
        krr_mse = mean((y_val_in .- krr_pred).^2)

        # ── [f] Coordinate descent on μ (L-BFGS eval) ──
        coarse_grid = vcat([0.0], 10.0 .^ [-4, -3, -2, -1, 0, 1, 2])  # 8 values

        @printf("  [f] Adaptive coordinate descent (L-BFGS eval, %d threads):\n",
                Threads.nthreads())
        t0_cd = time()
        cd_mu = Dict(g => 0.0 for g in 0:7)
        cd_best_mse = krr_mse
        eval_count = 0
        total_est = 8 * length(coarse_grid) * 2 + 8 * 11 * 2
        p_cd = Progress(total_est; desc="      CD:   ", barlen=30, showspeed=true)

        for stage in 1:2
            improved_this_stage = false

            for g in 0:7
                gname = GROUP_NAMES[g]

                if stage == 1
                    grid = coarse_grid
                else
                    current = cd_mu[g]
                    if current < 1e-10
                        grid = vcat([0.0], 10.0 .^ range(-6, -2, length=10))
                    else
                        log_current = log10(current)
                        lo = max(-6, log_current - 1.0)
                        hi = min(3, log_current + 1.0)
                        grid = vcat([0.0], 10.0 .^ range(lo, hi, length=10))
                    end
                end

                n_vals = length(grid)
                mses = Vector{Float64}(undef, n_vals)

                Threads.@threads for k in 1:n_vals
                    mu_test = copy(cd_mu)
                    mu_test[g] = grid[k]
                    mses[k] = eval_config_lbfgs(nys, y_tr_in, y_val_in, X_tr_in,
                                best_lambda, mu_test, restrictions, dc_tr, β_krr;
                                maxiter=15)
                end

                best_k = argmin(mses)
                best_val = grid[best_k]
                best_mse_g = mses[best_k]

                if best_mse_g < cd_best_mse - 1e-12
                    cd_mu[g] = best_val
                    cd_best_mse = best_mse_g
                    improved_this_stage = true
                end

                eval_count += n_vals
                ProgressMeter.update!(p_cd, min(eval_count, total_est);
                    showvalues=[(:stage, stage == 1 ? "coarse" : "fine"),
                                (:group, gname),
                                (:best_mse, @sprintf("%.8f", cd_best_mse))])
            end

            !improved_this_stage && stage == 2 && break
        end
        finish!(p_cd)

        cd_time = time() - t0_cd
        cd_gain = (krr_mse - cd_best_mse) / krr_mse * 100

        active_cd = String[]
        for (g, v) in sort(collect(cd_mu), by=first)
            v > 1e-6 && push!(active_cd, "$(GROUP_NAMES[g])=$(@sprintf("%.4f", v))")
        end

        @printf("      Best MSE=%.8f | Gain=%.3f%% | %.1fs | %d evals\n",
                cd_best_mse, cd_gain, cd_time, eval_count)
        println("      Active: ", isempty(active_cd) ? "none (pure KRR)" : join(active_cd, ", "))

        # ── Summary ──
        println()
        println("  " * "─"^55)
        @printf("  %-28s %12s %8s %8s\n", "Method", "Val MSE", "Gain", "Time")
        println("  " * "─"^55)
        @printf("  %-28s %12.8f %8s %7.3fs\n",
                "KRR baseline", krr_mse, "---", krr_time)
        @printf("  %-28s %12.8f %7.3f%% %7.1fs\n",
                "Theory-KRR (coord descent)", cd_best_mse, cd_gain, cd_time)
        println("  " * "─"^55)

        # ── [g] Re-fit on train+val with best μ, predict on test ──
        print("  [g] OOS prediction on test year $(test_year)... ")
        t0 = time()

        # Combine train + val for final fit
        trainval_df = vcat(train_df, val_df)
        port_trainval = build_managed_portfolios(trainval_df, chars)
        port_test_final = build_managed_portfolios(test_df, chars)

        X_tv = hcat([Float64.(coalesce.(port_trainval[!, Symbol(c)], 0.0)) for c in chars]...)
        y_tv = Float64.(coalesce.(port_trainval.port_ret, 0.0))
        X_test_f = hcat([Float64.(coalesce.(port_test_final[!, Symbol(c)], 0.0)) for c in chars]...)
        y_test_f = Float64.(coalesce.(port_test_final.port_ret, 0.0))

        # Nystrom on train+val
        sigma_tv = median_heuristic(X_tv)
        nys_tv = compute_nystrom(X_tv, X_test_f; sigma=sigma_tv, m=min(NYSTROM_M, size(X_tv,1)), has_gpu=has_gpu)

        # Data context for train+val
        dc_tv = Dict{String,Vector{Float64}}()
        for k in dc_keys
            s = Symbol(k)
            if hasproperty(port_trainval, s)
                dc_tv[k] = Float64.(coalesce.(port_trainval[!, s], 0.0))
            end
        end
        if hasproperty(port_trainval, :yyyymm)
            dc_tv["yyyymm"] = Float64.(port_trainval.yyyymm)
        end

        # ── Fit all models on train+val, predict on test ──
        test_preds = Dict{String, Vector{Float64}}()
        model_times = Dict{String, Float64}()

        # Split trainval for Ridge/Lasso/EN CV
        tv_months = sort(unique(port_trainval.yyyymm))
        tv_val_cut = tv_months[max(1, end - VAL_YEARS*12 + 1)]
        tv_tr_mask = port_trainval.yyyymm .< tv_val_cut
        tv_va_mask = .!tv_tr_mask
        has_val_split = sum(tv_tr_mask) > 10 && sum(tv_va_mask) > 10
        if has_val_split
            X_tv_tr = X_tv[tv_tr_mask, :]
            y_tv_tr = y_tv[tv_tr_mask]
            X_tv_va = X_tv[tv_va_mask, :]
            y_tv_va = y_tv[tv_va_mask]
        end

        function _timed_fit!(name, expr_fn)
            t = time()
            try
                test_preds[name] = expr_fn()
            catch
                test_preds[name] = fill(mean(y_tv), length(y_test_f))
            end
            model_times[name] = time() - t
        end

        # 1. Historical mean
        _timed_fit!("hist_mean", () -> fill(mean(y_tv), length(y_test_f)))

        # 2. OLS
        _timed_fit!("ols", () -> fit_predict_ols(X_tv, y_tv, X_test_f))

        # 3. Ridge
        _timed_fit!("ridge", () -> has_val_split ?
            fit_predict_ridge(X_tv_tr, y_tv_tr, X_tv_va, y_tv_va, X_test_f) :
            fill(mean(y_tv), length(y_test_f)))

        # 4. Lasso
        _timed_fit!("lasso", () -> has_val_split ?
            fit_predict_lasso(X_tv_tr, y_tv_tr, X_tv_va, y_tv_va, X_test_f) :
            fill(mean(y_tv), length(y_test_f)))

        # 5. Elastic net
        _timed_fit!("elastic_net", () -> has_val_split ?
            fit_predict_elasticnet(X_tv_tr, y_tv_tr, X_tv_va, y_tv_va, X_test_f) :
            fill(mean(y_tv), length(y_test_f)))

        # 6. KRR (Nystrom, no theory) — use best_lambda from CV
        _timed_fit!("krr", () -> begin
            β_krr_tv = nystrom_krr_solve(nys_tv.Z_tr, y_tv, best_lambda)
            nystrom_predict(nys_tv.Z_val, β_krr_tv)
        end)

        # 7. Theory-KRR with best μ (from CD) — L-BFGS on β only, μ fixed
        # Same L-BFGS optimizer and same λ as used in μ selection (Fix 3: consistency)
        _timed_fit!("best_tikrr", () -> begin
            has_active_cd = any(v > 1e-10 for v in values(cd_mu))

            β_krr_tv = nystrom_krr_solve(nys_tv.Z_tr, y_tv, best_lambda)

            if !has_active_cd
                nystrom_predict(nys_tv.Z_val, β_krr_tv)
            else
                Z_full = nys_tv.Z_tr
                n_full = length(y_tv)

                active = Tuple{RestrictionDef, Float64}[]
                for r in restrictions
                    g = get(FAMILY_TO_GROUP, r.family, -1)
                    mu = get(cd_mu, g, 0.0)
                    mu > 1e-10 && push!(active, (r, mu))
                end

                function obj_tv(β)
                    f_hat = Z_full * β
                    residual = y_tv .- f_hat
                    loss = dot(residual, residual)
                    loss += n_full * best_lambda * dot(β, β)
                    for (r, mu) in active
                        try; loss += mu * r.penalty_fn(f_hat, X_tv, dc_tv)
                        catch; end
                    end
                    return loss
                end

                function grad_tv!(G, β)
                    f_hat = Z_full * β
                    residual = y_tv .- f_hat
                    G .= -2.0 .* (Z_full' * residual) .+ 2.0 * n_full * best_lambda .* β
                    for (r, mu) in active
                        try
                            g_r = r.gradient_fn(f_hat, X_tv, dc_tv)
                            G .+= mu .* (Z_full' * g_r)
                        catch; end
                    end
                end

                result = optimize(obj_tv, grad_tv!, β_krr_tv, LBFGS(),
                    Optim.Options(iterations=200, g_tol=1e-6, show_trace=false))
                nystrom_predict(nys_tv.Z_val, Optim.minimizer(result))
            end
        end)

        # Print timing breakdown
        println("      Model timing:")
        for m in all_models
            t = get(model_times, m, 0.0)
            @printf("        %-18s %6.2fs\n", m, t)
        end

        # Accumulate OOS predictions for all models
        for m in all_models
            append!(oos_realized_all[m], y_test_f)
            append!(oos_pred_all[m], get(test_preds, m, fill(mean(y_tv), length(y_test_f))))
        end

        # Compute monthly long-short returns for Sharpe ratio
        test_months_unique = sort(unique(port_test_final.yyyymm))
        test_yyyymm_vec = port_test_final.yyyymm
        for m_model in all_models
            pred_m = get(test_preds, m_model, fill(mean(y_tv), length(y_test_f)))
            for mo in test_months_unique
                mo_mask = test_yyyymm_vec .== mo
                sum(mo_mask) < 10 && continue
                y_mo = y_test_f[mo_mask]
                p_mo = pred_m[mo_mask]
                n_mo = sum(mo_mask)
                # Sort by predicted return, top/bottom decile
                perm = sortperm(p_mo)
                d = max(1, n_mo ÷ 10)
                long_ret = mean(y_mo[perm[end-d+1:end]])
                short_ret = mean(y_mo[perm[1:d]])
                push!(ls_returns_all[m_model], long_ret - short_ret)
            end
        end

        oos_time = time() - t0

        @printf("done (%.1fs)\n", oos_time)
        @printf("      Test MSE: HM=%.6f OLS=%.6f Ridge=%.6f Lasso=%.6f KRR=%.6f TIKRR=%.6f\n",
                mean((y_test_f .- test_preds["hist_mean"]).^2),
                mean((y_test_f .- test_preds["ols"]).^2),
                mean((y_test_f .- test_preds["ridge"]).^2),
                mean((y_test_f .- test_preds["lasso"]).^2),
                mean((y_test_f .- test_preds["krr"]).^2),
                mean((y_test_f .- test_preds["best_tikrr"]).^2))

        # Save window result for JSON
        top_mults = Dict{String,Float64}()
        for (g, v) in cd_mu
            v > 1e-6 && (top_mults[GROUP_NAMES[g]] = v)
        end
        push!(window_results, Dict(
            "window" => w_idx,
            "test_year" => test_year,
            "test_start" => test_start,
            "test_end" => test_end,
            "best_config" => isempty(active_cd) ? "krr_only" : join([s for s in active_cd], "+"),
            "best_lambda" => best_lambda,
            "best_val_mse" => cd_best_mse,
            "krr_val_mse" => krr_mse,
            "val_mse_gain_pct" => cd_gain,
            "test_mse_hm" => mean((y_test_f .- test_preds["hist_mean"]).^2),
            "test_mse_krr" => mean((y_test_f .- test_preds["krr"]).^2),
            "test_mse_tikrr" => mean((y_test_f .- test_preds["best_tikrr"]).^2),
            "top_multipliers" => top_mults,
            "mu_groups" => Dict(GROUP_NAMES[g] => v for (g,v) in cd_mu),
        ))

        println()
    end

    # ══════════════════════════════════════════════════════════════
    #  [4/5] Aggregate OOS metrics and save
    # ══════════════════════════════════════════════════════════════

    println("=" ^ 60)
    println("  AGGREGATE OOS RESULTS")
    println("=" ^ 60)

    mkpath("output")

    # R²_OOS = 1 - Σ(y - ŷ)² / Σ(y - ȳ)²
    function r2_oos(realized, predicted, hm_predicted)
        ss_model = sum((realized .- predicted).^2)
        ss_hm = sum((realized .- hm_predicted).^2)
        return ss_hm > 0 ? (1.0 - ss_model / ss_hm) * 100 : 0.0
    end

    # Diebold-Mariano test: compare squared errors
    function dm_test(realized, pred_model, pred_baseline; nlags=6)
        e1 = (realized .- pred_model).^2
        e2 = (realized .- pred_baseline).^2
        d = e2 .- e1  # positive = model is better
        n = length(d)
        n < nlags + 2 && return (0.0, 1.0)
        dbar = mean(d)
        # Newey-West HAC variance
        gamma0 = var(d; corrected=false)
        v = gamma0
        for l in 1:nlags
            gl = 0.0
            for t in (l+1):n
                gl += (d[t] - dbar) * (d[t-l] - dbar)
            end
            gl /= n
            w = 1.0 - l / (nlags + 1)  # Bartlett kernel
            v += 2 * w * gl
        end
        v = max(v, 1e-20)
        dm = dbar / sqrt(v / n)
        return (dm, NaN)  # p-value would need t-distribution CDF
    end

    y_all = oos_realized_all["hist_mean"]
    hm_all = oos_pred_all["hist_mean"]

    println()
    @printf("  %-20s %10s %10s %10s\n", "Model", "R²_OOS(%)", "SR(ann)", "DM vs HM")
    println("  " * "─"^52)

    csv_rows = []
    for model in all_models
        pred = oos_pred_all[model]
        r2 = r2_oos(y_all, pred, hm_all)
        if model == "hist_mean"
            dm_stat = NaN
        else
            dm_stat, _ = dm_test(y_all, pred, hm_all)
        end
        # Annualized Sharpe ratio
        ls = ls_returns_all[model]
        if length(ls) > 1 && std(ls) > 0
            sr_ann = mean(ls) / std(ls) * sqrt(12)
        else
            sr_ann = 0.0
        end

        @printf("  %-20s %10.2f %10.2f %10.2f\n", model, r2, sr_ann, isnan(dm_stat) ? 0.0 : dm_stat)
        # DM vs KRR (for theory-krr comparison)
        dm_vs_krr = NaN
        if model == "best_tikrr" && length(oos_pred_all["krr"]) > 0
            dm_vs_krr, _ = dm_test(y_all, pred, oos_pred_all["krr"])
        end
        push!(csv_rows, Dict("model" => model, "r2_oos_pct" => r2,
                             "sharpe_ann" => sr_ann,
                             "dm_vs_hm" => isnan(dm_stat) ? nothing : dm_stat,
                             "dm_vs_krr" => isnan(dm_vs_krr) ? nothing : dm_vs_krr))
    end
    println()

    # ── Save cv_results.csv ──
    open("output/cv_results.csv", "w") do f
        println(f, ",r2_oos_pct,sharpe_ann,dm_vs_hm,dm_vs_hm_pval,dm_vs_krr,dm_vs_krr_pval")
        for row in csv_rows
            dm_hm = row["dm_vs_hm"]
            dm_hm_str = dm_hm === nothing ? "" : @sprintf("%.2f", dm_hm)
            dm_krr = row["dm_vs_krr"]
            dm_krr_str = dm_krr === nothing ? "" : @sprintf("%.2f", dm_krr)
            @printf(f, "%s,%.2f,%.2f,%s,,%s,\n",
                    row["model"], row["r2_oos_pct"], row["sharpe_ann"], dm_hm_str, dm_krr_str)
        end
    end
    println("  Saved output/cv_results.csv")

    # ── Save cv_window_results.json ──
    open("output/cv_window_results.json", "w") do f
        JSON.print(f, window_results, 2)
    end
    println("  Saved output/cv_window_results.json")

    println("\n[5/5] Done! Run 'python -m code.generate_tables' to update paper tables.")
end

main()

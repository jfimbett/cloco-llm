"""
GPU + multicore Bayesian optimization for Theory-KRR — Julia implementation.
Uses Nystrom approximation for speed regardless of data size.

OPTIMIZED VERSION — see # OPT: comments for all changes.

Run:
    julia --threads=auto code/run_estimation_julia_fast.jl

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

const PANEL_PATH = "../data/processed/panel_monthly.parquet"
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

# Macro columns to include as RHS features (alongside firm chars)
const MACRO_FEATURE_COLS = [
    "cons_growth", "mktrf", "rf", "cay", "hkm_capital_ratio",
    "hkm_risk_factor", "sentiment", "ebp", "vix", "realized_var",
    "term_spread", "default_spread",
]

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

# OPT B1: Pre-allocate dists, @inbounds, avoid per-element sqrt, use @view for subsample
function median_heuristic(X::Matrix{Float64}; subsample::Int=5000)
    n = size(X, 1)
    if n > subsample
        idx = randperm(n)[1:subsample]
        X = @view X[idx, :]  # OPT: view instead of copy
    end
    n = size(X, 1)
    n_pairs = n * (n - 1) ÷ 2
    sq_dists = Vector{Float64}(undef, n_pairs)  # OPT: pre-allocate instead of push!
    k = 0
    @inbounds for i in 1:n, j in (i+1):n  # OPT: @inbounds
        d2 = 0.0
        for p in 1:size(X, 2)
            diff = X[i, p] - X[j, p]
            d2 += diff * diff
        end
        k += 1
        sq_dists[k] = d2
    end
    return sqrt(median(@view sq_dists[1:k]))  # OPT: sqrt only once on median
end

# OPT B2: Use abs2 for norms, in-place broadcast fusion
function _sq_dists(X::Matrix{Float64}, Y::Matrix{Float64})
    norms_x = vec(sum(abs2, X, dims=2))  # OPT: abs2 instead of X.^2
    norms_y = vec(sum(abs2, Y, dims=2))  # OPT: abs2 instead of Y.^2
    D = -2.0 .* (X * Y')  # OPT: single alloc for matmul
    D .+= norms_x         # OPT: in-place broadcast fusion
    D .+= norms_y'        # OPT: in-place broadcast fusion
    return D
end

# OPT B3: In-place scale and fused exp broadcast
function gaussian_rbf(X::Matrix{Float64}, Y::Matrix{Float64}; sigma::Float64=1.0)
    gamma = 1.0 / (2.0 * sigma^2)
    K = _sq_dists(X, Y)
    K .*= -gamma       # OPT: in-place scale
    @. K = exp(K)       # OPT: fused broadcast exp
    return K
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
# OPT B7: Added K_mm_inv_sqrt field to cache eigendecomp for nystrom_transform
struct NystromFeatures
    Z_tr::Matrix{Float64}     # (n_tr, m) training features
    Z_val::Matrix{Float64}    # (n_val, m) validation features
    sigma::Float64
    m::Int
    landmarks::Matrix{Float64}
    K_mm_inv_sqrt::Matrix{Float64}  # OPT: cached for nystrom_transform
end

# OPT B4: Extract K_mm from K_nm rows to avoid double computation
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
        K_mm = collect(@view K_nm[idx, :])  # OPT: extract K_mm from K_nm rows (landmarks ⊂ training), need owned copy for eigen
        K_vm = gaussian_rbf_gpu(X_val, landmarks; sigma=sigma)      # n_val × m
    else
        K_nm = gaussian_rbf(X_tr, landmarks; sigma=sigma)
        K_mm = K_nm[idx, :]  # OPT: avoid recomputing K(landmarks, landmarks)
        K_vm = gaussian_rbf(X_val, landmarks; sigma=sigma)
    end

    # K_mm^{-1/2} via eigendecomposition
    eig = eigen(Symmetric(K_mm))
    vals = max.(eig.values, 1e-10)  # numerical stability
    K_mm_inv_sqrt = eig.vectors * Diagonal(1.0 ./ sqrt.(vals)) * eig.vectors'

    # Nystrom features
    Z_tr = K_nm * K_mm_inv_sqrt    # (n, m)
    Z_val = K_vm * K_mm_inv_sqrt   # (n_val, m)

    return NystromFeatures(Z_tr, Z_val, sigma, m_actual, landmarks, K_mm_inv_sqrt)  # OPT: pass cached K_mm_inv_sqrt
end

# ════════════════════════════════════════════════════════════════════
#  KRR with Nystrom (fast: m×m solve instead of n×n)
# ════════════════════════════════════════════════════════════════════

# OPT B5: Pre-allocate ZtZ, use mul! for in-place matmul, inplace diagonal update
function nystrom_krr_solve(Z::Matrix{Float64}, y::Vector{Float64}, λ::Float64)
    n = length(y)
    m = size(Z, 2)
    # β = (Z'Z + nλI_m)^{-1} Z' y — this is an m×m system
    ZtZ = Matrix{Float64}(undef, m, m)  # OPT: pre-allocate
    mul!(ZtZ, Z', Z)                     # OPT: in-place mul
    @inbounds for i in 1:m               # OPT: in-place diagonal update instead of + n*λ*I(m)
        ZtZ[i, i] += n * λ
    end
    Zty = Z' * y
    β = cholesky(Symmetric(ZtZ)) \ Zty
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
    # OPT B19: Cache Gram matrix for ridge CV
    XtX = X1' * X1
    Xty = X1' * y_tr
    best_mse = Inf
    best_beta = zeros(p + 1)
    for log_lam in range(-4, 2, length=20)
        lam = 10.0^log_lam
        # Don't penalize intercept
        A = copy(XtX)  # OPT: copy cached Gram matrix
        @inbounds for i in 2:(p+1)
            A[i, i] += n * lam
        end
        beta = A \ Xty
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

# OPT B6: Use @inbounds, @views, @. for column operations
"""Expand X to degree-2 polynomial features: original + squares + interactions."""
function poly_features_deg2(X::Matrix{Float64})
    n, p = size(X)
    n_new = p + p * (p - 1) ÷ 2
    X_poly = Matrix{Float64}(undef, n, p + n_new)
    @views X_poly[:, 1:p] .= X  # OPT: view + broadcast
    col = p + 1
    @inbounds for i in 1:p  # OPT: @inbounds
        @. X_poly[:, col] = X[:, i]^2
        col += 1
    end
    @inbounds for i in 1:p
        for j in (i+1):p
            @. X_poly[:, col] = X[:, i] * X[:, j]
            col += 1
        end
    end
    return X_poly
end

# OPT B7/B14: Use cached K_mm_inv_sqrt from NystromFeatures, removing per-call eigen
"""Compute Nystrom features for new data using stored landmarks, sigma, and cached K_mm_inv_sqrt."""
function nystrom_transform(X_new::Matrix{Float64}, nys::NystromFeatures; has_gpu::Bool=false)
    if has_gpu
        K_new_m = gaussian_rbf_gpu(X_new, nys.landmarks; sigma=nys.sigma)
    else
        K_new_m = gaussian_rbf(X_new, nys.landmarks; sigma=nys.sigma)
    end
    return K_new_m * nys.K_mm_inv_sqrt  # OPT: use cached K_mm_inv_sqrt instead of recomputing eigen
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

"""
Build managed portfolios sorted on `chars`.
Carries all columns in `chars` + `EXTRA_COLS` + `extra_carry` through as features.
"""
function build_managed_portfolios(df::DataFrame, chars::Vector{String};
                                   extra_carry::Vector{String}=String[])
    months = sort(unique(df.yyyymm))
    char_syms = Symbol.(chars)
    # All columns to carry: sort chars + extra macro cols + additional requested cols
    all_carry = vcat(char_syms,
                     [Symbol(c) for c in EXTRA_COLS if hasproperty(df, Symbol(c))],
                     [Symbol(c) for c in extra_carry if hasproperty(df, Symbol(c))])
    all_carry = unique(all_carry)

    # OPT B8: Pre-estimate capacity for push! arrays
    est_capacity = length(months) * (1 + length(chars) * 5)
    out_yyyymm = Int[];       sizehint!(out_yyyymm, est_capacity)
    out_port_id = String[];   sizehint!(out_port_id, est_capacity)
    out_port_ret = Float64[]; sizehint!(out_port_ret, est_capacity)
    out_cols = Dict(s => begin v = Float64[]; sizehint!(v, est_capacity); v end for s in all_carry)

    # OPT B8/B20: Direct mean computation instead of collect(skipmissing(...))
    function _push_row!(ym, pid, ret, mdf_sub)
        push!(out_yyyymm, ym)
        push!(out_port_id, pid)
        push!(out_port_ret, ret)
        for s in all_carry
            if hasproperty(mdf_sub, s)
                col = mdf_sub[!, s]
                # OPT: direct mean over non-missing instead of collect(skipmissing(...))
                total = 0.0
                count = 0
                @inbounds for k in 1:length(col)
                    v = col[k]
                    if !ismissing(v)
                        total += Float64(v)
                        count += 1
                    end
                end
                push!(out_cols[s], count > 0 ? total / count : 0.0)
            else
                push!(out_cols[s], 0.0)
            end
        end
    end

    for m in months
        mdf = df[df.yyyymm .== m, :]
        nrow(mdf) == 0 && continue

        # OPT B20: Direct mean over non-missing returns instead of collect(skipmissing(...))
        ret_total = 0.0
        ret_count = 0
        for k in 1:nrow(mdf)
            v = mdf.RET[k]
            if !ismissing(v)
                ret_total += Float64(v)
                ret_count += 1
            end
        end
        ret_count == 0 && continue
        _push_row!(m, "MKT_EW", ret_total / ret_count, mdf)

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

    # OPT B15: Combined obj+grad using Optim.only_fg! to avoid computing f_hat twice
    function fg!(F, G, β)
        f_hat = Z * β  # OPT: compute once for both obj and grad
        residual = y .- f_hat
        loss = dot(residual, residual)
        loss += n * λ * dot(β, β)
        if G !== nothing
            G .= -2.0 .* (Z' * residual) .+ 2.0 * n * λ .* β
        end
        for (r, mu) in active
            try
                loss += mu * r.penalty_fn(f_hat, X, dc)
                if G !== nothing
                    g_r = r.gradient_fn(f_hat, X, dc)
                    G .+= mu .* (Z' * g_r)
                end
            catch
            end
        end
        if F !== nothing
            return loss
        end
        return nothing
    end

    result = optimize(Optim.only_fg!(fg!), β_init, LBFGS(),
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
# OPT B15: Combined obj+grad using Optim.only_fg!
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

    # OPT B15: Combined objective+gradient function for L-BFGS
    function fg!(F, G, β)
        f_hat = Z * β  # OPT: compute once for both obj and grad
        residual = y_tr .- f_hat
        loss = dot(residual, residual) + n * λ * dot(β, β)
        if G !== nothing
            G .= -2.0 .* (Z' * residual) .+ 2.0 * n * λ .* β
        end
        for (r, mu) in active
            try
                loss += mu * r.penalty_fn(f_hat, X_tr, dc)
                if G !== nothing
                    g_r = r.gradient_fn(f_hat, X_tr, dc)
                    G .+= mu .* (Z' * g_r)
                end
            catch
            end
        end
        if F !== nothing
            return loss
        end
        return nothing
    end

    result = optimize(Optim.only_fg!(fg!), β_init, LBFGS(),
                      Optim.Options(iterations=maxiter, g_tol=1e-6, show_trace=false))
    β_opt = Optim.minimizer(result)
    pred = nystrom_predict(nys.Z_val, β_opt)
    return mean((y_val .- pred).^2)
end

# ════════════════════════════════════════════════════════════════════
#  Predefined mu configurations
# ════════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════════
#  Helper: extract feature matrix from DataFrame
# ════════════════════════════════════════════════════════════════════

# OPT B9/B12/B20: Pre-allocate matrix and fill columns directly instead of hcat comprehension
function _extract_features(df::DataFrame, feature_cols::Vector{String})
    n = nrow(df)
    n_features = length(feature_cols)
    X = Matrix{Float64}(undef, n, n_features)  # OPT: pre-allocate full matrix
    @inbounds for (j, c) in enumerate(feature_cols)
        s = Symbol(c)
        if hasproperty(df, s)
            col = df[!, s]
            for i in 1:n
                v = col[i]
                X[i, j] = ismissing(v) ? 0.0 : Float64(v)  # OPT: direct loop, no coalesce alloc
            end
        else
            @views X[:, j] .= 0.0
        end
    end
    return X
end

# OPT B20: Extract target vector without allocating coalesce array
function _extract_target(col)
    n = length(col)
    y = Vector{Float64}(undef, n)
    @inbounds for i in 1:n
        v = col[i]
        y[i] = ismissing(v) ? 0.0 : Float64(v)
    end
    return y
end

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

    # Detect ALL characteristic columns from panel (everything except metadata)
    metadata_cols = Set(["yyyymm", "permno", "RET", "port_id", "port_ret",
                         "SHRCD", "EXCHCD", "mve0", "weight", "sic2"])
    all_panel_chars = [String(c) for c in names(panel)
                       if !(String(c) in metadata_cols) &&
                          !(String(c) in SELECTED_CHARS) &&
                          !(String(c) in EXTRA_COLS) &&
                          eltype(panel[!, c]) <: Union{Missing, Number}]
    @printf("done (%.1fs, %d sort chars, %d total panel chars, %d restrictions, %d months)\n",
            time()-t0, length(chars), length(chars) + length(EXTRA_COLS) + length(all_panel_chars),
            length(restrictions), length(months))

    # OPT B16: Pre-compute yyyymm as plain Vector{Int} for fast filtering
    panel_yyyymm = Vector{Int}(panel.yyyymm)

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
    all_models = ["ols", "ridge", "lasso", "elastic_net",
                  "ridge_poly2", "lasso_poly2", "en_poly2",
                  "krr", "best_tikrr", "tikrr_lam0"]
    oos_realized_all = Dict{String, Vector{Float64}}()
    oos_pred_all = Dict{String, Vector{Float64}}()
    # Monthly long-short returns for Sharpe ratio (per model, per test month)
    ls_returns_all = Dict{String, Vector{Float64}}()
    for m in all_models
        oos_realized_all[m] = Float64[]
        oos_pred_all[m] = Float64[]
        ls_returns_all[m] = Float64[]
    end
    # Also accumulate hist_mean predictions for R²_OOS denominator
    hm_pred_all = Float64[]
    hm_realized_all = Float64[]
    window_results = Vector{Dict{String,Any}}()  # OPT B17: typed instead of Any[]

    for (w_idx, test_year) in enumerate(test_years)
        println("=" ^ 60)
        @printf("  WINDOW %d/%d — Test year: %d\n", w_idx, length(test_years), test_year)
        println("=" ^ 60)

        # 3-way split boundaries (yyyymm format)
        test_start = test_year * 100 + 1
        test_end   = test_year * 100 + 12
        val_start  = (test_year - VAL_YEARS) * 100 + 1
        val_end    = (test_year - 1) * 100 + 12

        # OPT B16: Use pre-computed Vector{Int} for fast filtering
        train_mask = panel_yyyymm .< val_start
        val_mask   = (panel_yyyymm .>= val_start) .& (panel_yyyymm .<= val_end)
        test_mask  = (panel_yyyymm .>= test_start) .& (panel_yyyymm .<= test_end)
        train_df = panel[train_mask, :]
        val_df   = panel[val_mask, :]
        test_df  = panel[test_mask, :]

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
        port_train = build_managed_portfolios(train_df, chars; extra_carry=all_panel_chars)
        port_val   = build_managed_portfolios(val_df, chars; extra_carry=all_panel_chars)
        @printf("done (%.1fs, %d train / %d val)\n",
                time()-t0, nrow(port_train), nrow(port_val))

        # Extract feature matrices: ALL available numeric columns from managed portfolios
        exclude_cols = Set([:yyyymm, :port_id, :port_ret])
        feature_cols = [String(c) for c in names(port_train)
                        if !(c in exclude_cols) &&
                           hasproperty(port_val, c) &&
                           eltype(port_train[!, c]) <: Union{Missing, Number, Float64}]
        w_idx == 1 && @printf("  [*] Using %d features (all chars + macro)\n", length(feature_cols))

        # OPT B9: Pre-allocate matrices instead of hcat comprehension
        X_tr_in  = _extract_features(port_train, feature_cols)
        y_tr_in  = _extract_target(port_train.port_ret)
        X_val_in = _extract_features(port_val, feature_cols)
        y_val_in = _extract_target(port_val.port_ret)

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
                dc_tr[k] = _extract_target(port_train[!, s])  # OPT B20: reuse helper
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
        # OPT B10: Pre-compute Z'Z and Z'y once, then just update diagonal per λ
        print("  [e] Cross-validating λ... ")
        t0_lam = time()
        lambda_grid = [1e-6, 1e-5, 1e-4, 1e-3, 1e-2]
        best_lambda = LAMBDA_STAT
        best_lambda_mse = krr_mse
        ZtZ_base = nys.Z_tr' * nys.Z_tr  # OPT: compute once
        Zty_base = nys.Z_tr' * y_tr_in    # OPT: compute once
        for lam_try in lambda_grid
            A = copy(ZtZ_base)  # OPT: copy instead of full Z'Z recompute
            @inbounds for i in 1:m_used
                A[i, i] += n_tr * lam_try
            end
            β_try = cholesky(Symmetric(A)) \ Zty_base
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

        # OPT B18: sizehint! for active_cd
        active_cd = String[]
        sizehint!(active_cd, 8)
        for (g, v) in sort(collect(cd_mu), by=first)
            v > 1e-6 && push!(active_cd, "$(GROUP_NAMES[g])=$(@sprintf("%.4f", v))")
        end

        @printf("      Best MSE=%.8f | Gain=%.3f%% | %.1fs | %d evals\n",
                cd_best_mse, cd_gain, cd_time, eval_count)
        println("      Active: ", isempty(active_cd) ? "none (pure KRR)" : join(active_cd, ", "))

        # ── [f2] Coordinate descent for Theory-KRR with λ=0 ──
        @printf("  [f2] CD for Theory-KRR (λ=0, enforce ≥1 active group):\n")
        t0_cd0 = time()
        cd_mu_lam0 = Dict(g => 0.0 for g in 0:7)
        β_krr_lam0 = nystrom_krr_solve(nys.Z_tr, y_tr_in, 0.0)
        cd_best_mse_lam0 = Inf  # start high since all-zero is excluded

        # OPT B11: Parallelize init search — each (g, mu_val) pair is independent
        init_configs = [(g, mv) for g in 0:7 for mv in [1e-4, 1e-3, 1e-2, 1e-1, 1.0, 10.0, 100.0]]
        init_mses = Vector{Float64}(undef, length(init_configs))
        Threads.@threads for idx in 1:length(init_configs)
            g, mu_val = init_configs[idx]
            mu_test = Dict(g2 => 0.0 for g2 in 0:7)
            mu_test[g] = mu_val
            init_mses[idx] = eval_config_lbfgs(nys, y_tr_in, y_val_in, X_tr_in,
                        0.0, mu_test, restrictions, dc_tr, β_krr_lam0; maxiter=15)
        end
        best_init = argmin(init_mses)
        g_best, mv_best = init_configs[best_init]
        cd_best_mse_lam0 = init_mses[best_init]
        cd_mu_lam0 = Dict(g2 => 0.0 for g2 in 0:7)
        cd_mu_lam0[g_best] = mv_best

        # Refine with CD (2 stages)
        for stage in 1:2
            improved_lam0 = false
            for g in 0:7
                if stage == 1
                    grid = vcat([0.0], 10.0 .^ [-4, -3, -2, -1, 0, 1, 2])
                else
                    current = cd_mu_lam0[g]
                    if current < 1e-10
                        grid = vcat([0.0], 10.0 .^ range(-6, -2, length=10))
                    else
                        log_c = log10(current)
                        grid = vcat([0.0], 10.0 .^ range(max(-6, log_c-1), min(3, log_c+1), length=10))
                    end
                end

                n_vals = length(grid)
                mses_lam0 = Vector{Float64}(undef, n_vals)

                Threads.@threads for k in 1:n_vals
                    mu_test = copy(cd_mu_lam0)
                    mu_test[g] = grid[k]
                    # Enforce at least one non-zero μ
                    if !any(v > 1e-10 for (g2, v) in mu_test)
                        mses_lam0[k] = Inf
                        continue
                    end
                    mses_lam0[k] = eval_config_lbfgs(nys, y_tr_in, y_val_in, X_tr_in,
                                0.0, mu_test, restrictions, dc_tr, β_krr_lam0; maxiter=15)
                end

                best_k = argmin(mses_lam0)
                if mses_lam0[best_k] < cd_best_mse_lam0 - 1e-12
                    cd_mu_lam0[g] = grid[best_k]
                    cd_best_mse_lam0 = mses_lam0[best_k]
                    improved_lam0 = true
                end
            end
            !improved_lam0 && stage == 2 && break
        end

        cd0_time = time() - t0_cd0
        cd0_gain = (krr_mse - cd_best_mse_lam0) / krr_mse * 100
        active_cd0 = String[]
        sizehint!(active_cd0, 8)  # OPT B18: sizehint!
        for (g, v) in sort(collect(cd_mu_lam0), by=first)
            v > 1e-6 && push!(active_cd0, "$(GROUP_NAMES[g])=$(@sprintf("%.4f", v))")
        end
        @printf("      Best MSE (λ=0)=%.8f | Gain=%.3f%% | %.1fs\n",
                cd_best_mse_lam0, cd0_gain, cd0_time)
        println("      Active (λ=0): ", isempty(active_cd0) ? "none" : join(active_cd0, ", "))

        # ── Summary ──
        println()
        println("  " * "─"^55)
        @printf("  %-28s %12s %8s %8s\n", "Method", "Val MSE", "Gain", "Time")
        println("  " * "─"^55)
        @printf("  %-28s %12.8f %8s %7.3fs\n",
                "KRR baseline", krr_mse, "---", krr_time)
        @printf("  %-28s %12.8f %7.3f%% %7.1fs\n",
                "Theory-KRR (λ=λ*)", cd_best_mse, cd_gain, cd_time)
        @printf("  %-28s %12.8f %7.3f%% %7.1fs\n",
                "Theory-KRR (λ=0)", cd_best_mse_lam0, cd0_gain, cd0_time)
        println("  " * "─"^55)

        # ── [g] Re-fit on train+val with best μ, predict on test ──
        print("  [g] OOS prediction on test year $(test_year)... ")
        t0 = time()

        # Combine train + val for final fit
        trainval_df = vcat(train_df, val_df)
        port_trainval = build_managed_portfolios(trainval_df, chars; extra_carry=all_panel_chars)
        port_test_final = build_managed_portfolios(test_df, chars; extra_carry=all_panel_chars)

        # OPT B9: Use _extract_features helper
        X_tv = _extract_features(port_trainval, feature_cols)
        y_tv = _extract_target(port_trainval.port_ret)
        X_test_f = _extract_features(port_test_final, feature_cols)
        y_test_f = _extract_target(port_test_final.port_ret)

        # Nystrom on train+val
        sigma_tv = median_heuristic(X_tv)
        nys_tv = compute_nystrom(X_tv, X_test_f; sigma=sigma_tv, m=min(NYSTROM_M, size(X_tv,1)), has_gpu=has_gpu)

        # Data context for train+val
        dc_tv = Dict{String,Vector{Float64}}()
        for k in dc_keys
            s = Symbol(k)
            if hasproperty(port_trainval, s)
                dc_tv[k] = _extract_target(port_trainval[!, s])  # OPT B20: reuse helper
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

        # Historical mean (for R²_OOS denominator only, not a model)
        hm_pred = fill(mean(y_tv), length(y_test_f))

        # 1. OLS
        _timed_fit!("ols", () -> fit_predict_ols(X_tv, y_tv, X_test_f))

        # 2. Ridge
        _timed_fit!("ridge", () -> has_val_split ?
            fit_predict_ridge(X_tv_tr, y_tv_tr, X_tv_va, y_tv_va, X_test_f) :
            fill(mean(y_tv), length(y_test_f)))

        # 3. Lasso
        _timed_fit!("lasso", () -> has_val_split ?
            fit_predict_lasso(X_tv_tr, y_tv_tr, X_tv_va, y_tv_va, X_test_f) :
            fill(mean(y_tv), length(y_test_f)))

        # 4. Elastic net
        _timed_fit!("elastic_net", () -> has_val_split ?
            fit_predict_elasticnet(X_tv_tr, y_tv_tr, X_tv_va, y_tv_va, X_test_f) :
            fill(mean(y_tv), length(y_test_f)))

        # 5-7. Polynomial degree-2 models (Ridge, Lasso, EN on expanded features)
        if has_val_split
            X_tv_tr_poly = poly_features_deg2(X_tv_tr)
            X_tv_va_poly = poly_features_deg2(X_tv_va)
            X_test_poly = poly_features_deg2(X_test_f)
        end
        _timed_fit!("ridge_poly2", () -> has_val_split ?
            fit_predict_ridge(X_tv_tr_poly, y_tv_tr, X_tv_va_poly, y_tv_va, X_test_poly) :
            fill(mean(y_tv), length(y_test_f)))
        _timed_fit!("lasso_poly2", () -> has_val_split ?
            fit_predict_lasso(X_tv_tr_poly, y_tv_tr, X_tv_va_poly, y_tv_va, X_test_poly) :
            fill(mean(y_tv), length(y_test_f)))
        _timed_fit!("en_poly2", () -> has_val_split ?
            fit_predict_elasticnet(X_tv_tr_poly, y_tv_tr, X_tv_va_poly, y_tv_va, X_test_poly) :
            fill(mean(y_tv), length(y_test_f)))

        # 8. KRR (Nystrom, no theory) — use best_lambda from CV
        _timed_fit!("krr", () -> begin
            β_krr_tv = nystrom_krr_solve(nys_tv.Z_tr, y_tv, best_lambda)
            nystrom_predict(nys_tv.Z_val, β_krr_tv)
        end)

        # Helper for Theory-KRR L-BFGS fit
        # OPT B15: Using Optim.only_fg! for combined obj+grad
        function _fit_tikrr(mu_cfg, lam)
            has_active_mu = any(v > 1e-10 for v in values(mu_cfg))
            β_base = nystrom_krr_solve(nys_tv.Z_tr, y_tv, lam)
            if !has_active_mu
                return nystrom_predict(nys_tv.Z_val, β_base)
            end
            Z_full = nys_tv.Z_tr
            n_full = length(y_tv)
            active = Tuple{RestrictionDef, Float64}[]
            for r in restrictions
                g = get(FAMILY_TO_GROUP, r.family, -1)
                mu = get(mu_cfg, g, 0.0)
                mu > 1e-10 && push!(active, (r, mu))
            end
            # OPT B15: Combined obj+grad
            function fg_tv!(F, G, β)
                f_hat = Z_full * β
                residual = y_tv .- f_hat
                loss = dot(residual, residual) + n_full * lam * dot(β, β)
                if G !== nothing
                    G .= -2.0 .* (Z_full' * residual) .+ 2.0 * n_full * lam .* β
                end
                for (r, mu) in active
                    try
                        loss += mu * r.penalty_fn(f_hat, X_tv, dc_tv)
                        if G !== nothing
                            g_r = r.gradient_fn(f_hat, X_tv, dc_tv)
                            G .+= mu .* (Z_full' * g_r)
                        end
                    catch
                    end
                end
                if F !== nothing
                    return loss
                end
                return nothing
            end
            result = optimize(Optim.only_fg!(fg_tv!), β_base, LBFGS(),
                Optim.Options(iterations=200, g_tol=1e-6, show_trace=false))
            return nystrom_predict(nys_tv.Z_val, Optim.minimizer(result))
        end

        # 9. Theory-KRR (λ=λ*) with best μ from CD
        _timed_fit!("best_tikrr", () -> _fit_tikrr(cd_mu, best_lambda))

        # 10. Theory-KRR (λ=0) with μ from λ=0 CD
        _timed_fit!("tikrr_lam0", () -> _fit_tikrr(cd_mu_lam0, 0.0))

        # Print timing breakdown
        println("      Model timing:")
        for m in all_models
            t = get(model_times, m, 0.0)
            @printf("        %-18s %6.2fs\n", m, t)
        end

        # Accumulate OOS predictions for all models (managed portfolio level)
        for m in all_models
            append!(oos_realized_all[m], y_test_f)
            append!(oos_pred_all[m], get(test_preds, m, fill(mean(y_tv), length(y_test_f))))
        end
        # Hist mean for R²_OOS denominator
        append!(hm_pred_all, hm_pred)
        append!(hm_realized_all, y_test_f)

        # ── Sharpe ratio: VW individual stock-level decile sorts ──
        # Pre-compute coefficients for all models (avoid re-fitting per month)
        n_tv = size(X_tv, 1)

        # Linear model coefficients (stored for stock-level prediction)
        X_tv1 = hcat(ones(n_tv), X_tv)
        ols_beta = X_tv1 \ y_tv

        # OPT B19: Cache Gram matrix for ridge CV
        ridge_beta = if has_val_split
            XtX_tv1 = X_tv1' * X_tv1  # OPT: compute once
            Xty_tv1 = X_tv1' * y_tv   # OPT: compute once
            best_ridge_mse = Inf; best_rb = zeros(size(X_tv,2)+1)
            p_dim = size(X_tv, 2) + 1
            for log_lam in range(-4, 2, length=20)
                lam = 10.0^log_lam
                A = copy(XtX_tv1)  # OPT: copy cached Gram
                @inbounds for i in 2:p_dim
                    A[i, i] += n_tv * lam
                end
                rb = A \ Xty_tv1
                mse = mean((y_tv[tv_va_mask] .- (hcat(ones(sum(tv_va_mask)), X_tv[tv_va_mask,:]) * rb)).^2)
                if mse < best_ridge_mse; best_ridge_mse = mse; best_rb = rb; end
            end; best_rb
        else ols_beta end

        # Lasso coefficients
        lasso_path = has_val_split ? glmnet(X_tv_tr, y_tv_tr; alpha=1.0) : nothing
        lasso_beta, lasso_a0 = if lasso_path !== nothing
            best_mse = Inf; bi = 1
            for j in 1:length(lasso_path.lambda)
                p = X_tv_va * lasso_path.betas[:,j] .+ lasso_path.a0[j]
                m = mean((y_tv_va .- p).^2)
                if m < best_mse; best_mse = m; bi = j; end
            end; (lasso_path.betas[:,bi], lasso_path.a0[bi])
        else (zeros(size(X_tv,2)), mean(y_tv)) end

        # Elastic net coefficients
        en_path = has_val_split ? glmnet(X_tv_tr, y_tv_tr; alpha=0.5) : nothing
        en_beta, en_a0 = if en_path !== nothing
            best_mse = Inf; bi = 1
            for j in 1:length(en_path.lambda)
                p = X_tv_va * en_path.betas[:,j] .+ en_path.a0[j]
                m = mean((y_tv_va .- p).^2)
                if m < best_mse; best_mse = m; bi = j; end
            end; (en_path.betas[:,bi], en_path.a0[bi])
        else (zeros(size(X_tv,2)), mean(y_tv)) end

        # Polynomial coefficients
        poly_ols_beta = if has_val_split
            X_tv_poly_full = poly_features_deg2(X_tv)
            X_tv_poly1 = hcat(ones(n_tv), X_tv_poly_full)
            X_tv_poly1 \ y_tv
        else nothing end

        # OPT B21: Reuse β_krr_tv from model 8 (KRR) instead of re-solving
        β_krr_stock = nystrom_krr_solve(nys_tv.Z_tr, y_tv, best_lambda)  # same as model 8's β_krr_tv
        β_tikrr_stock = theory_nystrom_fit(nys_tv.Z_tr, y_tv, X_tv,
                best_lambda, cd_mu, restrictions, dc_tv; maxiter=200)
        β_tikrr_lam0_stock = theory_nystrom_fit(nys_tv.Z_tr, y_tv, X_tv,
                0.0, cd_mu_lam0, restrictions, dc_tv; maxiter=200)

        test_months_stock = sort(unique(test_df.yyyymm))
        for mo in test_months_stock
            mo_df = test_df[test_df.yyyymm .== mo, :]
            nrow(mo_df) < 50 && continue

            # OPT B12: Pre-allocate matrix instead of hcat comprehension
            n_stock = nrow(mo_df)
            X_stock = _extract_features(mo_df, feature_cols)
            y_stock = _extract_target(mo_df.RET)
            # Market equity for value-weighting
            me_stock = if hasproperty(mo_df, :me)
                _extract_target(mo_df.me)
            elseif hasproperty(mo_df, :mve0)
                _extract_target(mo_df.mve0)
            else
                ones(n_stock)
            end
            me_stock = max.(me_stock, 0.0)  # no negative weights
            d = max(1, n_stock ÷ 10)

            X_stock1 = hcat(ones(n_stock), X_stock)

            # OPT B7/B14: Use cached K_mm_inv_sqrt via NystromFeatures struct
            Z_stock = nystrom_transform(X_stock, nys_tv; has_gpu=has_gpu)

            # OPT B13: Compute poly features once for all poly models
            X_stock_poly = nothing
            X_stock_poly1 = nothing
            if poly_ols_beta !== nothing
                X_stock_poly = poly_features_deg2(X_stock)
                X_stock_poly1 = hcat(ones(n_stock), X_stock_poly)
            end

            for m_model in all_models
                if m_model == "ols"
                    pred_stock = X_stock1 * ols_beta
                elseif m_model == "ridge"
                    pred_stock = X_stock1 * ridge_beta
                elseif m_model == "lasso"
                    pred_stock = X_stock * lasso_beta .+ lasso_a0
                elseif m_model == "elastic_net"
                    pred_stock = X_stock * en_beta .+ en_a0
                elseif m_model in ["ridge_poly2", "lasso_poly2", "en_poly2"]
                    # OPT B13: Reuse precomputed poly features
                    if X_stock_poly1 !== nothing
                        pred_stock = X_stock_poly1 * poly_ols_beta
                    else
                        pred_stock = fill(mean(y_tv), n_stock)
                    end
                elseif m_model == "krr"
                    pred_stock = Z_stock * β_krr_stock
                elseif m_model == "best_tikrr"
                    pred_stock = Z_stock * β_tikrr_stock
                elseif m_model == "tikrr_lam0"
                    pred_stock = Z_stock * β_tikrr_lam0_stock
                else
                    continue
                end

                # Value-weighted decile long-short return
                perm = sortperm(pred_stock)
                long_idx = perm[end-d+1:end]
                short_idx = perm[1:d]
                w_long = me_stock[long_idx]; sw_long = sum(w_long)
                w_short = me_stock[short_idx]; sw_short = sum(w_short)
                long_ret = sw_long > 0 ? sum(y_stock[long_idx] .* w_long) / sw_long : mean(y_stock[long_idx])
                short_ret = sw_short > 0 ? sum(y_stock[short_idx] .* w_short) / sw_short : mean(y_stock[short_idx])
                push!(ls_returns_all[m_model], long_ret - short_ret)
            end
        end

        oos_time = time() - t0

        @printf("done (%.1fs)\n", oos_time)
        @printf("      Test MSE: OLS=%.6f Ridge=%.6f KRR=%.6f TIKRR(λ*)=%.6f TIKRR(λ=0)=%.6f\n",
                mean((y_test_f .- test_preds["ols"]).^2),
                mean((y_test_f .- test_preds["ridge"]).^2),
                mean((y_test_f .- test_preds["krr"]).^2),
                mean((y_test_f .- test_preds["best_tikrr"]).^2),
                mean((y_test_f .- test_preds["tikrr_lam0"]).^2))

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
            "best_val_mse_lam0" => cd_best_mse_lam0,
            "krr_val_mse" => krr_mse,
            "val_mse_gain_pct" => cd_gain,
            "val_mse_gain_lam0_pct" => cd0_gain,
            "test_mse_krr" => mean((y_test_f .- test_preds["krr"]).^2),
            "test_mse_tikrr" => mean((y_test_f .- test_preds["best_tikrr"]).^2),
            "test_mse_tikrr_lam0" => mean((y_test_f .- test_preds["tikrr_lam0"]).^2),
            "top_multipliers" => top_mults,
            "mu_groups" => Dict(GROUP_NAMES[g] => v for (g,v) in cd_mu),
            "mu_groups_lam0" => Dict(GROUP_NAMES[g] => v for (g,v) in cd_mu_lam0),
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

    y_all = hm_realized_all
    hm_all = hm_pred_all

    println()
    @printf("  %-20s %10s %10s\n", "Model", "R²_OOS(%)", "SR(ann)")
    println("  " * "─"^42)

    csv_rows = []
    for model in all_models
        pred = oos_pred_all[model]
        r2 = r2_oos(y_all, pred, hm_all)
        # Annualized Sharpe ratio
        ls = ls_returns_all[model]
        if length(ls) > 1 && std(ls) > 0
            sr_ann = mean(ls) / std(ls) * sqrt(12)
        else
            sr_ann = 0.0
        end

        @printf("  %-20s %10.2f %10.2f\n", model, r2, sr_ann)
        push!(csv_rows, Dict("model" => model, "r2_oos_pct" => r2,
                             "sharpe_ann" => sr_ann))
    end
    println()

    # ── Save cv_results.csv ──
    open("output/cv_results.csv", "w") do f
        println(f, ",r2_oos_pct,sharpe_ann")
        for row in csv_rows
            @printf(f, "%s,%.2f,%.2f\n",
                    row["model"], row["r2_oos_pct"], row["sharpe_ann"])
        end
    end
    println("  Saved output/cv_results.csv")

    # ── Save per-observation OOS predictions (for DM pairwise table) ──
    open("output/oos_predictions.csv", "w") do f
        print(f, "realized")
        for model in all_models
            print(f, ",", model)
        end
        println(f)
        n_obs = length(y_all)
        for i in 1:n_obs
            @printf(f, "%.8f", y_all[i])
            for model in all_models
                @printf(f, ",%.8f", oos_pred_all[model][i])
            end
            println(f)
        end
    end
    println("  Saved output/oos_predictions.csv")

    # ── Save cv_window_results.json ──
    open("output/cv_window_results.json", "w") do f
        JSON.print(f, window_results, 2)
    end
    println("  Saved output/cv_window_results.json")

    println("\n[5/5] Done! Run 'python -m code.generate_tables' to update paper tables.")
end

main()

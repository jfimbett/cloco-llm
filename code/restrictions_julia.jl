"""
Structural restriction penalties — Julia port.
Exact 1:1 translation of the Python restriction classes.

Each restriction computes a penalty C_j(f_hat) and its gradient ∂C_j/∂f_hat.
Penalties are organized by family (consumption, production, intermediary, etc.)
and accessed via a data_context Dict{String, Vector{Float64}} aligned with f_hat.
"""

using Statistics
using LinearAlgebra

# ════════════════════════════════════════════════════════════════════
#  Helper functions
# ════════════════════════════════════════════════════════════════════

function safe_corr(x::Vector{Float64}, y::Vector{Float64})
    n = length(x)
    n < 3 && return 0.0
    sx = std(x; corrected=false)
    sy = std(y; corrected=false)
    (sx == 0 || sy == 0) && return 0.0
    mx = mean(x)
    my = mean(y)
    return sum((x .- mx) .* (y .- my)) / (n * sx * sy)
end

function corr_gradient(f_hat::Vector{Float64}, x::Vector{Float64})
    """∂corr(f_hat, x)/∂f_hat"""
    n = length(f_hat)
    sf = std(f_hat; corrected=false)
    sx = std(x; corrected=false)
    (sf == 0 || sx == 0) && return zeros(n)
    return (x .- mean(x)) ./ (n * sf * sx)
end

function get_ctx(dc::Dict{String,Vector{Float64}}, key::String, default::Vector{Float64})
    return get(dc, key, default)
end

# ════════════════════════════════════════════════════════════════════
#  Monthly aggregation helpers (Fix: time-series penalty dilution)
#
#  In managed portfolios, macro variables are constant within each month
#  across ~36 portfolios. Computing corr(f_hat, macro_var) across all
#  n ≈ 7000 portfolio-months dilutes the signal by ~35x. These helpers
#  aggregate f_hat to monthly means before computing time-series penalties.
# ════════════════════════════════════════════════════════════════════

struct MonthlyAgg
    f_bar::Vector{Float64}     # monthly mean of f_hat (T,)
    obs_to_tidx::Vector{Int}   # maps each obs to its month index (n,)
    counts::Vector{Int}        # number of obs per month (T,)
    T::Int                     # number of unique months
end

function _monthly_agg(f_hat::Vector{Float64}, dc::Dict{String,Vector{Float64}})
    yyyymm = get(dc, "yyyymm", Float64[])
    isempty(yyyymm) && return nothing

    months = sort(unique(Int.(yyyymm)))
    T = length(months)
    month_to_tidx = Dict(m => i for (i, m) in enumerate(months))

    f_bar = zeros(T)
    counts = zeros(Int, T)
    obs_to_tidx = Vector{Int}(undef, length(f_hat))

    for i in eachindex(f_hat)
        t = month_to_tidx[Int(yyyymm[i])]
        obs_to_tidx[i] = t
        f_bar[t] += f_hat[i]
        counts[t] += 1
    end
    f_bar ./= max.(counts, 1)

    return MonthlyAgg(f_bar, obs_to_tidx, counts, T)
end

"""Get monthly-level values of a variable (take mean within each month)."""
function _monthly_var(x::Vector{Float64}, dc::Dict{String,Vector{Float64}})
    yyyymm = get(dc, "yyyymm", Float64[])
    isempty(yyyymm) && return x

    months = sort(unique(Int.(yyyymm)))
    T = length(months)
    month_to_tidx = Dict(m => i for (i, m) in enumerate(months))

    x_bar = zeros(T)
    counts = zeros(Int, T)
    for i in eachindex(x)
        t = month_to_tidx[Int(yyyymm[i])]
        x_bar[t] += x[i]
        counts[t] += 1
    end
    x_bar ./= max.(counts, 1)
    return x_bar
end

"""Propagate gradient from monthly to observation level: ∂L/∂f_i = (1/n_t) * ∂L/∂f̄_t"""
function _monthly_grad_to_obs(grad_monthly::Vector{Float64}, agg::MonthlyAgg)
    n = length(agg.obs_to_tidx)
    grad = Vector{Float64}(undef, n)
    for i in 1:n
        t = agg.obs_to_tidx[i]
        grad[i] = grad_monthly[t] / agg.counts[t]
    end
    return grad
end

"""Time-series aware correlation penalty (monthly aggregation)."""
function _ts_corr_penalty(f_hat, x, penalize_positive::Bool, dc::Dict{String,Vector{Float64}})
    agg = _monthly_agg(f_hat, dc)
    if agg === nothing
        return _corr_penalty(f_hat, x, penalize_positive)
    end
    x_bar = _monthly_var(x, dc)
    c = safe_corr(agg.f_bar, x_bar)
    if penalize_positive
        return max(0.0, c)^2
    else
        return max(0.0, -c)^2
    end
end

"""Time-series aware correlation gradient (monthly aggregation)."""
function _ts_corr_gradient(f_hat, x, penalize_positive::Bool, dc::Dict{String,Vector{Float64}})
    agg = _monthly_agg(f_hat, dc)
    if agg === nothing
        return _corr_gradient(f_hat, x, penalize_positive)
    end
    x_bar = _monthly_var(x, dc)
    c = safe_corr(agg.f_bar, x_bar)
    if penalize_positive
        c <= 0 && return zeros(length(f_hat))
        grad_monthly = 2.0 .* c .* corr_gradient(agg.f_bar, x_bar)
    else
        c >= 0 && return zeros(length(f_hat))
        grad_monthly = -2.0 .* c .* corr_gradient(agg.f_bar, x_bar)
    end
    return _monthly_grad_to_obs(grad_monthly, agg)
end

# ════════════════════════════════════════════════════════════════════
#  Restriction struct
# ════════════════════════════════════════════════════════════════════

struct RestrictionDef
    name::String
    family::String         # consumption, production, intermediary, etc.
    penalty_fn::Function   # (f_hat, X, dc) -> Float64
    gradient_fn::Function  # (f_hat, X, dc) -> Vector{Float64}
end

# ════════════════════════════════════════════════════════════════════
#  CONSUMPTION restrictions (13)
# ════════════════════════════════════════════════════════════════════

function _euler_capm_penalty(f_hat, X, dc; gamma=2.0, beta=0.995)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc)
        log_m = log(beta) .- gamma .* cg_m
        euler_err = mean(exp.(log_m) .* (1.0 .+ agg.f_bar)) - 1.0
        return euler_err^2
    end
    log_m = log(beta) .- gamma .* cg
    euler_err = mean(exp.(log_m) .* (1.0 .+ f_hat)) - 1.0
    return euler_err^2
end

function _euler_capm_gradient(f_hat, X, dc; gamma=2.0, beta=0.995)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc)
        log_m = log(beta) .- gamma .* cg_m
        m_vals = exp.(log_m)
        euler_err = mean(m_vals .* (1.0 .+ agg.f_bar)) - 1.0
        grad_monthly = 2.0 .* euler_err .* m_vals ./ agg.T
        return _monthly_grad_to_obs(grad_monthly, agg)
    end
    log_m = log(beta) .- gamma .* cg
    m = exp.(log_m)
    euler_err = mean(m .* (1.0 .+ f_hat)) - 1.0
    n = length(f_hat)
    return 2.0 .* euler_err .* m ./ n
end

function _euler_habit_penalty(f_hat, X, dc; gamma=2.0, s_bar=0.057)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    gamma_eff = gamma * (1.0 + 1.0 / s_bar)
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc)
        euler_err = mean(-gamma_eff .* cg_m .* agg.f_bar)
        return euler_err^2
    end
    euler_err = mean(-gamma_eff .* cg .* f_hat)
    return euler_err^2
end

function _euler_habit_gradient(f_hat, X, dc; gamma=2.0, s_bar=0.057)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    gamma_eff = gamma * (1.0 + 1.0 / s_bar)
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc)
        euler_err = mean(-gamma_eff .* cg_m .* agg.f_bar)
        grad_monthly = 2.0 .* euler_err .* (-gamma_eff .* cg_m) ./ agg.T
        return _monthly_grad_to_obs(grad_monthly, agg)
    end
    euler_err = mean(-gamma_eff .* cg .* f_hat)
    n = length(f_hat)
    return 2.0 .* euler_err .* (-gamma_eff .* cg) ./ n
end

function _euler_lrr_penalty(f_hat, X, dc; gamma=10.0)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc)
        target = gamma * var(cg_m; corrected=false)
        return (mean(agg.f_bar) - target)^2
    end
    target = gamma * var(cg; corrected=false)
    return (mean(f_hat) - target)^2
end

function _euler_lrr_gradient(f_hat, X, dc; gamma=10.0)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc)
        target = gamma * var(cg_m; corrected=false)
        grad_monthly = 2.0 .* (mean(agg.f_bar) - target) .* ones(agg.T) ./ agg.T
        return _monthly_grad_to_obs(grad_monthly, agg)
    end
    target = gamma * var(cg; corrected=false)
    n = length(f_hat)
    return 2.0 .* (mean(f_hat) - target) .* ones(n) ./ n
end

function _euler_ez_penalty(f_hat, X, dc; gamma=10.0, psi=1.5, beta=0.995)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    mktrf = get_ctx(dc, "mktrf", zeros(length(f_hat)))
    theta = (1 - gamma) / (1 - 1/psi)
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc)
        mkt_m = _monthly_var(mktrf, dc)
        log_m = theta .* log(beta) .- (theta / psi) .* cg_m .+ (theta - 1) .* mkt_m
        euler_err = mean(exp.(log_m) .* (1.0 .+ agg.f_bar)) - 1.0
        return euler_err^2
    end
    log_m = theta .* log(beta) .- (theta / psi) .* cg .+ (theta - 1) .* mktrf
    euler_err = mean(exp.(log_m) .* (1.0 .+ f_hat)) - 1.0
    return euler_err^2
end

function _euler_ez_gradient(f_hat, X, dc; gamma=10.0, psi=1.5, beta=0.995)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    mktrf = get_ctx(dc, "mktrf", zeros(length(f_hat)))
    theta = (1 - gamma) / (1 - 1/psi)
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc)
        mkt_m = _monthly_var(mktrf, dc)
        log_m = theta .* log(beta) .- (theta / psi) .* cg_m .+ (theta - 1) .* mkt_m
        m_vals = exp.(log_m)
        euler_err = mean(m_vals .* (1.0 .+ agg.f_bar)) - 1.0
        grad_monthly = 2.0 .* euler_err .* m_vals ./ agg.T
        return _monthly_grad_to_obs(grad_monthly, agg)
    end
    log_m = theta .* log(beta) .- (theta / psi) .* cg .+ (theta - 1) .* mktrf
    m = exp.(log_m)
    euler_err = mean(m .* (1.0 .+ f_hat)) - 1.0
    n = length(f_hat)
    return 2.0 .* euler_err .* m ./ n
end

function _cons_growth_mono_penalty(f_hat, X, dc)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    return _ts_corr_penalty(f_hat, cg, true, dc)
end

function _cons_growth_mono_gradient(f_hat, X, dc)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    return _ts_corr_gradient(f_hat, cg, true, dc)
end

function _cay_predict_penalty(f_hat, X, dc)
    cay = get_ctx(dc, "cay", zeros(length(f_hat)))
    return _ts_corr_penalty(f_hat, cay, false, dc)
end

function _cay_predict_gradient(f_hat, X, dc)
    cay = get_ctx(dc, "cay", zeros(length(f_hat)))
    return _ts_corr_gradient(f_hat, cay, false, dc)
end

function _precautionary_penalty(f_hat, X, dc)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc)
        cg_sq_m = (cg_m .- mean(cg_m)).^2
        std(cg_sq_m) == 0 && return 0.0
        c = safe_corr(agg.f_bar, cg_sq_m)
        return max(0.0, -c)^2
    end
    cg_sq = (cg .- mean(cg)).^2
    std(cg_sq) == 0 && return 0.0
    c = safe_corr(f_hat, cg_sq)
    return max(0.0, -c)^2
end

function _precautionary_gradient(f_hat, X, dc)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc)
        cg_sq_m = (cg_m .- mean(cg_m)).^2
        c = safe_corr(agg.f_bar, cg_sq_m)
        c >= 0 && return zeros(length(f_hat))
        grad_monthly = -2.0 .* c .* corr_gradient(agg.f_bar, cg_sq_m)
        return _monthly_grad_to_obs(grad_monthly, agg)
    end
    cg_sq = (cg .- mean(cg)).^2
    c = safe_corr(f_hat, cg_sq)
    c >= 0 && return zeros(length(f_hat))
    return -2.0 .* c .* corr_gradient(f_hat, cg_sq)
end

# ════════════════════════════════════════════════════════════════════
#  PRODUCTION restrictions (10)
# ════════════════════════════════════════════════════════════════════

# Generic: penalize corr(f, x) having wrong sign
function _corr_penalty(f_hat, x, penalize_positive::Bool)
    c = safe_corr(f_hat, x)
    if penalize_positive
        return max(0.0, c)^2
    else
        return max(0.0, -c)^2
    end
end

function _corr_gradient(f_hat, x, penalize_positive::Bool)
    c = safe_corr(f_hat, x)
    if penalize_positive
        c <= 0 && return zeros(length(f_hat))
        return 2.0 .* c .* corr_gradient(f_hat, x)
    else
        c >= 0 && return zeros(length(f_hat))
        return -2.0 .* c .* corr_gradient(f_hat, x)
    end
end

# invest_mono: higher I/K → lower returns (penalize positive corr)
_invest_mono_p(f, X, dc)  = _corr_penalty(f, get_ctx(dc,"ik",zeros(length(f))), true)
_invest_mono_g(f, X, dc)  = _corr_gradient(f, get_ctx(dc,"ik",zeros(length(f))), true)

# profit_mono: higher ROE → higher returns (penalize negative corr)
_profit_mono_p(f, X, dc)  = _corr_penalty(f, get_ctx(dc,"roe",zeros(length(f))), false)
_profit_mono_g(f, X, dc)  = _corr_gradient(f, get_ctx(dc,"roe",zeros(length(f))), false)

# leverage: higher lev → higher returns (penalize negative corr)
_leverage_p(f, X, dc)     = _corr_penalty(f, get_ctx(dc,"leverage",zeros(length(f))), false)
_leverage_g(f, X, dc)     = _corr_gradient(f, get_ctx(dc,"leverage",zeros(length(f))), false)

# ROA mono: higher ROA → higher returns
_roa_mono_p(f, X, dc)     = _corr_penalty(f, get_ctx(dc,"roa",zeros(length(f))), false)
_roa_mono_g(f, X, dc)     = _corr_gradient(f, get_ctx(dc,"roa",zeros(length(f))), false)

# GP mono: higher GP → higher returns
_gp_mono_p(f, X, dc)      = _corr_penalty(f, get_ctx(dc,"gp",zeros(length(f))), false)
_gp_mono_g(f, X, dc)      = _corr_gradient(f, get_ctx(dc,"gp",zeros(length(f))), false)

# Asset growth: higher AG → lower returns (penalize positive corr)
_ag_effect_p(f, X, dc)    = _corr_penalty(f, get_ctx(dc,"ag",zeros(length(f))), true)
_ag_effect_g(f, X, dc)    = _corr_gradient(f, get_ctx(dc,"ag",zeros(length(f))), true)

# R&D: higher R&D → higher returns
_rd_effect_p(f, X, dc)    = _corr_penalty(f, get_ctx(dc,"rd_intensity",zeros(length(f))), false)
_rd_effect_g(f, X, dc)    = _corr_gradient(f, get_ctx(dc,"rd_intensity",zeros(length(f))), false)

# Capex growth: higher capex growth → lower returns
_capex_p(f, X, dc)        = _corr_penalty(f, get_ctx(dc,"grcapx",zeros(length(f))), true)
_capex_g(f, X, dc)        = _corr_gradient(f, get_ctx(dc,"grcapx",zeros(length(f))), true)

# BM value: higher BM → higher returns
_bm_value_p(f, X, dc)     = _corr_penalty(f, get_ctx(dc,"bm",zeros(length(f))), false)
_bm_value_g(f, X, dc)     = _corr_gradient(f, get_ctx(dc,"bm",zeros(length(f))), false)

# Q-theory pricing: regress f on I/K(-) and ROE(+), penalize wrong signs
function _q_theory_penalty(f_hat, X, dc)
    ik = get_ctx(dc, "ik", zeros(length(f_hat)))
    roe = get_ctx(dc, "roe", zeros(length(f_hat)))
    mask = isfinite.(ik) .& isfinite.(roe) .& isfinite.(f_hat)
    sum(mask) < 20 && return 0.0
    Xq = hcat(ik[mask], roe[mask], ones(sum(mask)))
    beta = Xq \ f_hat[mask]
    return max(0.0, beta[1])^2 + max(0.0, -beta[2])^2
end

function _q_theory_gradient(f_hat, X, dc)
    ik = get_ctx(dc, "ik", zeros(length(f_hat)))
    roe = get_ctx(dc, "roe", zeros(length(f_hat)))
    n = length(f_hat)
    mask = isfinite.(ik) .& isfinite.(roe) .& isfinite.(f_hat)
    sum(mask) < 20 && return zeros(n)
    Xq = hcat(ik[mask], roe[mask], ones(sum(mask)))
    beta = Xq \ f_hat[mask]
    XtX_inv = inv(Xq' * Xq)
    dbeta_df = XtX_inv * Xq'
    grad = zeros(n)
    midx = findall(mask)
    if beta[1] > 0
        grad[midx] .+= 2.0 .* beta[1] .* dbeta_df[1, :]
    end
    if beta[2] < 0
        grad[midx] .+= 2.0 .* beta[2] .* dbeta_df[2, :]
    end
    return grad
end

# ════════════════════════════════════════════════════════════════════
#  INTERMEDIARY restrictions (8)
# ════════════════════════════════════════════════════════════════════

_hkm_capital_p(f, X, dc)  = _ts_corr_penalty(f, get_ctx(dc,"hkm_capital_ratio",zeros(length(f))), true, dc)
_hkm_capital_g(f, X, dc)  = _ts_corr_gradient(f, get_ctx(dc,"hkm_capital_ratio",zeros(length(f))), true, dc)

_hkm_factor_p(f, X, dc)   = _ts_corr_penalty(f, get_ctx(dc,"hkm_risk_factor",zeros(length(f))), false, dc)
_hkm_factor_g(f, X, dc)   = _ts_corr_gradient(f, get_ctx(dc,"hkm_risk_factor",zeros(length(f))), false, dc)

function _intermediary_euler_penalty(f_hat, X, dc; gamma=2.0)
    hkm = get_ctx(dc, "hkm_capital_ratio", zeros(length(f_hat)))
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        hkm_m = _monthly_var(hkm, dc)
        any(hkm_m .<= 0) && return 0.0
        log_m = -gamma .* log.(max.(hkm_m, 1e-10))
        euler_err = mean(exp.(log_m) .* (1.0 .+ agg.f_bar)) - 1.0
        return euler_err^2
    end
    any(hkm .<= 0) && return 0.0
    log_m = -gamma .* log.(max.(hkm, 1e-10))
    euler_err = mean(exp.(log_m) .* (1.0 .+ f_hat)) - 1.0
    return euler_err^2
end

function _intermediary_euler_gradient(f_hat, X, dc; gamma=2.0)
    hkm = get_ctx(dc, "hkm_capital_ratio", zeros(length(f_hat)))
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        hkm_m = _monthly_var(hkm, dc)
        log_m = -gamma .* log.(max.(hkm_m, 1e-10))
        m_vals = exp.(log_m)
        euler_err = mean(m_vals .* (1.0 .+ agg.f_bar)) - 1.0
        grad_monthly = 2.0 .* euler_err .* m_vals ./ agg.T
        return _monthly_grad_to_obs(grad_monthly, agg)
    end
    log_m = -gamma .* log.(max.(hkm, 1e-10))
    m = exp.(log_m)
    euler_err = mean(m .* (1.0 .+ f_hat)) - 1.0
    n = length(f_hat)
    return 2.0 .* euler_err .* m ./ n
end

_sentiment_p(f, X, dc)    = _ts_corr_penalty(f, get_ctx(dc,"sentiment",zeros(length(f))), true, dc)
_sentiment_g(f, X, dc)    = _ts_corr_gradient(f, get_ctx(dc,"sentiment",zeros(length(f))), true, dc)

_funding_liq_p(f, X, dc)  = _ts_corr_penalty(f, get_ctx(dc,"ebp",zeros(length(f))), false, dc)
_funding_liq_g(f, X, dc)  = _ts_corr_gradient(f, get_ctx(dc,"ebp",zeros(length(f))), false, dc)

# ════════════════════════════════════════════════════════════════════
#  INFORMATION restrictions (6)
# ════════════════════════════════════════════════════════════════════

_forecast_disp_p(f, X, dc) = _corr_penalty(f, get_ctx(dc,"ForecastDispersion",zeros(length(f))), false)
_forecast_disp_g(f, X, dc) = _corr_gradient(f, get_ctx(dc,"ForecastDispersion",zeros(length(f))), false)

_macro_uncert_p(f, X, dc)  = _ts_corr_penalty(f, get_ctx(dc,"vix",zeros(length(f))), false, dc)
_macro_uncert_g(f, X, dc)  = _ts_corr_gradient(f, get_ctx(dc,"vix",zeros(length(f))), false, dc)

# ════════════════════════════════════════════════════════════════════
#  DEMAND restrictions (6) — simplified to correlation-based
# ════════════════════════════════════════════════════════════════════

_demand_elast_p(f, X, dc) = begin
    me = get_ctx(dc, "me", zeros(length(f)))
    bm = get_ctx(dc, "bm", zeros(length(f)))
    any(me .<= 0) && return 0.0
    any(bm .<= 0) && return 0.0
    ratio = log.(max.(me, 1e-10)) .- log.(max.(bm, 1e-10))
    _corr_penalty(f, ratio, true)
end
_demand_elast_g(f, X, dc) = begin
    me = get_ctx(dc, "me", zeros(length(f)))
    bm = get_ctx(dc, "bm", zeros(length(f)))
    any(me .<= 0) && return zeros(length(f))
    any(bm .<= 0) && return zeros(length(f))
    ratio = log.(max.(me, 1e-10)) .- log.(max.(bm, 1e-10))
    _corr_gradient(f, ratio, true)
end

_size_demand_p(f, X, dc)  = begin
    me = get_ctx(dc, "me", zeros(length(f)))
    any(me .<= 0) && return 0.0
    _corr_penalty(f, log.(max.(me, 1e-10)), true)
end
_size_demand_g(f, X, dc)  = begin
    me = get_ctx(dc, "me", zeros(length(f)))
    any(me .<= 0) && return zeros(length(f))
    _corr_gradient(f, log.(max.(me, 1e-10)), true)
end

# ════════════════════════════════════════════════════════════════════
#  VOLATILITY restrictions (2)
# ════════════════════════════════════════════════════════════════════

_vix_premium_p(f, X, dc)  = _ts_corr_penalty(f, get_ctx(dc,"vix",zeros(length(f))), false, dc)
_vix_premium_g(f, X, dc)  = _ts_corr_gradient(f, get_ctx(dc,"vix",zeros(length(f))), false, dc)

_realized_vol_p(f, X, dc) = _ts_corr_penalty(f, get_ctx(dc,"realized_var",zeros(length(f))), false, dc)
_realized_vol_g(f, X, dc) = _ts_corr_gradient(f, get_ctx(dc,"realized_var",zeros(length(f))), false, dc)

# ════════════════════════════════════════════════════════════════════
#  BEHAVIORAL restrictions (6)
# ════════════════════════════════════════════════════════════════════

_momentum_p(f, X, dc)     = _corr_penalty(f, get_ctx(dc,"Mom12m",zeros(length(f))), false)
_momentum_g(f, X, dc)     = _corr_gradient(f, get_ctx(dc,"Mom12m",zeros(length(f))), false)

_st_reversal_p(f, X, dc)  = _corr_penalty(f, get_ctx(dc,"streversal",zeros(length(f))), true)
_st_reversal_g(f, X, dc)  = _corr_gradient(f, get_ctx(dc,"streversal",zeros(length(f))), true)

_lt_reversal_p(f, X, dc)  = _corr_penalty(f, get_ctx(dc,"LRreversal",zeros(length(f))), true)
_lt_reversal_g(f, X, dc)  = _corr_gradient(f, get_ctx(dc,"LRreversal",zeros(length(f))), true)

function _disposition_penalty(f_hat, X, dc)
    mom = get_ctx(dc, "Mom12m", zeros(length(f_hat)))
    strev = get_ctx(dc, "streversal", zeros(length(f_hat)))
    cgo_proxy = mom .- strev
    return _corr_penalty(f_hat, cgo_proxy, true)
end

function _disposition_gradient(f_hat, X, dc)
    mom = get_ctx(dc, "Mom12m", zeros(length(f_hat)))
    strev = get_ctx(dc, "streversal", zeros(length(f_hat)))
    cgo_proxy = mom .- strev
    return _corr_gradient(f_hat, cgo_proxy, true)
end

# ════════════════════════════════════════════════════════════════════
#  MACRO restrictions (5)
# ════════════════════════════════════════════════════════════════════

_term_spread_p(f, X, dc)   = _ts_corr_penalty(f, get_ctx(dc,"term_spread",zeros(length(f))), false, dc)
_term_spread_g(f, X, dc)   = _ts_corr_gradient(f, get_ctx(dc,"term_spread",zeros(length(f))), false, dc)

_default_spread_p(f, X, dc)= _ts_corr_penalty(f, get_ctx(dc,"default_spread",zeros(length(f))), false, dc)
_default_spread_g(f, X, dc)= _ts_corr_gradient(f, get_ctx(dc,"default_spread",zeros(length(f))), false, dc)

_ebp_predict_p(f, X, dc)  = _ts_corr_penalty(f, get_ctx(dc,"ebp",zeros(length(f))), false, dc)
_ebp_predict_g(f, X, dc)  = _ts_corr_gradient(f, get_ctx(dc,"ebp",zeros(length(f))), false, dc)

_rf_effect_p(f, X, dc)    = _ts_corr_penalty(f, get_ctx(dc,"rf",zeros(length(f))), true, dc)
_rf_effect_g(f, X, dc)    = _ts_corr_gradient(f, get_ctx(dc,"rf",zeros(length(f))), true, dc)

function _macro_factor_penalty(f_hat, X, dc)
    ts = get_ctx(dc, "term_spread", zeros(length(f_hat)))
    ds = get_ctx(dc, "default_spread", zeros(length(f_hat)))
    cay = get_ctx(dc, "cay", zeros(length(f_hat)))
    ebp = get_ctx(dc, "ebp", zeros(length(f_hat)))
    rf = get_ctx(dc, "rf", zeros(length(f_hat)))
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        f_m = agg.f_bar
        ts_m = _monthly_var(ts, dc); ds_m = _monthly_var(ds, dc)
        cay_m = _monthly_var(cay, dc); ebp_m = _monthly_var(ebp, dc)
        rf_m = _monthly_var(rf, dc)
        T = agg.T
        T < 10 && return 0.0
        Xm = hcat(ts_m, ds_m, cay_m, ebp_m, rf_m, ones(T))
        beta = Xm \ f_m
        pred = Xm * beta
        ss_res = sum((f_m .- pred).^2)
        ss_tot = sum((f_m .- mean(f_m)).^2)
        r2 = ss_tot > 0 ? 1.0 - ss_res / ss_tot : 0.0
        return max(0.0, 0.1 - r2)^2
    end
    Xm = hcat(ts, ds, cay, ebp, rf, ones(length(f_hat)))
    n = length(f_hat)
    n < 10 && return 0.0
    beta = Xm \ f_hat
    pred = Xm * beta
    ss_res = sum((f_hat .- pred).^2)
    ss_tot = sum((f_hat .- mean(f_hat)).^2)
    r2 = ss_tot > 0 ? 1.0 - ss_res / ss_tot : 0.0
    return max(0.0, 0.1 - r2)^2
end

function _macro_factor_gradient(f_hat, X, dc)
    ts = get_ctx(dc, "term_spread", zeros(length(f_hat)))
    ds = get_ctx(dc, "default_spread", zeros(length(f_hat)))
    cay = get_ctx(dc, "cay", zeros(length(f_hat)))
    ebp = get_ctx(dc, "ebp", zeros(length(f_hat)))
    rf = get_ctx(dc, "rf", zeros(length(f_hat)))
    n = length(f_hat)
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        f_m = agg.f_bar; T = agg.T
        ts_m = _monthly_var(ts, dc); ds_m = _monthly_var(ds, dc)
        cay_m = _monthly_var(cay, dc); ebp_m = _monthly_var(ebp, dc)
        rf_m = _monthly_var(rf, dc)
        T < 10 && return zeros(n)
        Xm = hcat(ts_m, ds_m, cay_m, ebp_m, rf_m, ones(T))
        beta = Xm \ f_m
        pred = Xm * beta
        ss_res = sum((f_m .- pred).^2)
        ss_tot = sum((f_m .- mean(f_m)).^2)
        ss_tot == 0 && return zeros(n)
        r2 = 1.0 - ss_res / ss_tot
        r2 >= 0.1 && return zeros(n)
        resid = f_m .- pred
        dss_res = 2.0 .* resid
        dss_tot = 2.0 .* (f_m .- mean(f_m))
        dr2 = -(dss_res .* ss_tot .- ss_res .* dss_tot) ./ (ss_tot^2)
        grad_monthly = 2.0 .* (0.1 - r2) .* (-dr2)
        return _monthly_grad_to_obs(grad_monthly, agg)
    end
    Xm = hcat(ts, ds, cay, ebp, rf, ones(n))
    n < 10 && return zeros(n)
    beta = Xm \ f_hat
    pred = Xm * beta
    ss_res = sum((f_hat .- pred).^2)
    ss_tot = sum((f_hat .- mean(f_hat)).^2)
    ss_tot == 0 && return zeros(n)
    r2 = 1.0 - ss_res / ss_tot
    r2 >= 0.1 && return zeros(n)
    resid = f_hat .- pred
    dss_res = 2.0 .* resid
    dss_tot = 2.0 .* (f_hat .- mean(f_hat))
    dr2 = -(dss_res .* ss_tot .- ss_res .* dss_tot) ./ (ss_tot^2)
    return 2.0 .* (0.1 - r2) .* (-dr2)
end


# ════════════════════════════════════════════════════════════════════
#  MISSING CONSUMPTION restrictions (6)
# ════════════════════════════════════════════════════════════════════

function _euler_cond_capm_penalty(f_hat, X, dc; gamma_base=2.0)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    cay = get_ctx(dc, "cay", zeros(length(f_hat)))
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc); cay_m = _monthly_var(cay, dc)
        gamma_t = gamma_base .+ 5.0 .* cay_m
        euler_err = mean(-gamma_t .* cg_m .* (1.0 .+ agg.f_bar))
        return euler_err^2
    end
    gamma_t = gamma_base .+ 5.0 .* cay
    euler_err = mean(-gamma_t .* cg .* (1.0 .+ f_hat))
    return euler_err^2
end
function _euler_cond_capm_gradient(f_hat, X, dc; gamma_base=2.0)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    cay = get_ctx(dc, "cay", zeros(length(f_hat)))
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc); cay_m = _monthly_var(cay, dc)
        gamma_t = gamma_base .+ 5.0 .* cay_m
        euler_err = mean(-gamma_t .* cg_m .* (1.0 .+ agg.f_bar))
        grad_monthly = 2.0 .* euler_err .* (-gamma_t .* cg_m) ./ agg.T
        return _monthly_grad_to_obs(grad_monthly, agg)
    end
    gamma_t = gamma_base .+ 5.0 .* cay
    euler_err = mean(-gamma_t .* cg .* (1.0 .+ f_hat))
    n = length(f_hat)
    return 2.0 .* euler_err .* (-gamma_t .* cg) ./ n
end

function _euler_durable_penalty(f_hat, X, dc; gamma=2.0, alpha=0.8)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    gamma_adj = gamma / alpha
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc)
        euler_err = mean(-gamma_adj .* cg_m .* agg.f_bar)
        return euler_err^2
    end
    euler_err = mean(-gamma_adj .* cg .* f_hat)
    return euler_err^2
end
function _euler_durable_gradient(f_hat, X, dc; gamma=2.0, alpha=0.8)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    gamma_adj = gamma / alpha
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc)
        euler_err = mean(-gamma_adj .* cg_m .* agg.f_bar)
        grad_monthly = 2.0 .* euler_err .* (-gamma_adj .* cg_m) ./ agg.T
        return _monthly_grad_to_obs(grad_monthly, agg)
    end
    euler_err = mean(-gamma_adj .* cg .* f_hat)
    n = length(f_hat)
    return 2.0 .* euler_err .* (-gamma_adj .* cg) ./ n
end

function _cons_beta_pricing_penalty(f_hat, X, dc)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc)
        var_cg = var(cg_m; corrected=false)
        var_cg == 0 && return 0.0
        beta_c = (agg.f_bar .* cg_m .- mean(agg.f_bar) .* mean(cg_m)) ./ var_cg
        lam = mean(agg.f_bar .* beta_c) / (mean(beta_c.^2) + 1e-10)
        resid = agg.f_bar .- lam .* beta_c
        return mean(resid.^2)
    end
    var_cg = var(cg; corrected=false)
    var_cg == 0 && return 0.0
    beta_c = (f_hat .* cg .- mean(f_hat) .* mean(cg)) ./ var_cg
    lam = mean(f_hat .* beta_c) / (mean(beta_c.^2) + 1e-10)
    resid = f_hat .- lam .* beta_c
    return mean(resid.^2)
end
function _cons_beta_pricing_gradient(f_hat, X, dc)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    n = length(f_hat)
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc)
        var_cg = var(cg_m; corrected=false)
        var_cg == 0 && return zeros(n)
        beta_c = (agg.f_bar .* cg_m .- mean(agg.f_bar) .* mean(cg_m)) ./ var_cg
        lam = mean(agg.f_bar .* beta_c) / (mean(beta_c.^2) + 1e-10)
        resid = agg.f_bar .- lam .* beta_c
        grad_monthly = 2.0 .* resid ./ agg.T
        return _monthly_grad_to_obs(grad_monthly, agg)
    end
    var_cg = var(cg; corrected=false)
    var_cg == 0 && return zeros(n)
    beta_c = (f_hat .* cg .- mean(f_hat) .* mean(cg)) ./ var_cg
    lam = mean(f_hat .* beta_c) / (mean(beta_c.^2) + 1e-10)
    resid = f_hat .- lam .* beta_c
    return 2.0 .* resid ./ n
end

function _recursive_utility_penalty(f_hat, X, dc; gamma=10.0, psi=1.5)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    mktrf = get_ctx(dc, "mktrf", zeros(length(f_hat)))
    theta = (1 - gamma) / (1 - 1.0 / psi)
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc); mkt_m = _monthly_var(mktrf, dc)
        pricing_err = mean(agg.f_bar .+ (theta / psi) .* cg_m .- (theta - 1) .* mkt_m)
        return pricing_err^2
    end
    pricing_err = mean(f_hat .+ (theta / psi) .* cg .- (theta - 1) .* mktrf)
    return pricing_err^2
end
function _recursive_utility_gradient(f_hat, X, dc; gamma=10.0, psi=1.5)
    n = length(f_hat)
    cg = get_ctx(dc, "cons_growth", zeros(n))
    mktrf = get_ctx(dc, "mktrf", zeros(n))
    theta = (1 - gamma) / (1 - 1.0 / psi)
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc); mkt_m = _monthly_var(mktrf, dc)
        pricing_err = mean(agg.f_bar .+ (theta / psi) .* cg_m .- (theta - 1) .* mkt_m)
        grad_monthly = 2.0 .* pricing_err .* ones(agg.T) ./ agg.T
        return _monthly_grad_to_obs(grad_monthly, agg)
    end
    pricing_err = mean(f_hat .+ (theta / psi) .* cg .- (theta - 1) .* mktrf)
    return 2.0 .* pricing_err .* ones(n) ./ n
end

function _disaster_risk_penalty(f_hat, X, dc; gamma=4.0, p_disaster=0.017, b=0.4)
    disaster_premium = p_disaster * ((1 - b)^(-gamma) - 1)
    agg = _monthly_agg(f_hat, dc)
    f = agg !== nothing ? agg.f_bar : f_hat
    return (mean(f) - disaster_premium * 0.5)^2
end
function _disaster_risk_gradient(f_hat, X, dc; gamma=4.0, p_disaster=0.017, b=0.4)
    disaster_premium = p_disaster * ((1 - b)^(-gamma) - 1)
    n = length(f_hat)
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        grad_monthly = 2.0 .* (mean(agg.f_bar) - disaster_premium * 0.5) .* ones(agg.T) ./ agg.T
        return _monthly_grad_to_obs(grad_monthly, agg)
    end
    return 2.0 .* (mean(f_hat) - disaster_premium * 0.5) .* ones(n) ./ n
end

function _intertemporal_sub_penalty(f_hat, X, dc; psi=1.5)
    rf = get_ctx(dc, "rf", zeros(length(f_hat)))
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        rf_m = _monthly_var(rf, dc); cg_m = _monthly_var(cg, dc)
        resid_m = cg_m .- psi .* rf_m
        std(agg.f_bar) == 0 && return 0.0
        c = safe_corr(agg.f_bar, resid_m)
        return c^2
    end
    resid = cg .- psi .* rf
    std(f_hat) == 0 && return 0.0
    c = safe_corr(f_hat, resid)
    return c^2
end
function _intertemporal_sub_gradient(f_hat, X, dc; psi=1.5)
    rf = get_ctx(dc, "rf", zeros(length(f_hat)))
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        rf_m = _monthly_var(rf, dc); cg_m = _monthly_var(cg, dc)
        resid_m = cg_m .- psi .* rf_m
        c = safe_corr(agg.f_bar, resid_m)
        grad_monthly = 2.0 .* c .* corr_gradient(agg.f_bar, resid_m)
        return _monthly_grad_to_obs(grad_monthly, agg)
    end
    resid = cg .- psi .* rf
    c = safe_corr(f_hat, resid)
    return 2.0 .* c .* corr_gradient(f_hat, resid)
end

# ════════════════════════════════════════════════════════════════════
#  MISSING INTERMEDIARY restrictions (3)
# ════════════════════════════════════════════════════════════════════

function _sentiment_xs_penalty(f_hat, X, dc)
    sent = get_ctx(dc, "sentiment", zeros(length(f_hat)))
    me = get_ctx(dc, "me", ones(length(f_hat)))
    interaction = sent ./ max.(me, 1e-6)
    return _corr_penalty(f_hat, interaction, true)
end
_sentiment_xs_gradient(f, X, dc) = begin
    sent = get_ctx(dc, "sentiment", zeros(length(f)))
    me = get_ctx(dc, "me", ones(length(f)))
    _corr_gradient(f, sent ./ max.(me, 1e-6), true)
end

function _leverage_cycle_penalty(f_hat, X, dc)
    hkm = get_ctx(dc, "hkm_capital_ratio", ones(length(f_hat)))
    lev_proxy = 1.0 ./ max.(hkm, 0.01)
    return _ts_corr_penalty(f_hat, lev_proxy, false, dc)
end
_leverage_cycle_gradient(f, X, dc) = begin
    hkm = get_ctx(dc, "hkm_capital_ratio", ones(length(f)))
    _ts_corr_gradient(f, 1.0 ./ max.(hkm, 0.01), false, dc)
end

function _institutional_ownership_penalty(f_hat, X, dc)
    me = get_ctx(dc, "me", zeros(length(f_hat)))
    return _corr_penalty(f_hat, me, true)
end
_institutional_ownership_gradient(f, X, dc) = _corr_gradient(f, get_ctx(dc, "me", zeros(length(f))), true)

# ════════════════════════════════════════════════════════════════════
#  MISSING INFORMATION restrictions (4)
# ════════════════════════════════════════════════════════════════════

function _learning_euler_penalty(f_hat, X, dc; gamma=2.0)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    vix = get_ctx(dc, "vix", zeros(length(f_hat)))
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc); vix_m = _monthly_var(vix, dc)
        target = gamma * var(cg_m; corrected=false) + gamma^2 * var(vix_m; corrected=false) / 10000
        return (mean(agg.f_bar) - target)^2
    end
    base = gamma * var(cg; corrected=false)
    uncert = gamma^2 * var(vix; corrected=false) / 10000
    return (mean(f_hat) - base - uncert)^2
end
function _learning_euler_gradient(f_hat, X, dc; gamma=2.0)
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    vix = get_ctx(dc, "vix", zeros(length(f_hat)))
    n = length(f_hat)
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        cg_m = _monthly_var(cg, dc); vix_m = _monthly_var(vix, dc)
        target = gamma * var(cg_m; corrected=false) + gamma^2 * var(vix_m; corrected=false) / 10000
        grad_monthly = 2.0 .* (mean(agg.f_bar) - target) .* ones(agg.T) ./ agg.T
        return _monthly_grad_to_obs(grad_monthly, agg)
    end
    target = gamma * var(cg; corrected=false) + gamma^2 * var(vix; corrected=false) / 10000
    return 2.0 .* (mean(f_hat) - target) .* ones(n) ./ n
end

function _ambiguity_aversion_penalty(f_hat, X, dc)
    vix = get_ctx(dc, "vix", zeros(length(f_hat)))
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        vix_m = _monthly_var(vix, dc)
        med = median(vix_m)
        high = vix_m .> med
        sum(high) < 5 && return 0.0
        sum(.!high) < 5 && return 0.0
        var_high = var(agg.f_bar[high]; corrected=false)
        var_low = var(agg.f_bar[.!high]; corrected=false)
        return max(0.0, var_low - var_high)^2
    end
    med = median(vix)
    high = vix .> med
    sum(high) < 5 && return 0.0
    sum(.!high) < 5 && return 0.0
    var_high = var(f_hat[high]; corrected=false)
    var_low = var(f_hat[.!high]; corrected=false)
    return max(0.0, var_low - var_high)^2
end
function _ambiguity_aversion_gradient(f_hat, X, dc)
    vix = get_ctx(dc, "vix", zeros(length(f_hat)))
    n = length(f_hat)
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        vix_m = _monthly_var(vix, dc)
        med = median(vix_m)
        high = vix_m .> med
        (sum(high) < 5 || sum(.!high) < 5) && return zeros(n)
        var_high = var(agg.f_bar[high]; corrected=false)
        var_low = var(agg.f_bar[.!high]; corrected=false)
        diff = var_low - var_high
        diff <= 0 && return zeros(n)
        grad_m = zeros(agg.T)
        n_low = sum(.!high); n_high = sum(high)
        low_idx = findall(.!high); high_idx = findall(high)
        grad_m[low_idx] .= 2.0 .* diff .* 2.0 .* (agg.f_bar[low_idx] .- mean(agg.f_bar[low_idx])) ./ n_low
        grad_m[high_idx] .= 2.0 .* diff .* (-2.0) .* (agg.f_bar[high_idx] .- mean(agg.f_bar[high_idx])) ./ n_high
        return _monthly_grad_to_obs(grad_m, agg)
    end
    med = median(vix)
    high = vix .> med
    (sum(high) < 5 || sum(.!high) < 5) && return zeros(n)
    var_high = var(f_hat[high]; corrected=false)
    var_low = var(f_hat[.!high]; corrected=false)
    diff = var_low - var_high
    diff <= 0 && return zeros(n)
    grad = zeros(n)
    n_low = sum(.!high)
    n_high = sum(high)
    grad[.!high] .= 2.0 .* diff .* 2.0 .* (f_hat[.!high] .- mean(f_hat[.!high])) ./ n_low
    grad[high] .= 2.0 .* diff .* (-2.0) .* (f_hat[high] .- mean(f_hat[high])) ./ n_high
    return grad
end

function _rational_inattention_penalty(f_hat, X, dc)
    iv = get_ctx(dc, "IdioVol3F", zeros(length(f_hat)))
    med = median(iv)
    high = iv .> med
    sum(high) < 5 && return 0.0
    sum(.!high) < 5 && return 0.0
    return max(0.0, var(f_hat[.!high]; corrected=false) - var(f_hat[high]; corrected=false))^2
end
function _rational_inattention_gradient(f_hat, X, dc)
    iv = get_ctx(dc, "IdioVol3F", zeros(length(f_hat)))
    n = length(f_hat)
    med = median(iv)
    high = iv .> med
    (sum(high) < 5 || sum(.!high) < 5) && return zeros(n)
    diff = var(f_hat[.!high]; corrected=false) - var(f_hat[high]; corrected=false)
    diff <= 0 && return zeros(n)
    grad = zeros(n)
    n_low = sum(.!high); n_high = sum(high)
    grad[.!high] .= 2.0 .* diff .* 2.0 .* (f_hat[.!high] .- mean(f_hat[.!high])) ./ n_low
    grad[high] .= 2.0 .* diff .* (-2.0) .* (f_hat[high] .- mean(f_hat[high])) ./ n_high
    return grad
end

function _cons_disagreement_penalty(f_hat, X, dc)
    fd = get_ctx(dc, "ForecastDispersion", zeros(length(f_hat)))
    cg = get_ctx(dc, "cons_growth", zeros(length(f_hat)))
    interaction = fd .* abs.(cg)
    return _corr_penalty(f_hat, interaction, false)
end
_cons_disagreement_gradient(f, X, dc) = begin
    fd = get_ctx(dc, "ForecastDispersion", zeros(length(f)))
    cg = get_ctx(dc, "cons_growth", zeros(length(f)))
    _corr_gradient(f, fd .* abs.(cg), false)
end

# ════════════════════════════════════════════════════════════════════
#  MISSING DEMAND restrictions (4)
# ════════════════════════════════════════════════════════════════════

function _market_clearing_penalty(f_hat, X, dc; target=0.005)
    me = get_ctx(dc, "me", ones(length(f_hat)))
    w = me ./ sum(me)
    vw_mean = dot(w, f_hat)
    return (vw_mean - target)^2
end
function _market_clearing_gradient(f_hat, X, dc; target=0.005)
    me = get_ctx(dc, "me", ones(length(f_hat)))
    w = me ./ sum(me)
    vw_mean = dot(w, f_hat)
    return 2.0 .* (vw_mean - target) .* w
end

function _inelastic_markets_penalty(f_hat, X, dc)
    mktrf = get_ctx(dc, "mktrf", zeros(length(f_hat)))
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        mkt_m = _monthly_var(mktrf, dc)
        pred_var = var(agg.f_bar; corrected=false)
        mkt_var = var(mkt_m; corrected=false)
        mkt_var == 0 && return 0.0
        return max(0.0, 1.0 - pred_var / mkt_var)^2
    end
    pred_var = var(f_hat; corrected=false)
    mkt_var = var(mktrf; corrected=false)
    mkt_var == 0 && return 0.0
    return max(0.0, 1.0 - pred_var / mkt_var)^2
end
function _inelastic_markets_gradient(f_hat, X, dc)
    mktrf = get_ctx(dc, "mktrf", zeros(length(f_hat)))
    n = length(f_hat)
    agg = _monthly_agg(f_hat, dc)
    if agg !== nothing
        mkt_m = _monthly_var(mktrf, dc)
        pred_var = var(agg.f_bar; corrected=false)
        mkt_var = var(mkt_m; corrected=false)
        mkt_var == 0 && return zeros(n)
        ratio = pred_var / mkt_var
        ratio >= 1.0 && return zeros(n)
        T = agg.T
        grad_m = 2.0 .* (1.0 - ratio) .* (-2.0 / (T * mkt_var)) .* (agg.f_bar .- mean(agg.f_bar))
        return _monthly_grad_to_obs(grad_m, agg)
    end
    pred_var = var(f_hat; corrected=false)
    mkt_var = var(mktrf; corrected=false)
    mkt_var == 0 && return zeros(n)
    ratio = pred_var / mkt_var
    ratio >= 1.0 && return zeros(n)
    return 2.0 .* (1.0 - ratio) .* (-2.0 / (n * mkt_var)) .* (f_hat .- mean(f_hat))
end

function _asset_embedding_penalty(f_hat, X, dc)
    # Smoothness penalty: predictions should vary smoothly in characteristic space
    n = length(f_hat)
    n < 20 && return 0.0
    # Subsample for speed
    m = min(n, 200)
    idx = 1:m  # use first m for speed
    f_sub = f_hat[idx]
    X_sub = size(X, 1) >= m ? X[idx, :] : X[1:min(end,m), :]
    h = 1.0
    vf = var(f_sub; corrected=false)
    vf == 0 && return 0.0
    # Graph Laplacian smoothness
    smoothness = 0.0
    for i in 1:m, j in (i+1):m
        d2 = sum((X_sub[i,:] .- X_sub[j,:]).^2)
        w = exp(-d2 / (2 * h^2))
        smoothness += w * (f_sub[i] - f_sub[j])^2
    end
    return smoothness / (m * vf)
end
function _asset_embedding_gradient(f_hat, X, dc)
    # Numerical gradient (only on subsample, fast)
    n = length(f_hat)
    grad = zeros(n)
    pen0 = _asset_embedding_penalty(f_hat, X, dc)
    eps = 1e-6
    m = min(n, 200)
    for i in 1:m
        f_plus = copy(f_hat)
        f_plus[i] += eps
        grad[i] = (_asset_embedding_penalty(f_plus, X, dc) - pen0) / eps
    end
    return grad
end

function _substitution_pattern_penalty(f_hat, X, dc)
    me = get_ctx(dc, "me", zeros(length(f_hat)))
    bm = get_ctx(dc, "bm", zeros(length(f_hat)))
    n = length(f_hat)
    n < 50 && return 0.0
    total_var = var(f_hat; corrected=false)
    total_var == 0 && return 0.0
    # Quintile sort on me and bm
    me_rank = (sortperm(sortperm(me)) .- 1) ./ max(n - 1, 1)
    bm_rank = (sortperm(sortperm(bm)) .- 1) ./ max(n - 1, 1)
    within_var = 0.0
    count = 0
    for i_me in 0:4, i_bm in 0:4
        mask = (me_rank .>= i_me/5) .& (me_rank .< (i_me+1)/5) .&
               (bm_rank .>= i_bm/5) .& (bm_rank .< (i_bm+1)/5)
        sum(mask) > 1 || continue
        within_var += var(f_hat[mask]; corrected=false)
        count += 1
    end
    count == 0 && return 0.0
    return within_var / count / total_var
end
function _substitution_pattern_gradient(f_hat, X, dc)
    n = length(f_hat)
    grad = zeros(n)
    pen0 = _substitution_pattern_penalty(f_hat, X, dc)
    eps = 1e-6
    for i in 1:min(n, 500)  # subsample for speed
        f_plus = copy(f_hat); f_plus[i] += eps
        grad[i] = (_substitution_pattern_penalty(f_plus, X, dc) - pen0) / eps
    end
    return grad
end

# ════════════════════════════════════════════════════════════════════
#  MISSING BEHAVIORAL restrictions (2)
# ════════════════════════════════════════════════════════════════════

function _sentiment_interaction_penalty(f_hat, X, dc)
    sent = get_ctx(dc, "sentiment", zeros(length(f_hat)))
    mom = get_ctx(dc, "Mom12m", zeros(length(f_hat)))
    med = median(sent)
    high = sent .> med
    (sum(high) < 5 || sum(.!high) < 5) && return 0.0
    corr_high = safe_corr(f_hat[high], mom[high])
    corr_low = safe_corr(f_hat[.!high], mom[.!high])
    return max(0.0, corr_low - corr_high)^2
end
function _sentiment_interaction_gradient(f_hat, X, dc)
    sent = get_ctx(dc, "sentiment", zeros(length(f_hat)))
    mom = get_ctx(dc, "Mom12m", zeros(length(f_hat)))
    n = length(f_hat)
    med = median(sent)
    high = sent .> med
    (sum(high) < 5 || sum(.!high) < 5) && return zeros(n)
    corr_high = safe_corr(f_hat[high], mom[high])
    corr_low = safe_corr(f_hat[.!high], mom[.!high])
    diff = corr_low - corr_high
    diff <= 0 && return zeros(n)
    grad = zeros(n)
    grad[.!high] .= 2.0 .* diff .* corr_gradient(f_hat[.!high], mom[.!high])
    grad[high] .= 2.0 .* diff .* (-corr_gradient(f_hat[high], mom[high]))
    return grad
end

function _overreaction_penalty(f_hat, X, dc)
    mom = get_ctx(dc, "Mom12m", zeros(length(f_hat)))
    thresh = quantile(abs.(mom), 0.9)
    extreme = abs.(mom) .> thresh
    sum(extreme) < 3 && return 0.0
    sum(.!extreme) < 3 && return 0.0
    mean_ext = mean(abs.(f_hat[extreme]))
    mean_norm = mean(abs.(f_hat[.!extreme]))
    return max(0.0, mean_ext - 2.0 * mean_norm)^2
end
function _overreaction_gradient(f_hat, X, dc)
    mom = get_ctx(dc, "Mom12m", zeros(length(f_hat)))
    n = length(f_hat)
    thresh = quantile(abs.(mom), 0.9)
    extreme = abs.(mom) .> thresh
    (sum(extreme) < 3 || sum(.!extreme) < 3) && return zeros(n)
    mean_ext = mean(abs.(f_hat[extreme]))
    mean_norm = mean(abs.(f_hat[.!extreme]))
    diff = mean_ext - 2.0 * mean_norm
    diff <= 0 && return zeros(n)
    grad = zeros(n)
    ne = sum(extreme); nn = sum(.!extreme)
    grad[extreme] .= 2.0 .* diff .* sign.(f_hat[extreme]) ./ ne
    grad[.!extreme] .= 2.0 .* diff .* (-2.0) .* sign.(f_hat[.!extreme]) ./ nn
    return grad
end

# ════════════════════════════════════════════════════════════════════
#  Build all restrictions
# ════════════════════════════════════════════════════════════════════

function build_all_restrictions()
    restrictions = RestrictionDef[]

    # Consumption (13)
    push!(restrictions, RestrictionDef("euler_capm", "consumption", _euler_capm_penalty, _euler_capm_gradient))
    push!(restrictions, RestrictionDef("euler_habit", "consumption", _euler_habit_penalty, _euler_habit_gradient))
    push!(restrictions, RestrictionDef("euler_lrr", "consumption", _euler_lrr_penalty, _euler_lrr_gradient))
    push!(restrictions, RestrictionDef("euler_ez", "consumption", _euler_ez_penalty, _euler_ez_gradient))
    push!(restrictions, RestrictionDef("cons_growth_mono", "consumption", _cons_growth_mono_penalty, _cons_growth_mono_gradient))
    push!(restrictions, RestrictionDef("euler_cond_capm", "consumption", _euler_cond_capm_penalty, _euler_cond_capm_gradient))
    push!(restrictions, RestrictionDef("euler_durable", "consumption", _euler_durable_penalty, _euler_durable_gradient))
    push!(restrictions, RestrictionDef("cons_beta_pricing", "consumption", _cons_beta_pricing_penalty, _cons_beta_pricing_gradient))
    push!(restrictions, RestrictionDef("recursive_utility", "consumption", _recursive_utility_penalty, _recursive_utility_gradient))
    push!(restrictions, RestrictionDef("disaster_risk", "consumption", _disaster_risk_penalty, _disaster_risk_gradient))
    push!(restrictions, RestrictionDef("intertemporal_sub", "consumption", _intertemporal_sub_penalty, _intertemporal_sub_gradient))
    push!(restrictions, RestrictionDef("precautionary", "consumption", _precautionary_penalty, _precautionary_gradient))
    push!(restrictions, RestrictionDef("cay_predict", "consumption", _cay_predict_penalty, _cay_predict_gradient))

    # Production (10)
    push!(restrictions, RestrictionDef("invest_mono", "production", _invest_mono_p, _invest_mono_g))
    push!(restrictions, RestrictionDef("profit_mono", "production", _profit_mono_p, _profit_mono_g))
    push!(restrictions, RestrictionDef("leverage_effect", "production", _leverage_p, _leverage_g))
    push!(restrictions, RestrictionDef("roa_mono", "production", _roa_mono_p, _roa_mono_g))
    push!(restrictions, RestrictionDef("gp_mono", "production", _gp_mono_p, _gp_mono_g))
    push!(restrictions, RestrictionDef("ag_effect", "production", _ag_effect_p, _ag_effect_g))
    push!(restrictions, RestrictionDef("rd_effect", "production", _rd_effect_p, _rd_effect_g))
    push!(restrictions, RestrictionDef("q_theory", "production", _q_theory_penalty, _q_theory_gradient))
    push!(restrictions, RestrictionDef("capex_growth", "production", _capex_p, _capex_g))
    push!(restrictions, RestrictionDef("bm_value", "production", _bm_value_p, _bm_value_g))

    # Intermediary (8)
    push!(restrictions, RestrictionDef("hkm_capital", "intermediary", _hkm_capital_p, _hkm_capital_g))
    push!(restrictions, RestrictionDef("hkm_factor", "intermediary", _hkm_factor_p, _hkm_factor_g))
    push!(restrictions, RestrictionDef("intermediary_euler", "intermediary", _intermediary_euler_penalty, _intermediary_euler_gradient))
    push!(restrictions, RestrictionDef("sentiment", "intermediary", _sentiment_p, _sentiment_g))
    push!(restrictions, RestrictionDef("sentiment_xs", "intermediary", _sentiment_xs_penalty, _sentiment_xs_gradient))
    push!(restrictions, RestrictionDef("leverage_cycle", "intermediary", _leverage_cycle_penalty, _leverage_cycle_gradient))
    push!(restrictions, RestrictionDef("funding_liquidity", "intermediary", _funding_liq_p, _funding_liq_g))
    push!(restrictions, RestrictionDef("institutional_ownership", "intermediary", _institutional_ownership_penalty, _institutional_ownership_gradient))

    # Information (6)
    push!(restrictions, RestrictionDef("forecast_dispersion", "information", _forecast_disp_p, _forecast_disp_g))
    push!(restrictions, RestrictionDef("macro_uncertainty", "information", _macro_uncert_p, _macro_uncert_g))
    push!(restrictions, RestrictionDef("learning_euler", "information", _learning_euler_penalty, _learning_euler_gradient))
    push!(restrictions, RestrictionDef("ambiguity_aversion", "information", _ambiguity_aversion_penalty, _ambiguity_aversion_gradient))
    push!(restrictions, RestrictionDef("rational_inattention", "information", _rational_inattention_penalty, _rational_inattention_gradient))
    push!(restrictions, RestrictionDef("cons_disagreement", "information", _cons_disagreement_penalty, _cons_disagreement_gradient))

    # Demand (6)
    push!(restrictions, RestrictionDef("market_clearing", "demand", _market_clearing_penalty, _market_clearing_gradient))
    push!(restrictions, RestrictionDef("demand_elasticity", "demand", _demand_elast_p, _demand_elast_g))
    push!(restrictions, RestrictionDef("inelastic_markets", "demand", _inelastic_markets_penalty, _inelastic_markets_gradient))
    push!(restrictions, RestrictionDef("asset_embedding", "demand", _asset_embedding_penalty, _asset_embedding_gradient))
    push!(restrictions, RestrictionDef("substitution_pattern", "demand", _substitution_pattern_penalty, _substitution_pattern_gradient))
    push!(restrictions, RestrictionDef("size_demand", "demand", _size_demand_p, _size_demand_g))

    # Volatility (2)
    push!(restrictions, RestrictionDef("vix_premium", "volatility", _vix_premium_p, _vix_premium_g))
    push!(restrictions, RestrictionDef("realized_vol", "volatility", _realized_vol_p, _realized_vol_g))

    # Behavioral (6)
    push!(restrictions, RestrictionDef("momentum", "behavioral", _momentum_p, _momentum_g))
    push!(restrictions, RestrictionDef("st_reversal", "behavioral", _st_reversal_p, _st_reversal_g))
    push!(restrictions, RestrictionDef("lt_reversal", "behavioral", _lt_reversal_p, _lt_reversal_g))
    push!(restrictions, RestrictionDef("sentiment_interaction", "behavioral", _sentiment_interaction_penalty, _sentiment_interaction_gradient))
    push!(restrictions, RestrictionDef("overreaction", "behavioral", _overreaction_penalty, _overreaction_gradient))
    push!(restrictions, RestrictionDef("disposition", "behavioral", _disposition_penalty, _disposition_gradient))

    # Macro (5)
    push!(restrictions, RestrictionDef("term_spread", "macro", _term_spread_p, _term_spread_g))
    push!(restrictions, RestrictionDef("default_spread", "macro", _default_spread_p, _default_spread_g))
    push!(restrictions, RestrictionDef("ebp_predict", "macro", _ebp_predict_p, _ebp_predict_g))
    push!(restrictions, RestrictionDef("rf_effect", "macro", _rf_effect_p, _rf_effect_g))
    push!(restrictions, RestrictionDef("macro_factor", "macro", _macro_factor_penalty, _macro_factor_gradient))

    return restrictions
end

# Group mapping (matching Python DEFAULT_GROUPS)
const FAMILY_TO_GROUP = Dict(
    "consumption" => 0,
    "production" => 1,
    "intermediary" => 2,
    "information" => 3,
    "demand" => 4,
    "volatility" => 5,
    "behavioral" => 6,
    "macro" => 7,
)

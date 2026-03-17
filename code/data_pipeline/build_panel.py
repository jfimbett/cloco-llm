"""
Build monthly security-level panel from raw data files.

Merges CRSP monthly returns, firm characteristics, Compustat fundamentals,
macro variables, and realized variance into a single panel at
../data/processed/panel_monthly.parquet.

Usage:
    python code/data_pipeline/build_panel.py
    python code/data_pipeline/build_panel.py --start 196307 --end 202312
    python code/data_pipeline/build_panel.py --raw-dir ../data/raw --output ../data/processed/panel_monthly.parquet
"""

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. CRSP Monthly
# ---------------------------------------------------------------------------

def load_crsp_monthly(raw_dir: Path, start: int, end: int) -> pd.DataFrame:
    """Load and clean CRSP monthly stock file."""
    log.info("Loading CRSP monthly...")
    df = pd.read_csv(raw_dir / "crsp_monthly.csv", low_memory=False)

    # Coerce returns to numeric (letter codes like 'C', 'B' → NaN)
    df["RET"] = pd.to_numeric(df["RET"], errors="coerce")
    df["RETX"] = pd.to_numeric(df["RETX"], errors="coerce")
    df["PRC"] = pd.to_numeric(df["PRC"], errors="coerce")
    df["SHROUT"] = pd.to_numeric(df["SHROUT"], errors="coerce")

    # Use absolute price (negative means bid-ask midpoint)
    df["PRC"] = df["PRC"].abs()

    # Date to yyyymm
    df["date"] = pd.to_datetime(df["date"])
    df["yyyymm"] = df["date"].dt.year * 100 + df["date"].dt.month

    # Rename for consistency
    df = df.rename(columns={"PERMNO": "permno"})

    # Filters: common stocks on major exchanges, price >= $5
    df = df[df["SHRCD"].isin([10, 11])].copy()
    df = df[df["EXCHCD"].isin([1, 2, 3])].copy()
    df = df[df["PRC"] >= 5].copy()
    df = df[df["yyyymm"].between(start, end)].copy()

    # Market equity (millions)
    df["me"] = df["PRC"] * df["SHROUT"] / 1000.0

    # Characteristics computable from CRSP
    df["price_char"] = np.log(df["PRC"])
    df["size_char"] = np.log(df["me"])
    df["streversal"] = df["RET"]  # short-term reversal = prior month return

    # Winsorize returns at 0.1% / 99.9%
    lo = df["RET"].quantile(0.001)
    hi = df["RET"].quantile(0.999)
    df["RET"] = df["RET"].clip(lo, hi)

    # Past average return (trailing 36-month mean) for extrapolative expectations
    df = df.sort_values(["permno", "yyyymm"])
    df["past_avg_ret"] = (
        df.groupby("permno")["RET"]
        .transform(lambda x: x.rolling(36, min_periods=12).mean())
    )

    keep_cols = [
        "permno", "yyyymm", "date", "RET", "RETX", "PRC", "SHROUT",
        "SHRCD", "EXCHCD", "me", "price_char", "size_char", "streversal",
        "past_avg_ret",
    ]
    df = df[keep_cols].copy()

    log.info(f"  CRSP monthly: {len(df):,} rows, {df['permno'].nunique():,} permnos")
    return df


# ---------------------------------------------------------------------------
# 2. Firm Characteristics (chunked)
# ---------------------------------------------------------------------------

def load_characteristics(raw_dir: Path, permno_set: set, start: int, end: int) -> pd.DataFrame:
    """Load firm characteristics with chunked reading to limit memory."""
    log.info("Loading firm characteristics (chunked)...")
    chunks = []
    n_rows = 0
    for chunk in pd.read_csv(
        raw_dir / "firm_characteristics.csv",
        chunksize=500_000,
        low_memory=False,
    ):
        chunk = chunk[chunk["permno"].isin(permno_set)].copy()
        chunk = chunk[chunk["yyyymm"].between(start, end)].copy()
        chunks.append(chunk)
        n_rows += len(chunk)

    df = pd.concat(chunks, ignore_index=True)
    log.info(f"  Characteristics: {len(df):,} rows, {df.shape[1] - 2} features")
    return df


# ---------------------------------------------------------------------------
# 3. Compustat Annual
# ---------------------------------------------------------------------------

def load_compustat_annual(raw_dir: Path) -> pd.DataFrame:
    """Load Compustat annual and compute accounting ratios."""
    log.info("Loading Compustat annual...")
    df = pd.read_csv(raw_dir / "compustat_annual.csv", low_memory=False)

    # Standardize gvkey
    df["gvkey"] = df["gvkey"].astype(str).str.zfill(6)
    df["datadate"] = pd.to_datetime(df["datadate"])

    # Keep only domestic, standard format
    df = df[
        (df["indfmt"] == "INDL")
        & (df["datafmt"] == "STD")
        & (df["consol"] == "C")
        & (df["curcd"] == "USD")
    ].copy()

    # Accounting ratios (handle division by zero with replace)
    at = df["at"].replace(0, np.nan)
    ceq = df["ceq"].replace(0, np.nan)
    sale = df["sale"].replace(0, np.nan)
    ppent = df["ppent"].replace(0, np.nan)

    df["ik"] = df["capx"] / ppent                      # investment rate
    df["roe"] = df["ib"] / ceq                          # return on equity
    df["leverage"] = (df["dlc"].fillna(0) + df["dltt"].fillna(0)) / at
    df["bm"] = ceq / (df["csho"] * df["prcc_f"]).replace(0, np.nan)  # book-to-market
    df["roa"] = df["ib"] / at                           # return on assets
    df["gp"] = (df["revt"] - df["cogs"]) / at           # gross profitability
    df["ag"] = df.groupby("gvkey")["at"].pct_change(fill_method=None)  # asset growth
    df["rd_intensity"] = df["xrd"].fillna(0) / sale      # R&D intensity
    total_debt = (df["dlc"].fillna(0) + df["dltt"].fillna(0)).replace(0, np.nan)
    df["k_debt"] = ppent / total_debt                      # collateral: PPE / total debt
    df["sga_at"] = df["xsga"].fillna(np.nan) / at          # SGA intensity

    # Available date: datadate + 6 months (GKX convention for lookahead avoidance)
    df["yyyymm_available"] = (
        (df["datadate"] + pd.DateOffset(months=6))
        .dt.year * 100
        + (df["datadate"] + pd.DateOffset(months=6)).dt.month
    )

    keep_cols = [
        "gvkey", "datadate", "sic", "yyyymm_available",
        "ik", "roe", "leverage", "bm", "roa", "gp", "ag", "rd_intensity",
        "k_debt", "sga_at",
    ]
    df = df[keep_cols].dropna(subset=["yyyymm_available"]).copy()
    df = df.sort_values(["gvkey", "yyyymm_available"])

    log.info(f"  Compustat annual: {len(df):,} rows")
    return df


# ---------------------------------------------------------------------------
# 4. Compustat Quarterly
# ---------------------------------------------------------------------------

def load_compustat_quarterly(raw_dir: Path) -> pd.DataFrame:
    """Load Compustat quarterly with point-in-time dating."""
    log.info("Loading Compustat quarterly...")
    df = pd.read_csv(raw_dir / "compustat_quarterly.csv", low_memory=False)

    df["gvkey"] = df["gvkey"].astype(str).str.zfill(6)
    df["datadate"] = pd.to_datetime(df["datadate"])
    df["rdq"] = pd.to_datetime(df["rdq"], errors="coerce")

    # Keep standard format
    df = df[
        (df["indfmt"] == "INDL")
        & (df["datafmt"] == "STD")
        & (df["consol"] == "C")
    ].copy()

    # Point-in-time: use rdq if available, else datadate + 3 months
    df["pit_date"] = df["rdq"].fillna(df["datadate"] + pd.DateOffset(months=3))
    df["yyyymm_available"] = df["pit_date"].dt.year * 100 + df["pit_date"].dt.month

    # Quarterly ratios
    atq = df["atq"].replace(0, np.nan)
    ceqq = df["ceqq"].replace(0, np.nan)

    df["roaq"] = df["ibq"] / atq
    df["sue"] = df.groupby("gvkey")["ibq"].diff(4) / df.groupby("gvkey")["ibq"].shift(4).abs().replace(0, np.nan)
    df["ceqq_growth"] = df.groupby("gvkey")["ceqq"].pct_change(4, fill_method=None)

    # Rename to avoid collision with characteristics file's roaq
    df = df.rename(columns={"roaq": "roaq_comp"})
    keep_cols = ["gvkey", "datadate", "yyyymm_available", "roaq_comp", "sue", "ceqq_growth"]
    df = df[keep_cols].dropna(subset=["yyyymm_available"]).copy()
    df = df.sort_values(["gvkey", "yyyymm_available"])

    log.info(f"  Compustat quarterly: {len(df):,} rows")
    return df


# ---------------------------------------------------------------------------
# 5. CCM Link
# ---------------------------------------------------------------------------

def build_ccm_link(raw_dir: Path) -> pd.DataFrame:
    """Build clean CRSP-Compustat link table."""
    log.info("Building CCM link...")
    df = pd.read_csv(raw_dir / "ccm_link.csv", low_memory=False)

    df = df.rename(columns={"LPERMNO": "permno"})
    df["gvkey"] = df["gvkey"].astype(str).str.zfill(6)

    # Filter link types
    df = df[df["LINKTYPE"].isin(["LC", "LU"])].copy()
    df = df[df["LINKPRIM"].isin(["P", "C"])].copy()

    # Parse dates
    df["LINKDT"] = pd.to_datetime(df["LINKDT"])
    df["LINKENDDT"] = pd.to_datetime(df["LINKENDDT"], errors="coerce")
    # Missing end date means still active
    df["LINKENDDT"] = df["LINKENDDT"].fillna(pd.Timestamp("2099-12-31"))

    # Deduplicate: prefer P over C, LC over LU
    link_prim_order = {"P": 0, "C": 1}
    link_type_order = {"LC": 0, "LU": 1}
    df["_prim_rank"] = df["LINKPRIM"].map(link_prim_order)
    df["_type_rank"] = df["LINKTYPE"].map(link_type_order)
    df = df.sort_values(["permno", "LINKDT", "_prim_rank", "_type_rank"])
    df = df.drop(columns=["_prim_rank", "_type_rank"])

    keep_cols = ["permno", "gvkey", "LINKDT", "LINKENDDT"]
    df = df[keep_cols].copy()

    log.info(f"  CCM links: {len(df):,} rows")
    return df


# ---------------------------------------------------------------------------
# 6. Merge Compustat via CCM
# ---------------------------------------------------------------------------

def merge_compustat(
    crsp: pd.DataFrame,
    ccm: pd.DataFrame,
    comp_a: pd.DataFrame,
    comp_q: pd.DataFrame,
) -> pd.DataFrame:
    """Attach Compustat annual and quarterly data to CRSP via CCM link."""
    log.info("Merging Compustat via CCM...")

    # Attach gvkey to CRSP via time-varying CCM link
    # Expand CCM to monthly level for conditional merge
    merged = crsp.merge(ccm, on="permno", how="left")

    # Keep only rows where CRSP date falls within link window
    merged = merged[
        (merged["date"] >= merged["LINKDT"])
        & (merged["date"] <= merged["LINKENDDT"])
    ].copy()

    # Deduplicate permno-month: keep first (already sorted by priority)
    merged = merged.drop_duplicates(subset=["permno", "yyyymm"], keep="first")
    merged = merged.drop(columns=["LINKDT", "LINKENDDT"])

    # Split: rows with gvkey get Compustat merge, rows without skip it
    has_gvkey = merged[merged["gvkey"].notna()].copy()
    no_gvkey = merged[merged["gvkey"].isna()].copy()

    # Ensure yyyymm is int for merge_asof (NaN contamination can make it float)
    has_gvkey["yyyymm"] = has_gvkey["yyyymm"].astype(int)

    # --- Merge annual Compustat via merge_asof ---
    # merge_asof requires left on-key globally sorted
    has_gvkey = has_gvkey.sort_values("yyyymm")
    comp_a["yyyymm_available"] = comp_a["yyyymm_available"].astype(int)
    comp_a = comp_a.sort_values("yyyymm_available")

    has_gvkey = pd.merge_asof(
        has_gvkey,
        comp_a.rename(columns={"yyyymm_available": "yyyymm_a"}),
        left_on="yyyymm",
        right_on="yyyymm_a",
        by="gvkey",
        direction="backward",
    )

    # --- Merge quarterly Compustat via merge_asof ---
    # Re-sort after first merge_asof (it may scramble order)
    has_gvkey = has_gvkey.sort_values("yyyymm")
    comp_q["yyyymm_available"] = comp_q["yyyymm_available"].astype(int)
    comp_q = comp_q.sort_values("yyyymm_available")

    has_gvkey = pd.merge_asof(
        has_gvkey,
        comp_q.rename(columns={"yyyymm_available": "yyyymm_q"}),
        left_on="yyyymm",
        right_on="yyyymm_q",
        by="gvkey",
        direction="backward",
    )

    # Recombine
    merged = pd.concat([has_gvkey, no_gvkey], ignore_index=True)

    # Drop helper columns
    for col in ["yyyymm_a", "yyyymm_q", "datadate_x", "datadate_y"]:
        if col in merged.columns:
            merged = merged.drop(columns=[col])

    log.info(f"  After Compustat merge: {len(merged):,} rows, gvkey fill rate: "
             f"{merged['gvkey'].notna().mean():.1%}")
    return merged


# ---------------------------------------------------------------------------
# 7. Macro Variables
# ---------------------------------------------------------------------------

def load_macro(raw_dir: Path, start: int, end: int) -> pd.DataFrame:
    """Harmonize 9 macro datasets to monthly yyyymm frequency."""
    log.info("Loading macro variables...")

    # --- FF Factors ---
    ff = pd.read_csv(raw_dir / "ff_factors_monthly.csv")
    ff = ff.rename(columns={"date": "yyyymm"})
    ff["yyyymm"] = ff["yyyymm"].astype(int)
    # Divide by 100 (Ken French reports in percent)
    for col in ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF", "Mom"]:
        ff[col] = ff[col] / 100.0
    ff = ff.rename(columns={"Mkt-RF": "mktrf", "RF": "rf"})
    # Lowercase all
    ff.columns = ff.columns.str.lower()

    # --- FRED Macro ---
    fred = pd.read_csv(raw_dir / "fred_macro.csv", parse_dates=["date"])
    fred["yyyymm"] = fred["date"].dt.year * 100 + fred["date"].dt.month
    fred["term_spread"] = fred["GS10"] - fred["TB3MS"]
    fred["default_spread"] = fred["BAA"] - fred["AAA"]
    fred = fred[["yyyymm", "TB3MS", "term_spread", "default_spread",
                 "CPIAUCSL", "INDPRO", "UNRATE"]].copy()
    fred.columns = fred.columns.str.lower()

    # --- NIPA Consumption ---
    nipa = pd.read_csv(raw_dir / "nipa_consumption.csv", parse_dates=["date"])
    # Real per capita consumption = (PCEND + PCES) / PCEPI / POPTHM
    # PCES = monthly services; fallback to PCESV (quarterly) for legacy files
    svc_col = "PCES" if "PCES" in nipa.columns else "PCESV"
    nipa["real_cons_pc"] = (nipa["PCEND"].fillna(0) + nipa[svc_col].fillna(0)) / nipa["PCEPI"] / nipa["POPTHM"]
    nipa["cons_growth"] = nipa["real_cons_pc"].pct_change()
    nipa["yyyymm"] = nipa["date"].dt.year * 100 + nipa["date"].dt.month
    nipa = nipa[["yyyymm", "cons_growth"]].copy()

    # --- HKM Intermediary ---
    hkm = pd.read_csv(raw_dir / "hkm_intermediary.csv")
    # yyyyq is float like 19701.0 → parse to quarterly, then forward fill to monthly
    hkm["year"] = (hkm["yyyyq"] // 10).astype(int)
    hkm["quarter"] = (hkm["yyyyq"] % 10).astype(int)
    hkm["date"] = pd.to_datetime(
        hkm["year"].astype(str) + "-" + ((hkm["quarter"] - 1) * 3 + 1).astype(str) + "-01"
    )
    hkm["yyyymm"] = hkm["date"].dt.year * 100 + hkm["date"].dt.month
    hkm = hkm[["yyyymm", "intermediary_capital_ratio", "intermediary_capital_risk_factor"]].copy()
    hkm = hkm.rename(columns={
        "intermediary_capital_ratio": "hkm_capital_ratio",
        "intermediary_capital_risk_factor": "hkm_risk_factor",
    })

    # --- CAY ---
    cay = pd.read_csv(raw_dir / "cay.csv", parse_dates=["date"])
    cay["yyyymm"] = cay["date"].dt.year * 100 + cay["date"].dt.month
    cay = cay[["yyyymm", "cay"]].copy()

    # --- VIX (daily → month-end) ---
    vix = pd.read_csv(raw_dir / "vix.csv", parse_dates=["date"])
    vix["VIXCLS"] = pd.to_numeric(vix["VIXCLS"], errors="coerce")
    vix["yyyymm"] = vix["date"].dt.year * 100 + vix["date"].dt.month
    # Take last observation per month (month-end close)
    vix = vix.sort_values("date").groupby("yyyymm")["VIXCLS"].last().reset_index()
    vix = vix.rename(columns={"VIXCLS": "vix"})

    # --- EBP (Excess Bond Premium) ---
    ebp = pd.read_csv(raw_dir / "ebp.csv", parse_dates=["date"])
    ebp["yyyymm"] = ebp["date"].dt.year * 100 + ebp["date"].dt.month
    ebp = ebp.rename(columns={"BAAFFM": "ebp"})
    ebp = ebp[["yyyymm", "ebp"]].copy()

    # --- TED Spread (daily → month-end) ---
    ted_path = raw_dir / "ted_spread.csv"
    if ted_path.exists():
        ted = pd.read_csv(ted_path, parse_dates=["date"])
        ted["TEDRATE"] = pd.to_numeric(ted["TEDRATE"], errors="coerce")
        ted["yyyymm"] = ted["date"].dt.year * 100 + ted["date"].dt.month
        ted = ted.sort_values("date").groupby("yyyymm")["TEDRATE"].last().reset_index()
        ted = ted.rename(columns={"TEDRATE": "ted_spread"})
    else:
        log.warning("  ted_spread.csv not found — skipping TED spread")
        ted = None

    # --- Monetary Policy Surprise ---
    mp_path = raw_dir / "mp_surprise.csv"
    if mp_path.exists():
        mp = pd.read_csv(mp_path, parse_dates=["date"])
        mp["mp_surprise"] = pd.to_numeric(mp["mp_surprise"], errors="coerce")
        mp["yyyymm"] = mp["date"].dt.year * 100 + mp["date"].dt.month
        mp = mp[["yyyymm", "mp_surprise"]].copy()
    else:
        log.warning("  mp_surprise.csv not found — skipping")
        mp = None

    # --- HXZ Q Factors (Hou-Xue-Zhang) ---
    qf_path = raw_dir / "q_factors.csv"
    if qf_path.exists():
        qf = pd.read_csv(qf_path)
        qf["yyyymm"] = qf["year"] * 100 + qf["month"]
        # Divide by 100 (reported in percent)
        for col in ["r_mkt", "r_me", "r_ia", "r_roe", "r_eg"]:
            if col in qf.columns:
                qf[col] = qf[col] / 100.0
        qf = qf[["yyyymm", "r_ia", "r_roe", "r_eg"]].copy()
    else:
        log.warning("  q_factors.csv not found — skipping HXZ factors")
        qf = None

    # --- Breakeven Inflation (10Y TIPS spread) ---
    bei_path = raw_dir / "breakeven_inflation.csv"
    if bei_path.exists():
        bei = pd.read_csv(bei_path, parse_dates=["date"])
        bei["breakeven_infl"] = pd.to_numeric(bei["breakeven_infl"], errors="coerce")
        bei["yyyymm"] = bei["date"].dt.year * 100 + bei["date"].dt.month
        bei = bei[["yyyymm", "breakeven_infl"]].copy()
    else:
        log.warning("  breakeven_inflation.csv not found — skipping")
        bei = None

    # --- BAB Factor (Frazzini-Pedersen) ---
    bab_path = raw_dir / "bab_factor.csv"
    if bab_path.exists():
        bab = pd.read_csv(bab_path, parse_dates=["date"])
        bab["bab"] = pd.to_numeric(bab["bab"], errors="coerce")
        bab["yyyymm"] = bab["date"].dt.year * 100 + bab["date"].dt.month
        bab = bab[["yyyymm", "bab"]].copy()
    else:
        log.warning("  bab_factor.csv not found — skipping BAB factor")
        bab = None

    # --- Sentiment ---
    sent = pd.read_csv(raw_dir / "sentiment.csv")
    sent = sent.rename(columns={"date": "yyyymm"})
    sent["yyyymm"] = sent["yyyymm"].astype(int)
    sent = sent[["yyyymm", "sentiment"]].copy()

    # --- Welch-Goyal ---
    wg = pd.read_csv(raw_dir / "welch_goyal.csv")
    wg["yyyymm"] = wg["yyyymm"].astype(int)
    wg_cols = ["yyyymm", "D12", "E12", "b/m", "tbl", "ntis", "infl", "svar"]
    wg_cols = [c for c in wg_cols if c in wg.columns]
    wg = wg[wg_cols].copy()
    wg = wg.rename(columns={"b/m": "bm_wg", "D12": "d12", "E12": "e12"})

    # --- Assemble monthly macro panel ---
    # Start with FF (monthly, most complete)
    yyyymm_range = pd.DataFrame({"yyyymm": range(start, end + 1)})
    # Filter to valid months only
    yyyymm_range = yyyymm_range[yyyymm_range["yyyymm"] % 100 <= 12]
    yyyymm_range = yyyymm_range[yyyymm_range["yyyymm"] % 100 >= 1]

    macro = yyyymm_range.copy()
    monthly_sources = [ff, fred, vix, ebp, sent, wg]
    if ted is not None:
        monthly_sources.append(ted)
    if bei is not None:
        monthly_sources.append(bei)
    if bab is not None:
        monthly_sources.append(bab)
    if qf is not None:
        monthly_sources.append(qf)
    if mp is not None:
        monthly_sources.append(mp)
    for source in monthly_sources:
        macro = macro.merge(source, on="yyyymm", how="left")

    # --- Equity Flows (quarterly, household equity transactions) ---
    flow_path = raw_dir / "equity_flows.csv"
    if flow_path.exists():
        eflow = pd.read_csv(flow_path, parse_dates=["date"])
        eflow["equity_flow"] = pd.to_numeric(eflow["equity_flow"], errors="coerce")
        eflow["yyyymm"] = eflow["date"].dt.year * 100 + eflow["date"].dt.month
        eflow = eflow[["yyyymm", "equity_flow"]].copy()
    else:
        log.warning("  equity_flows.csv not found — skipping")
        eflow = None

    # --- AEM Intermediary Leverage (quarterly) ---
    aem_path = raw_dir / "aem_leverage.csv"
    if aem_path.exists():
        aem = pd.read_csv(aem_path, parse_dates=["date"])
        aem["yyyymm"] = aem["date"].dt.year * 100 + aem["date"].dt.month
        aem = aem[["yyyymm", "aem_leverage", "aem_leverage_change"]].copy()
    else:
        log.warning("  aem_leverage.csv not found — skipping AEM leverage")
        aem = None

    # Forward-fill quarterly series (NIPA, HKM, CAY, AEM) into monthly
    quarterly_sources = [nipa, hkm, cay]
    if aem is not None:
        quarterly_sources.append(aem)
    if eflow is not None:
        quarterly_sources.append(eflow)
    for qdf in quarterly_sources:
        macro = macro.merge(qdf, on="yyyymm", how="left")
        # Forward fill the columns just added
        new_cols = [c for c in qdf.columns if c != "yyyymm"]
        macro[new_cols] = macro[new_cols].ffill()

    macro = macro[macro["yyyymm"].between(start, end)].copy()
    log.info(f"  Macro: {len(macro):,} months, {macro.shape[1] - 1} variables")
    return macro


# ---------------------------------------------------------------------------
# 8. Realized Variance (chunked)
# ---------------------------------------------------------------------------

def compute_realized_variance(
    raw_dir: Path, permno_set: set, start: int, end: int
) -> pd.DataFrame:
    """Compute monthly realized variance from CRSP daily returns (chunked)."""
    log.info("Computing realized variance from CRSP daily (chunked)...")
    agg_list = []

    for chunk in pd.read_csv(
        raw_dir / "crsp_daily.csv",
        chunksize=5_000_000,
        low_memory=False,
    ):
        chunk = chunk.rename(columns={"PERMNO": "permno"})
        chunk = chunk[chunk["permno"].isin(permno_set)].copy()
        chunk["RET"] = pd.to_numeric(chunk["RET"], errors="coerce")
        chunk["date"] = pd.to_datetime(chunk["date"])
        chunk["yyyymm"] = chunk["date"].dt.year * 100 + chunk["date"].dt.month
        chunk = chunk[chunk["yyyymm"].between(start, end)].copy()
        chunk = chunk.dropna(subset=["RET"])

        # Partial aggregation: sum of squared returns and count per permno-month
        partial = (
            chunk.groupby(["permno", "yyyymm"])["RET"]
            .agg(ret2_sum=lambda x: (x ** 2).sum(), n_days="count")
            .reset_index()
        )
        agg_list.append(partial)

    if not agg_list:
        log.warning("  No daily data found!")
        return pd.DataFrame(columns=["permno", "yyyymm", "realized_var"])

    # Final aggregation (combine partial chunks)
    agg = pd.concat(agg_list, ignore_index=True)
    agg = agg.groupby(["permno", "yyyymm"]).agg(
        ret2_sum=("ret2_sum", "sum"),
        n_days=("n_days", "sum"),
    ).reset_index()

    # Require at least 15 trading days
    agg = agg[agg["n_days"] >= 15].copy()
    agg["realized_var"] = agg["ret2_sum"]
    agg["permno"] = agg["permno"].astype("int64")
    agg["yyyymm"] = agg["yyyymm"].astype("int64")
    agg = agg[["permno", "yyyymm", "realized_var"]].copy()

    log.info(f"  Realized variance: {len(agg):,} permno-months")
    return agg


# ---------------------------------------------------------------------------
# 9. Build Panel
# ---------------------------------------------------------------------------

def build_panel(
    raw_dir: Path,
    output_path: Path,
    start: int = 196307,
    end: int = 202312,
) -> None:
    """Orchestrate all steps into the final monthly panel."""
    log.info(f"Building panel: {start} to {end}")
    log.info(f"  Raw dir: {raw_dir}")
    log.info(f"  Output:  {output_path}")

    # Step 1: CRSP monthly
    crsp = load_crsp_monthly(raw_dir, start, end)
    permno_set = set(crsp["permno"].unique())

    # Step 2: Firm characteristics (chunked, filtered to CRSP permnos)
    chars = load_characteristics(raw_dir, permno_set, start, end)

    # Step 3-5: Compustat + CCM
    comp_a = load_compustat_annual(raw_dir)
    comp_q = load_compustat_quarterly(raw_dir)
    ccm = build_ccm_link(raw_dir)

    # Step 6: Merge Compustat to CRSP
    panel = merge_compustat(crsp, ccm, comp_a, comp_q)

    # Standardize key columns to consistent dtypes after concat
    panel["permno"] = panel["permno"].astype("int64")
    panel["yyyymm"] = panel["yyyymm"].astype("int64")

    # Industry filter: drop utilities (SIC 4900-4999) and financials (6000-6999)
    if "sic" in panel.columns:
        panel["sic"] = pd.to_numeric(panel["sic"], errors="coerce")
        before = len(panel)
        panel = panel[
            ~(panel["sic"].between(4900, 4999) | panel["sic"].between(6000, 6999))
        ].copy()
        log.info(f"  Industry filter: dropped {before - len(panel):,} rows "
                 f"(utilities + financials)")

    # Step 2b: Merge characteristics
    log.info("Merging firm characteristics...")
    panel = panel.merge(chars, on=["permno", "yyyymm"], how="left")

    # Coalesce roaq: prefer characteristics version, fill gaps from Compustat quarterly
    if "roaq" in panel.columns and "roaq_comp" in panel.columns:
        panel["roaq"] = panel["roaq"].fillna(panel["roaq_comp"])
        panel = panel.drop(columns=["roaq_comp"])
    elif "roaq_comp" in panel.columns:
        panel = panel.rename(columns={"roaq_comp": "roaq"})

    log.info(f"  After chars merge: {panel.shape}")

    # Step 7: Macro variables
    macro = load_macro(raw_dir, start, end)
    panel = panel.merge(macro, on="yyyymm", how="left")

    # Step 8: Realized variance
    rv = compute_realized_variance(raw_dir, permno_set, start, end)
    panel = panel.merge(rv, on=["permno", "yyyymm"], how="left")

    # --- Derived characteristics (need full panel with macro) ---
    log.info("Computing derived characteristics (salience, CGO)...")

    # Salience (Bordalo et al 2012): |R_i - R_m| / cross-sectional std
    if "mktrf" in panel.columns:
        mkt_stats = panel.groupby("yyyymm").agg(
            _mkt_ret=("mktrf", "first"),
            _cross_std=("RET", "std"),
        ).reset_index()
        panel = panel.merge(mkt_stats, on="yyyymm", how="left")
        panel["salience"] = (
            (panel["RET"] - panel["_mkt_ret"]).abs()
            / panel["_cross_std"].replace(0, np.nan)
        )
        panel = panel.drop(columns=["_mkt_ret", "_cross_std"])

    # CGO (capital gains overhang, Grinblatt-Han 2005 / Frazzini 2006)
    # Reference price = EWMA of past prices (halflife 12 months)
    if "PRC" in panel.columns:
        panel = panel.sort_values(["permno", "yyyymm"])
        panel["_ref_price"] = panel.groupby("permno")["PRC"].transform(
            lambda x: x.ewm(halflife=12, min_periods=6).mean()
        )
        panel["cgo"] = (panel["PRC"] - panel["_ref_price"]) / panel["PRC"].replace(0, np.nan)
        panel = panel.drop(columns=["_ref_price"])

    # --- Filters ---
    # Identify characteristic columns (everything from chars except permno, yyyymm)
    id_cols = {"permno", "yyyymm", "date", "RET", "RETX", "PRC", "SHROUT",
               "SHRCD", "EXCHCD", "me", "price_char", "size_char", "streversal",
               "past_avg_ret", "salience", "cgo", "gvkey", "sic"}
    # Annual compustat ratios
    comp_a_cols = {"ik", "roe", "leverage", "bm", "roa", "gp", "ag", "rd_intensity", "k_debt", "sga_at"}
    # Quarterly compustat ratios
    comp_q_cols = {"roaq", "sue", "ceqq_growth"}
    # Macro and RV
    macro_rv_cols = set(macro.columns) | {"realized_var"}

    char_cols = [c for c in panel.columns
                 if c not in id_cols and c not in comp_a_cols
                 and c not in comp_q_cols and c not in macro_rv_cols
                 and c != "yyyymm"]

    # All rankable characteristics = chars file columns + CRSP-derived + Compustat ratios
    rank_cols = char_cols + list(comp_a_cols & set(panel.columns)) + list(comp_q_cols & set(panel.columns))
    # Add CRSP-derived
    for c in ["price_char", "size_char", "streversal", "realized_var",
              "past_avg_ret", "salience", "cgo"]:
        if c in panel.columns and c not in rank_cols:
            rank_cols.append(c)

    # Minimum 15 non-missing characteristics
    panel["_n_chars"] = panel[rank_cols].notna().sum(axis=1)
    before = len(panel)
    panel = panel[panel["_n_chars"] >= 15].copy()
    log.info(f"  Min-chars filter (>=15): dropped {before - len(panel):,} rows")
    panel = panel.drop(columns=["_n_chars"])

    # Deduplicate (safety check)
    before = len(panel)
    panel = panel.drop_duplicates(subset=["permno", "yyyymm"], keep="first")
    if before != len(panel):
        log.warning(f"  Dropped {before - len(panel):,} duplicate permno-months")

    # --- Cross-sectional ranking to [0, 1] ---
    log.info(f"Ranking {len(rank_cols)} characteristics cross-sectionally...")
    for col in rank_cols:
        if col in panel.columns:
            panel[col] = panel.groupby("yyyymm")[col].rank(pct=True)

    # Sort
    panel = panel.sort_values(["permno", "yyyymm"]).reset_index(drop=True)

    # Write to parquet
    output_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(output_path, index=False, engine="pyarrow", compression="snappy")

    log.info(f"Panel written to {output_path}")
    log.info(f"  Shape: {panel.shape}")
    log.info(f"  Permnos: {panel['permno'].nunique():,}")
    log.info(f"  Months: {panel['yyyymm'].nunique():,}")
    log.info(f"  Avg stocks/month: {panel.groupby('yyyymm').size().mean():.0f}")
    log.info(f"  Date range: {panel['yyyymm'].min()} - {panel['yyyymm'].max()}")
    log.info(f"  File size: {output_path.stat().st_size / 1e9:.2f} GB")


# ---------------------------------------------------------------------------
# 10. CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build monthly security panel")
    parser.add_argument("--raw-dir", type=str, default="../data/raw",
                        help="Path to raw data directory")
    parser.add_argument("--output", type=str,
                        default="../data/processed/panel_monthly.parquet",
                        help="Output parquet path")
    parser.add_argument("--start", type=int, default=196307,
                        help="Start yyyymm (default: 196307)")
    parser.add_argument("--end", type=int, default=202312,
                        help="End yyyymm (default: 202312)")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing output")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    output_path = Path(args.output)

    if not raw_dir.exists():
        log.error(f"Raw directory not found: {raw_dir}")
        sys.exit(1)

    if output_path.exists() and not args.force:
        log.error(f"Output already exists: {output_path}. Use --force to overwrite.")
        sys.exit(1)

    build_panel(raw_dir, output_path, args.start, args.end)


if __name__ == "__main__":
    main()

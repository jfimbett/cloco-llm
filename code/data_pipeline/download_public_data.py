"""
Download public datasets for Theory-Informed KRR project.

Downloads 7 publicly available datasets to data/raw/:
  - Kenneth French factors (FF5 + Momentum)
  - NIPA consumption series (from FRED)
  - FRED macro series
  - He-Kelly-Manela intermediary factor
  - Gilchrist-Zakrajsek excess bond premium (from FRED)
  - Welch-Goyal predictors (from Google Sheets)
  - VIX (from FRED)

Usage:
    python code/data_pipeline/download_public_data.py [--force]

Flags:
    --force   Re-download even if file already exists
"""

import argparse
import io
import os
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

# Project root is two levels up from this script
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"


def _ensure_dirs():
    RAW_DIR.mkdir(parents=True, exist_ok=True)


def _should_download(filepath: Path, force: bool) -> bool:
    if force:
        return True
    if filepath.exists() and filepath.stat().st_size > 0:
        print(f"  [SKIP] {filepath.name} already exists. Use --force to re-download.")
        return False
    return True


# ---------------------------------------------------------------------------
# 1. Kenneth French Factors (FF5 + Momentum)
# ---------------------------------------------------------------------------

def _parse_french_csv(text: str) -> pd.DataFrame:
    """Parse the CSV format from French's data library.

    The file has a text header block, then a column-name row (first field empty
    or whitespace), then monthly data (6-digit YYYYMM), then possibly annual
    data (4-digit YYYY). We extract only the monthly section.
    """
    lines = text.replace("\r", "").strip().split("\n")
    data_lines = []
    header = None
    in_data = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_data:
                break  # blank line after data = end of monthly section
            continue

        parts = [p.strip() for p in stripped.split(",")]

        # Detect header row: comma-separated short tokens containing factor names.
        # Must have commas (at least 1 field separator) and short fields (not prose).
        if not in_data and "," in stripped and all(len(p) < 15 for p in parts):
            if any(k in parts for k in ["Mkt-RF", "Mkt_RF", "Mom", "SMB", "HML"]):
                # First field is often empty (the date column has no label)
                header = ["date"] + [p for p in parts[1:] if p]
            in_data = True
            continue

        if in_data:
            # Monthly rows have a 6-digit date
            if len(parts[0]) == 6 and parts[0].isdigit():
                data_lines.append(parts)
            elif len(parts[0]) == 4 and parts[0].isdigit():
                # Annual section starts — stop
                break

    if not header or not data_lines:
        raise ValueError(f"Could not parse French CSV data (header={header}, data_lines={len(data_lines) if data_lines else 0})")

    # Ensure columns match data width
    n_cols = len(data_lines[0])
    header = header[:n_cols]
    while len(header) < n_cols:
        header.append(f"col_{len(header)}")

    df = pd.DataFrame(data_lines, columns=header)

    # Convert to numeric (except date)
    for col in df.columns:
        if col != "date":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


def download_french_factors(force: bool = False):
    """Download FF5 factors and Momentum, merge into one CSV."""
    outpath = RAW_DIR / "ff_factors_monthly.csv"
    if not _should_download(outpath, force):
        return

    print("  Downloading FF5 factors...")
    ff5_url = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_5_Factors_2x3_CSV.zip"
    resp = requests.get(ff5_url, timeout=60)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        csv_name = [n for n in zf.namelist() if n.endswith(".CSV") or n.endswith(".csv")][0]
        ff5_text = zf.read(csv_name).decode("utf-8", errors="replace")
    df_ff5 = _parse_french_csv(ff5_text)

    print("  Downloading Momentum factor...")
    mom_url = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Momentum_Factor_CSV.zip"
    resp = requests.get(mom_url, timeout=60)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        csv_name = [n for n in zf.namelist() if n.endswith(".CSV") or n.endswith(".csv")][0]
        mom_text = zf.read(csv_name).decode("utf-8", errors="replace")
    df_mom = _parse_french_csv(mom_text)

    # Rename momentum column
    mom_cols = [c for c in df_mom.columns if c != "date"]
    if mom_cols:
        df_mom.rename(columns={mom_cols[0]: "Mom"}, inplace=True)

    # Merge on date
    df = df_ff5.merge(df_mom[["date", "Mom"]], on="date", how="left")
    df.to_csv(outpath, index=False)
    print(f"  [OK] {outpath.name}: {len(df)} rows, cols={list(df.columns)}")


# ---------------------------------------------------------------------------
# 2. FRED downloads (generic helper)
# ---------------------------------------------------------------------------

def _get_fred_api_key() -> str | None:
    """Read FRED_API_KEY from environment or .env file."""
    key = os.environ.get('FRED_API_KEY')
    if key:
        return key
    env_path = PROJECT_ROOT / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith('FRED_API_KEY='):
                    return line.split('=', 1)[1].strip()
    return None


def _download_fred_single(sid: str, api_key: str | None = None) -> pd.DataFrame:
    """Download a single FRED series, using API key if available."""
    if api_key:
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={sid}&api_key={api_key}&file_type=json"
        )
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        obs = resp.json()['observations']
        df = pd.DataFrame(obs)[['date', 'value']]
        df = df.rename(columns={'value': sid})
        df[sid] = pd.to_numeric(df[sid], errors='coerce')
    else:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        date_col = [c for c in df.columns if "date" in c.lower()][0]
        df.rename(columns={date_col: "date"}, inplace=True)
        for col in df.columns:
            if col != "date":
                df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _download_fred_series(series_ids: list[str], outpath: Path, force: bool = False):
    """Download multiple FRED series and merge by date."""
    if not _should_download(outpath, force):
        return

    api_key = _get_fred_api_key()
    if api_key:
        print(f"  Using FRED API key")

    frames = []
    for sid in series_ids:
        print(f"  Downloading FRED series: {sid}...")
        df = _download_fred_single(sid, api_key)
        frames.append(df)

    # Merge all on date
    merged = frames[0]
    for f in frames[1:]:
        merged = merged.merge(f, on="date", how="outer")

    merged.sort_values("date", inplace=True)
    merged.to_csv(outpath, index=False)
    print(f"  [OK] {outpath.name}: {len(merged)} rows, cols={list(merged.columns)}")


def download_nipa_consumption(force: bool = False):
    """Download NIPA consumption components from FRED.

    Uses PCES (monthly services) instead of PCESV (quarterly) so that
    consumption growth can be computed at monthly frequency without gaps.
    """
    outpath = RAW_DIR / "nipa_consumption.csv"
    series = ["PCEND", "PCES", "PCEPI", "POPTHM"]
    _download_fred_series(series, outpath, force)


def download_fred_macro(force: bool = False):
    """Download macro series from FRED."""
    outpath = RAW_DIR / "fred_macro.csv"
    series = ["TB3MS", "GS10", "AAA", "BAA", "CPIAUCSL", "INDPRO", "UNRATE"]
    _download_fred_series(series, outpath, force)


def download_ebp(force: bool = False):
    """Download Gilchrist-Zakrajsek excess bond premium from FRED."""
    outpath = RAW_DIR / "ebp.csv"
    series = ["BAAFFM"]
    _download_fred_series(series, outpath, force)


def download_vix(force: bool = False):
    """Download VIX from FRED."""
    outpath = RAW_DIR / "vix.csv"
    series = ["VIXCLS"]
    _download_fred_series(series, outpath, force)


def download_ted_spread(force: bool = False):
    """Download TED spread (3m LIBOR - 3m T-bill) from FRED."""
    outpath = RAW_DIR / "ted_spread.csv"
    series = ["TEDRATE"]
    _download_fred_series(series, outpath, force)


def download_bab_factor(force: bool = False):
    """Download BAB factor (Frazzini-Pedersen) from AQR data library."""
    outpath = RAW_DIR / "bab_factor.csv"
    if not _should_download(outpath, force):
        return

    print("  Downloading BAB factor from AQR...")
    url = "https://images.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Betting-Against-Beta-Equity-Factors-Monthly.xlsx"
    resp = requests.get(url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()

    # Parse: header is row 18, extract USA column
    df = pd.read_excel(io.BytesIO(resp.content), sheet_name="BAB Factors", header=18)
    usa = df[["DATE", "USA"]].copy()
    usa["DATE"] = pd.to_datetime(usa["DATE"])
    usa["USA"] = pd.to_numeric(usa["USA"], errors="coerce")
    usa = usa.rename(columns={"DATE": "date", "USA": "bab"})
    usa.to_csv(outpath, index=False)
    valid = usa["bab"].dropna()
    print(f"  [OK] {outpath.name}: {len(valid)} months, mean={valid.mean():.4f}")


def download_breakeven_inflation(force: bool = False):
    """Download 10-year breakeven inflation rate from FRED (T10YIEM, monthly)."""
    outpath = RAW_DIR / "breakeven_inflation.csv"
    if not _should_download(outpath, force):
        return

    api_key = _get_fred_api_key()
    print("  Downloading 10Y breakeven inflation from FRED...")
    df = _download_fred_single("T10YIEM", api_key)
    df = df.rename(columns={"T10YIEM": "breakeven_infl"})
    df.to_csv(outpath, index=False)
    valid = pd.to_numeric(df["breakeven_infl"], errors="coerce").dropna()
    print(f"  [OK] {outpath.name}: {len(valid)} months, mean={valid.mean():.3f}%")


def download_aem_leverage(force: bool = False):
    """Download AEM intermediary leverage from FRED Flow of Funds.

    Computes broker-dealer leverage = Total Assets / Equity Capital using
    FRED series BOGZ1FL664090005Q and BOGZ1FL665080003Q (quarterly).
    """
    outpath = RAW_DIR / "aem_leverage.csv"
    if not _should_download(outpath, force):
        return

    api_key = _get_fred_api_key()
    print("  Downloading broker-dealer assets and equity from FRED...")
    assets = _download_fred_single("BOGZ1FL664090005Q", api_key)
    equity = _download_fred_single("BOGZ1FL665080003Q", api_key)

    merged = assets.merge(equity, on="date")
    merged["date"] = pd.to_datetime(merged["date"])
    merged = merged.sort_values("date")
    merged["aem_leverage"] = merged["BOGZ1FL664090005Q"] / merged["BOGZ1FL665080003Q"]
    merged["aem_leverage_change"] = merged["aem_leverage"].pct_change(fill_method=None)

    out = merged[["date", "aem_leverage", "aem_leverage_change"]].copy()
    out.to_csv(outpath, index=False)
    valid = out["aem_leverage"].dropna()
    print(f"  [OK] {outpath.name}: {len(valid)} quarters, leverage mean={valid.mean():.1f}")


# ---------------------------------------------------------------------------
# 3. He-Kelly-Manela Intermediary Factor
# ---------------------------------------------------------------------------

def download_hkm(force: bool = False):
    """Download HKM intermediary capital factor."""
    outpath = RAW_DIR / "hkm_intermediary.csv"
    if not _should_download(outpath, force):
        return

    print("  Downloading HKM intermediary factor...")
    url = "https://asaf.manela.org/papers/hkm/intermediarycapitalrisk/He_Kelly_Manela_Factors.zip"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        # Find the CSV/xlsx inside
        names = zf.namelist()
        # Try CSV first, then xlsx
        csv_files = [n for n in names if n.lower().endswith(".csv")]
        xlsx_files = [n for n in names if n.lower().endswith(".xlsx")]

        if csv_files:
            data = zf.read(csv_files[0])
            df = pd.read_csv(io.BytesIO(data))
        elif xlsx_files:
            data = zf.read(xlsx_files[0])
            df = pd.read_excel(io.BytesIO(data))
        else:
            # Try any file that's not a directory
            data_files = [n for n in names if not n.endswith("/")]
            if data_files:
                data = zf.read(data_files[0])
                df = pd.read_csv(io.BytesIO(data))
            else:
                raise ValueError(f"No data file found in HKM zip. Contents: {names}")

    df.to_csv(outpath, index=False)
    print(f"  [OK] {outpath.name}: {len(df)} rows, cols={list(df.columns)}")


# ---------------------------------------------------------------------------
# 4. Welch-Goyal Predictors
# ---------------------------------------------------------------------------

def download_welch_goyal(force: bool = False):
    """Download Welch-Goyal predictors from Google Sheets."""
    outpath = RAW_DIR / "welch_goyal.csv"
    if not _should_download(outpath, force):
        return

    print("  Downloading Welch-Goyal predictors...")
    url = "https://docs.google.com/spreadsheets/d/1OIZg6htTK60wtnCVXvxAujvG1aKEOVYv/export?format=xlsx"
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()

    # Read xlsx — may have multiple sheets; use the first one with data
    xls = pd.ExcelFile(io.BytesIO(resp.content))
    df = pd.read_excel(xls, sheet_name=0)

    # Drop fully empty rows/columns
    df.dropna(how="all", axis=0, inplace=True)
    df.dropna(how="all", axis=1, inplace=True)

    df.to_csv(outpath, index=False)
    print(f"  [OK] {outpath.name}: {len(df)} rows, cols={list(df.columns)}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

DOWNLOADS = [
    ("Kenneth French Factors (FF5 + Mom)", download_french_factors),
    ("NIPA Consumption (FRED)", download_nipa_consumption),
    ("FRED Macro Series", download_fred_macro),
    ("HKM Intermediary Factor", download_hkm),
    ("GZ Excess Bond Premium (FRED)", download_ebp),
    ("Welch-Goyal Predictors", download_welch_goyal),
    ("VIX (FRED)", download_vix),
    ("TED Spread (FRED)", download_ted_spread),
    ("BAB Factor (AQR)", download_bab_factor),
    ("AEM Intermediary Leverage (FRED)", download_aem_leverage),
    ("Breakeven Inflation (FRED)", download_breakeven_inflation),
]


def main():
    parser = argparse.ArgumentParser(description="Download public datasets for Theory-Informed KRR")
    parser.add_argument("--force", action="store_true", help="Re-download even if file exists")
    args = parser.parse_args()

    _ensure_dirs()

    print(f"Downloading public datasets to {RAW_DIR}/\n")

    successes = 0
    failures = []
    for name, func in DOWNLOADS:
        print(f"[{name}]")
        try:
            func(force=args.force)
            successes += 1
        except Exception as e:
            print(f"  [FAIL] {name}: {e}")
            failures.append((name, str(e)))
        print()

    print("=" * 60)
    print(f"Done: {successes}/{len(DOWNLOADS)} succeeded")
    if failures:
        print("\nFailed downloads:")
        for name, err in failures:
            print(f"  - {name}: {err}")

    # Note datasets that need manual download
    print("\n[NOTE] The following datasets are NOT auto-downloadable:")
    print("  - Lettau-Ludvigson cay: website returns 404; provide manually")
    print("  - Baker-Wurgler Sentiment: JS-heavy site, no direct CSV; provide manually")
    print("  Place these in data/raw/ as cay.csv and sentiment.csv respectively.")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())

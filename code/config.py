"""
Centralized configuration loaded from .env file.

TEST_MODE controls whether the pipeline runs on a subsample (fast iteration)
or the full dataset. All estimation scripts should import from here.
"""
import os
from pathlib import Path

# Load .env from project root
_env_path = Path(__file__).resolve().parent.parent / '.env'
if _env_path.exists():
    with open(_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())


def _env_bool(key: str, default: bool = False) -> bool:
    return os.environ.get(key, str(default)).lower() in ('true', '1', 'yes')


def _env_int(key: str, default: int) -> int:
    return int(os.environ.get(key, str(default)))


# --- Public config ---
TEST_MODE: bool = _env_bool('TEST_MODE', False)
TEST_MAX_STOCKS_PER_MONTH: int = _env_int('TEST_MAX_STOCKS_PER_MONTH', 200)
TEST_MAX_ROLLING_WINDOWS: int = _env_int('TEST_MAX_ROLLING_WINDOWS', 3)
USE_GPU: bool = _env_bool('USE_GPU', False)

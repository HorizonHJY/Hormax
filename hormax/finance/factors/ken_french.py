"""Fama-French factor returns from the Ken French Data Library.

The library publishes each factor set as a zipped CSV with a prose preamble,
a header row, the data, then a blank line and a copyright notice. Values are in
**percent** — a row of ``-0.67`` means -0.67%, not -67%. Getting that wrong
scales every regression coefficient by 100, so this module converts once, here,
and returns decimals.

The data is updated monthly and therefore **lags the present by several weeks**.
Callers that regress recent returns against it must expect the overlap to end
before today; :func:`load_factors` reports the actual coverage rather than
silently returning a shorter series than asked for.
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests

BASE_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp"

# Each entry: (zip filename, columns it contributes)
DATASETS = {
    "ff5_daily": ("F-F_Research_Data_5_Factors_2x3_daily_CSV.zip", None),
    "mom_daily": ("F-F_Momentum_Factor_daily_CSV.zip", None),
}

# The library rejects requests without a browser-ish user agent.
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; hormax/0.1)"}


class FactorDataError(RuntimeError):
    """Factor data could not be fetched or parsed."""


@dataclass(frozen=True)
class FactorData:
    """Daily factor returns as decimals, plus the risk-free rate.

    Attributes:
        returns: DataFrame indexed by date. Columns are the factor names in
            lower snake case (``mkt_rf``, ``smb``, ``hml``, ``rmw``, ``cma``,
            ``mom``) plus ``rf``.
        start: First date covered.
        end: Last date covered — expect this to lag today by weeks.
        source: Where the data came from.
    """

    returns: pd.DataFrame
    start: date
    end: date
    source: str

    @property
    def factor_columns(self) -> list[str]:
        return [c for c in self.returns.columns if c != "rf"]


def _download(filename: str, timeout: int) -> str:
    url = f"{BASE_URL}/{filename}"
    try:
        response = requests.get(url, timeout=timeout, headers=_HEADERS)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise FactorDataError(f"could not download {url}: {exc}") from exc

    try:
        archive = zipfile.ZipFile(io.BytesIO(response.content))
    except zipfile.BadZipFile as exc:
        raise FactorDataError(f"{url} did not return a valid zip archive") from exc

    names = archive.namelist()
    if not names:
        raise FactorDataError(f"{url} contained an empty archive")
    return archive.read(names[0]).decode("utf-8", errors="replace")


def _parse(raw: str, filename: str) -> pd.DataFrame:
    """Pull the daily block out of a Ken French CSV.

    The preamble length varies per file, so locate the data by shape — the
    first line whose first field is an 8-digit date — rather than by a fixed
    skiprows count that would silently break when the preamble is reworded.
    """
    lines = raw.splitlines()

    header_index = None
    for index, line in enumerate(lines):
        first = line.split(",")[0].strip()
        if len(first) == 8 and first.isdigit():
            header_index = index - 1
            break

    if header_index is None or header_index < 0:
        raise FactorDataError(f"{filename}: could not locate the daily data block")

    frame = pd.read_csv(io.StringIO(raw), skiprows=header_index, index_col=0)

    # Trailing blank line and copyright notice arrive as non-numeric index
    # entries; annual blocks in some files do too.
    index_text = frame.index.astype(str).str.strip()
    frame = frame[index_text.str.fullmatch(r"\d{8}")]

    frame.index = pd.to_datetime(frame.index.astype(str).str.strip(), format="%Y%m%d")
    frame.index.name = "date"

    frame = frame.apply(pd.to_numeric, errors="coerce")
    frame = frame.dropna(how="all")

    # -99.99 is the library's missing-data sentinel. Leaving it in would look
    # like a -99% day and quietly destroy any regression it touches.
    frame = frame.mask(frame <= -99.0)

    return frame / 100.0        # percent → decimal


def _normalise(name: str) -> str:
    return name.strip().lower().replace("-", "_").replace(" ", "_")


def load_factors(
    *,
    cache_dir: Path | None = None,
    max_age_days: int = 7,
    timeout: int = 60,
) -> FactorData:
    """Fetch FF5 + momentum daily factors, merged on date.

    Args:
        cache_dir: Where to keep a local copy. The library updates monthly, so
            re-downloading on every call is pure waste. ``None`` disables
            caching.
        max_age_days: Refetch when the cached copy is older than this.
        timeout: Per-request timeout in seconds.

    Returns:
        FactorData with decimal returns.

    Raises:
        FactorDataError: If the data cannot be fetched or parsed.
    """
    cache_file = None
    if cache_dir is not None:
        cache_dir = Path(cache_dir)
        cache_file = cache_dir / "ken_french_daily.parquet"
        if cache_file.exists():
            age = datetime.now(timezone.utc).timestamp() - cache_file.stat().st_mtime
            if age < max_age_days * 86400:
                cached = pd.read_parquet(cache_file)
                return _to_factor_data(cached, source=f"cache:{cache_file}")

    frames = []
    for filename, _ in DATASETS.values():
        parsed = _parse(_download(filename, timeout), filename)
        parsed.columns = [_normalise(c) for c in parsed.columns]
        frames.append(parsed)

    merged = frames[0]
    for extra in frames[1:]:
        # RF only exists in the FF5 file; an inner join keeps the intersection,
        # which is what a regression needs anyway.
        merged = merged.join(extra, how="inner", rsuffix="_dup")

    merged = merged[[c for c in merged.columns if not c.endswith("_dup")]]
    merged = merged.dropna(how="any").sort_index()

    if merged.empty:
        raise FactorDataError("factor files parsed but produced no overlapping rows")

    if cache_file is not None:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            merged.to_parquet(cache_file)
        except Exception:
            pass        # a failed cache write must not fail the fetch

    return _to_factor_data(merged, source=BASE_URL)


def _to_factor_data(frame: pd.DataFrame, *, source: str) -> FactorData:
    return FactorData(
        returns=frame,
        start=frame.index[0].date(),
        end=frame.index[-1].date(),
        source=source,
    )

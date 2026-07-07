"""Utility functions for the BI application."""

from __future__ import annotations
import hashlib
import json
import pickle
import re
from pathlib import Path
from typing import Any, Optional

import pandas as pd


def sanitize_filename(name: str) -> str:
    """Remove or replace characters that are invalid in filenames."""
    return re.sub(r'[<>:"/\\|?*]', "_", name)[:100]


def format_number(num: float | int) -> str:
    """Format large numbers with K/M/B suffixes."""
    if abs(num) >= 1e9:
        return f"{num/1e9:.2f}B"
    if abs(num) >= 1e6:
        return f"{num/1e6:.2f}M"
    if abs(num) >= 1e3:
        return f"{num/1e3:.1f}K"
    return f"{num:,.2f}" if isinstance(num, float) else f"{num:,}"


def detect_date_columns(df: pd.DataFrame) -> list[str]:
    """Auto-detect date-like columns."""
    date_cols = []
    for col in df.columns:
        if df[col].dtype == "datetime64[ns]":
            date_cols.append(col)
        elif df[col].dtype == "object":
            # Try parsing as date
            try:
                sample = df[col].dropna().head(5)
                if pd.to_datetime(sample, errors="coerce").notna().sum() >= 3:
                    date_cols.append(col)
            except Exception:
                continue
    return date_cols


def auto_clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Basic automatic data cleaning."""
    df = df.copy()

    # Strip whitespace from string columns
    for col in df.select_dtypes(include="object"):
        df[col] = df[col].astype(str).str.strip()

    # Try converting object columns that look like numbers
    for col in df.select_dtypes(include="object"):
        try:
            converted = pd.to_numeric(df[col], errors="coerce")
            if converted.notna().sum() > len(df) * 0.5:
                df[col] = converted
        except Exception:
            continue

    # Try converting object columns that look like dates
    for col in df.select_dtypes(include="object"):
        try:
            converted = pd.to_datetime(df[col], errors="coerce", infer_datetime_format=True)
            if converted.notna().sum() > len(df) * 0.5:
                df[col] = converted
        except Exception:
            continue

    # Drop completely empty columns
    df = df.dropna(axis=1, how="all")

    # Fill small NaN counts in numeric columns with median (avoid data leakage)
    for col in df.select_dtypes(include="number"):
        if df[col].isna().sum() > 0 and df[col].isna().sum() / len(df) < 0.3:
            df[col] = df[col].fillna(df[col].median())

    return df


def profile_dataset(df: pd.DataFrame) -> dict:
    """Quick profiling without pandas-profiling dependency."""
    profile = {
        "shape": df.shape,
        "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
        "missing": df.isna().sum().to_dict(),
        "missing_pct": (df.isna().sum() / len(df) * 100).round(1).to_dict(),
        "unique_counts": {c: int(df[c].nunique()) for c in df.columns},
    }
    # Memory usage
    profile["memory_mb"] = round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2)
    # Duplicates
    profile["duplicate_rows"] = int(df.duplicated().sum())
    return profile


def safe_json_dumps(obj: Any) -> str:
    """JSON serialize with fallback for non-serializable types."""
    class CustomEncoder(json.JSONEncoder):
        def default(self, o):
            try:
                return str(o)
            except Exception:
                return None
    return json.dumps(obj, cls=CustomEncoder, indent=2)


def chunk_dataframe(df: pd.DataFrame, chunk_size: int = 100) -> list[pd.DataFrame]:
    """Split a dataframe into chunks (for large datasets)."""
    return [df[i:i + chunk_size] for i in range(0, len(df), chunk_size)]


__all__ = [
    "sanitize_filename", "format_number", "detect_date_columns",
    "auto_clean_df", "profile_dataset", "safe_json_dumps", "chunk_dataframe",
]

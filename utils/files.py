"""File management utilities for script and plot outputs."""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any, Union


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUTS_DIR = PROJECT_ROOT / "outputs"


def ensure_outputs_dir(dir_path: Union[str, Path] = DEFAULT_OUTPUTS_DIR) -> Path:
    """Ensures the output directory exists and returns its Path."""
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def sanitize_filename_token(token: str) -> str:
    """Sanitizes ticker symbols and timeframe strings for filesystem safety."""
    if not token:
        return "UNKNOWN"
    # Replace dots and special characters with underscore
    sanitized = re.sub(r"[^A-Za-z0-9_-]", "_", token.strip())
    return sanitized or "UNKNOWN"


def generate_filename(
    symbols: Union[List[str], str],
    timeframe: str = "ytd",
    extension: str = "py",
    timestamp: Optional[datetime] = None
) -> str:
    """Generates a unique, descriptive filename formatted as {symbols}_{timeframe}_{timestamp}.{extension}.
    
    Example: TSLA_ytd_20260910_143201.py
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    if isinstance(symbols, list):
        symbols_str = "_".join(sanitize_filename_token(s) for s in symbols if s) or "STOCK"
    else:
        symbols_str = sanitize_filename_token(symbols) or "STOCK"
        
    timeframe_str = sanitize_filename_token(timeframe)
    time_str = timestamp.strftime("%Y%m%d_%H%M%S")
    ext = extension.lstrip(".")
    
    return f"{symbols_str}_{timeframe_str}_{time_str}.{ext}"


def get_associated_chart_path(script_path: Union[str, Path]) -> Path:
    """Returns the matching .png path for a given .py script path."""
    p = Path(script_path)
    return p.with_suffix(".png")


def get_latest_saved_script(dir_path: Union[str, Path] = DEFAULT_OUTPUTS_DIR) -> Optional[Path]:
    """Finds the most recently modified .py script in the outputs directory."""
    path = Path(dir_path)
    if not path.exists():
        return None
    py_files = list(path.glob("*.py"))
    if not py_files:
        return None
    # Sort by modification time, newest first
    py_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return py_files[0]


def list_saved_analyses(dir_path: Union[str, Path] = DEFAULT_OUTPUTS_DIR) -> List[Dict[str, Any]]:
    """Scans the outputs directory and returns metadata for all saved analyses."""
    path = Path(dir_path)
    if not path.exists():
        return []

    results = []
    py_files = sorted(path.glob("*.py"), key=lambda p: p.stat().st_mtime, reverse=True)
    for py_file in py_files:
        chart_file = py_file.with_suffix(".png")
        stat = py_file.stat()
        results.append({
            "script_name": py_file.name,
            "script_path": str(py_file.resolve()),
            "has_chart": chart_file.exists(),
            "chart_path": str(chart_file.resolve()) if chart_file.exists() else None,
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "size_bytes": stat.st_size,
        })
    return results

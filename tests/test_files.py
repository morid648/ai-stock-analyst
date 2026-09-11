"""Unit tests for utils/files.py."""

import pytest
from datetime import datetime
from pathlib import Path
from utils.files import (
    sanitize_filename_token,
    generate_filename,
    get_associated_chart_path,
    get_latest_saved_script,
    list_saved_analyses,
    ensure_outputs_dir,
)


class TestFilesUtil:
    def test_sanitize_filename_token(self):
        assert sanitize_filename_token("RELIANCE.NS") == "RELIANCE_NS"
        assert sanitize_filename_token("TSLA") == "TSLA"
        assert sanitize_filename_token("") == "UNKNOWN"
        assert sanitize_filename_token("^GSPC") == "_GSPC"

    def test_generate_filename_single_ticker(self):
        fixed_time = datetime(2026, 9, 10, 14, 30, 45)
        name = generate_filename("TSLA", timeframe="ytd", extension="py", timestamp=fixed_time)
        assert name == "TSLA_ytd_20260910_143045.py"

    def test_generate_filename_multi_ticker(self):
        fixed_time = datetime(2026, 9, 10, 14, 30, 45)
        name = generate_filename(["AAPL", "MSFT"], timeframe="1y", extension="png", timestamp=fixed_time)
        assert name == "AAPL_MSFT_1y_20260910_143045.png"

    def test_get_associated_chart_path(self):
        p = Path("outputs/TSLA_ytd_20260910_143045.py")
        chart_path = get_associated_chart_path(p)
        assert chart_path == Path("outputs/TSLA_ytd_20260910_143045.png")

    def test_get_latest_saved_script_and_listing(self, tmp_path):
        ensure_outputs_dir(tmp_path)
        assert get_latest_saved_script(tmp_path) is None

        # Create two scripts with different mtimes
        f1 = tmp_path / "AAPL_1y_1.py"
        f1.write_text("print('aapl')")
        
        f2 = tmp_path / "TSLA_ytd_2.py"
        f2.write_text("print('tsla')")

        # Also create a chart for f2
        chart2 = tmp_path / "TSLA_ytd_2.png"
        chart2.write_bytes(b"PNGDATA")

        latest = get_latest_saved_script(tmp_path)
        assert latest is not None
        assert latest.suffix == ".py"

        analyses = list_saved_analyses(tmp_path)
        assert len(analyses) == 2
        tsla_entry = next(a for a in analyses if a["script_name"] == "TSLA_ytd_2.py")
        assert tsla_entry["has_chart"] is True

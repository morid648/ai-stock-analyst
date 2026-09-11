"""Unit tests for utils/executor.py."""

import pytest
from pathlib import Path
from utils.executor import execute_script


class TestExecutor:
    def test_execute_valid_script(self, tmp_path):
        script = tmp_path / "valid_test.py"
        script.write_text("print('Hello from isolated subprocess!')")
        
        res = execute_script(script, timeout_seconds=10)
        assert res.success is True
        assert "Hello from isolated subprocess!" in res.stdout
        assert res.error is None

    def test_execute_script_with_chart_generation(self, tmp_path):
        script = tmp_path / "plot_test.py"
        chart_file = tmp_path / "plot_test.png"
        script.write_text(f"""
from pathlib import Path
Path(r"{chart_file}").write_text("dummy png")
print("Chart saved")
""")
        res = execute_script(script, timeout_seconds=10)
        assert res.success is True
        assert res.chart_path is not None
        assert Path(res.chart_path).exists()

    def test_execute_script_with_runtime_error(self, tmp_path):
        script = tmp_path / "failing_test.py"
        script.write_text("raise ValueError('Something broke during calculation!')")

        res = execute_script(script, timeout_seconds=10)
        assert res.success is False
        assert res.error is not None
        assert "ValueError" in res.error

    def test_execute_nonexistent_script(self, tmp_path):
        missing = tmp_path / "does_not_exist.py"
        res = execute_script(missing)
        assert res.success is False
        assert "not found" in res.error.lower()

    def test_execute_script_timeout(self, tmp_path):
        script = tmp_path / "slow_test.py"
        script.write_text("import time\ntime.sleep(5)\nprint('done')")

        res = execute_script(script, timeout_seconds=1)
        assert res.success is False
        assert "timed out" in res.error.lower()

    def test_execute_script_with_dynamically_named_chart(self, tmp_path):
        script = tmp_path / "dynamic_plot.py"
        # Script saves to a custom named chart in its directory
        custom_chart = tmp_path / "CUPID_NS_1y.png"
        script.write_text(f"""
from pathlib import Path
Path(r"{custom_chart}").write_text("dummy png content")
print("Saved to custom chart")
""")
        res = execute_script(script, timeout_seconds=10)
        assert res.success is True
        assert res.chart_path is not None
        assert Path(res.chart_path).exists()


"""Tests for server.py FastMCP tools, file handling, error handling, and subprocess execution."""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from server import analyze_stock, save_code, run_code_and_show_plot, list_saved_analyses
from utils.files import ensure_outputs_dir


class TestServerAnalyzeStock:
    @pytest.mark.anyio
    @patch("server.run_financial_analysis")
    async def test_analyze_stock_success(self, mock_run):
        mock_run.return_value = """```python
import yfinance as yf
import matplotlib.pyplot as plt

df = yf.download('TSLA', period='ytd')
plt.plot(df['Close'])
plt.savefig('outputs/tsla.png')
```"""
        raw_res = await analyze_stock("Plot TSLA YTD")
        res = json.loads(raw_res)

        assert res["success"] is True
        assert "import yfinance as yf" in res["data"]
        assert "```" not in res["data"]

    @pytest.mark.anyio
    @patch("server.run_financial_analysis")
    async def test_analyze_stock_ollama_offline_error(self, mock_run):
        mock_run.side_effect = Exception("Connection refused to http://localhost:11434")
        raw_res = await analyze_stock("Plot TSLA YTD")
        res = json.loads(raw_res)

        assert res["success"] is False
        assert "Could not connect to local Ollama LLM server" in res["error"]

    @pytest.mark.anyio
    @patch("server.run_financial_analysis")
    async def test_analyze_stock_syntax_failure(self, mock_run):
        mock_run.return_value = "def broken(\n return"
        raw_res = await analyze_stock("broken code query")
        res = json.loads(raw_res)

        assert res["success"] is False
        assert "syntax validation" in res["message"].lower()

    @pytest.mark.anyio
    @patch("server.run_financial_analysis")
    async def test_analyze_stock_bad_ticker_error(self, mock_run):
        mock_run.side_effect = RuntimeError("No price data found for ticker INVALID123")
        raw_res = await analyze_stock("Plot INVALID123 stock")
        res = json.loads(raw_res)

        assert res["success"] is False
        assert "INVALID123" in res["error"]


class TestServerSaveCode:
    def test_save_code_valid(self, tmp_path, monkeypatch):
        monkeypatch.setattr("server.ensure_outputs_dir", lambda: tmp_path)

        code = "import yfinance as yf\nprint('valid')"
        raw_res = save_code(code, filename="custom_test.py")
        res = json.loads(raw_res)

        assert res["success"] is True
        saved_file = Path(res["data"]["script_path"])
        assert saved_file.exists()
        assert saved_file.name == "custom_test.py"
        assert "import yfinance as yf" in saved_file.read_text(encoding="utf-8")

    def test_save_code_rejects_syntax_error(self, tmp_path, monkeypatch):
        monkeypatch.setattr("server.ensure_outputs_dir", lambda: tmp_path)

        code = "def foo(\n return"
        raw_res = save_code(code)
        res = json.loads(raw_res)

        assert res["success"] is False
        assert "syntax validation failed" in res["message"].lower()
        assert not list(tmp_path.glob("*.py"))

    def test_save_code_consecutive_queries_produce_separate_files(self, tmp_path, monkeypatch):
        """T5.6 — Test: two consecutive queries produce two separate files."""
        monkeypatch.setattr("server.ensure_outputs_dir", lambda: tmp_path)

        code1 = "import yfinance as yf\n# Query 1\ndf = yf.download('AAPL')"
        code2 = "import yfinance as yf\n# Query 2\ndf = yf.download('TSLA')"

        # Give unique filenames or let generator create unique timestamped names
        res1 = json.loads(save_code(code1, filename="AAPL_1y.py"))
        res2 = json.loads(save_code(code2, filename="TSLA_ytd.py"))

        assert res1["success"] is True
        assert res2["success"] is True

        f1 = Path(res1["data"]["script_path"])
        f2 = Path(res2["data"]["script_path"])

        assert f1.exists()
        assert f2.exists()
        assert f1 != f2
        assert "AAPL" in f1.read_text()
        assert "TSLA" in f2.read_text()


class TestServerRunCodeAndShowPlot:
    @pytest.mark.anyio
    async def test_run_code_no_script_found(self, monkeypatch):
        monkeypatch.setattr("server.get_latest_saved_script", lambda: None)
        raw_res = await run_code_and_show_plot()
        res = json.loads(raw_res)

        assert res["success"] is False
        assert "No saved analysis script found" in res["message"]

    @pytest.mark.anyio
    async def test_run_code_successful_execution(self, tmp_path, monkeypatch):
        script = tmp_path / "test_exec.py"
        script.write_text("print('Executing analysis')")
        chart = tmp_path / "test_exec.png"
        chart.write_bytes(b"FAKE_PNG_CONTENT")

        raw_res = await run_code_and_show_plot(str(script))
        res = json.loads(raw_res)

        assert res["success"] is True
        assert "Script executed successfully" in res["message"]
        assert "Executing analysis" in res["data"]["stdout"]
        assert res["data"]["chart_path"] is not None


class TestServerListSavedAnalyses:
    def test_list_saved_analyses_tool(self, tmp_path, monkeypatch):
        monkeypatch.setattr("server.get_all_saved_analyses", lambda: [
            {"script_name": "TSLA_ytd.py", "has_chart": True}
        ])

        raw_res = list_saved_analyses()
        res = json.loads(raw_res)

        assert res["success"] is True
        assert len(res["data"]) == 1
        assert res["data"][0]["script_name"] == "TSLA_ytd.py"

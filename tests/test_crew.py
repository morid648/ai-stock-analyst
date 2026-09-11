"""Tests for finance_crew.py orchestration, bounded retry, and sanitization."""

import pytest
from unittest.mock import MagicMock, patch
from finance_crew import create_financial_crew, run_financial_analysis, QueryAnalysisOutput


class TestFinanceCrew:
    def test_create_financial_crew_structure(self):
        crew = create_financial_crew()
        assert len(crew.agents) == 3
        assert len(crew.tasks) == 3
        role_names = [a.role for a in crew.agents]
        assert "Stock Data Analyst" in role_names
        assert "Senior Python Developer" in role_names
        assert "Senior Code Execution Expert" in role_names

    def test_query_analysis_output_model(self):
        output = QueryAnalysisOutput(
            symbols=["TSLA", "AAPL"],
            timeframe="1y",
            action="compare"
        )
        assert output.symbols == ["TSLA", "AAPL"]
        assert output.timeframe == "1y"
        assert output.action == "compare"

    @patch("finance_crew.create_financial_crew")
    def test_run_financial_analysis_success_with_thinking_and_fences(self, mock_create):
        mock_crew = MagicMock()
        mock_result = MagicMock()
        mock_result.raw = """<think>
Need to plot TSLA YTD.
</think>
```python
import yfinance as yf
import matplotlib.pyplot as plt

df = yf.download('TSLA', period='ytd')
plt.figure()
plt.plot(df['Close'])
plt.savefig('outputs/tsla.png')
```"""
        mock_crew.kickoff.return_value = mock_result
        mock_create.return_value = mock_crew

        code = run_financial_analysis("Plot YTD stock gain of Tesla", max_retries=3)
        assert "<think>" not in code
        assert "```" not in code
        assert "import yfinance as yf" in code
        assert "plt.savefig" in code
        assert mock_crew.kickoff.call_count == 1

    @patch("finance_crew.create_financial_crew")
    def test_run_financial_analysis_bounded_retry_exhausted(self, mock_create):
        mock_crew = MagicMock()
        mock_result = MagicMock()
        # Invalid python syntax (unclosed paren)
        mock_result.raw = "def broken(\n  return"
        mock_crew.kickoff.return_value = mock_result
        mock_create.return_value = mock_crew

        with pytest.raises(RuntimeError) as exc_info:
            run_financial_analysis("Invalid query test", max_retries=3)

        assert "Failed to generate valid Python script after 3 attempts" in str(exc_info.value)
        assert mock_crew.kickoff.call_count == 3

    @pytest.mark.anyio
    @patch("finance_crew.create_financial_crew")
    async def test_run_financial_analysis_inside_active_event_loop(self, mock_create):
        """Verifies that calling run_financial_analysis from inside an active asyncio event loop works without error."""
        mock_crew = MagicMock()
        mock_result = MagicMock()
        mock_result.raw = "import yfinance as yf\nprint('inside event loop')"
        mock_crew.kickoff.return_value = mock_result
        mock_create.return_value = mock_crew

        code = run_financial_analysis("Plot stock", max_retries=1)
        assert "print('inside event loop')" in code
        assert mock_crew.kickoff.call_count == 1

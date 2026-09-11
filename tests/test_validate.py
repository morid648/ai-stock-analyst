"""Unit tests for utils/validate.py."""

import pytest
from utils.validate import validate_python_code


class TestValidatePythonCode:
    def test_valid_code(self):
        code = "import yfinance as yf\ndata = yf.download('TSLA')\nprint(data)"
        is_valid, err = validate_python_code(code)
        assert is_valid is True
        assert err is None

    def test_syntax_error(self):
        code = "def foo(\n  return 42"
        is_valid, err = validate_python_code(code)
        assert is_valid is False
        assert "SyntaxError" in err

    def test_nested_fstring_quote_error_simulation(self):
        # In Python <3.12 this was syntax error; in any Python, mismatched quotes fail:
        code = 'f"hello {config["timeframe"]}'  # unclosed or mismatched
        is_valid, err = validate_python_code(code)
        assert is_valid is False
        assert "SyntaxError" in err

    def test_empty_string(self):
        is_valid, err = validate_python_code("")
        assert is_valid is False
        assert "empty" in err.lower()

    def test_whitespace_only(self):
        is_valid, err = validate_python_code("   \n\t  ")
        assert is_valid is False
        assert "empty" in err.lower()

    def test_none_input(self):
        is_valid, err = validate_python_code(None)
        assert is_valid is False
        assert "empty" in err.lower()

    def test_valid_with_comments_and_functions(self):
        code = """
# Calculate moving average
import yfinance as yf
import matplotlib.pyplot as plt

def plot_stock(ticker: str):
    df = yf.download(ticker, period="1y")
    plt.plot(df['Close'])
    plt.savefig('output.png')
"""
        is_valid, err = validate_python_code(code)
        assert is_valid is True
        assert err is None

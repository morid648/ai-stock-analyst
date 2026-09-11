"""Unit tests for utils/sanitize.py."""

import pytest
from utils.sanitize import sanitize_llm_output, strip_thinking_tags, extract_code_block


class TestStripThinkingTags:
    def test_strip_single_complete_tag(self):
        text = "<think>Let me plan this.\nI should import yf.</think>import yfinance as yf"
        assert strip_thinking_tags(text) == "import yfinance as yf"

    def test_strip_case_insensitive_tag(self):
        text = "<THINK>Thinking...</THINK>code"
        assert strip_thinking_tags(text) == "code"

    def test_strip_multiple_thinking_tags(self):
        text = "<think>First thought</think>part1\n<think>Second thought</think>part2"
        assert strip_thinking_tags(text) == "part1\npart2"

    def test_unclosed_thinking_tag(self):
        text = "code before<think>Unclosed thinking..."
        assert strip_thinking_tags(text) == "code before"

    def test_empty_input(self):
        assert strip_thinking_tags("") == ""
        assert strip_thinking_tags(None) == ""


class TestExtractCodeBlock:
    def test_python_fenced_code(self):
        text = "```python\nimport yfinance as yf\nprint(1)\n```"
        assert extract_code_block(text) == "import yfinance as yf\nprint(1)"

    def test_generic_fenced_code(self):
        text = "```\nimport yfinance as yf\n```"
        assert extract_code_block(text) == "import yfinance as yf"

    def test_surrounding_commentary(self):
        text = "Here is the code:\n```python\nimport yfinance as yf\n```\nEnjoy!"
        assert extract_code_block(text) == "import yfinance as yf"

    def test_no_fences(self):
        text = "import yfinance as yf\nprint('hello')"
        assert extract_code_block(text) == text

    def test_empty_string(self):
        assert extract_code_block("") == ""


class TestSanitizeLlmOutput:
    def test_full_deepseek_r1_sample(self):
        raw_output = """<think>
The user wants to plot Tesla YTD gain.
I should import yfinance as yf and matplotlib.pyplot as plt.
Then calculate YTD return and plot it.
</think>
Here is the complete script:
```python
import yfinance as yf
import matplotlib.pyplot as plt

data = yf.download('TSLA', period='ytd')
plt.figure()
plt.plot(data['Close'])
plt.title('TSLA YTD')
plt.savefig('outputs/tsla.png')
```
Let me know if you need anything else!"""

        expected = """import yfinance as yf
import matplotlib.pyplot as plt

data = yf.download('TSLA', period='ytd')
plt.figure()
plt.plot(data['Close'])
plt.title('TSLA YTD')
plt.savefig('outputs/tsla.png')"""
        assert sanitize_llm_output(raw_output) == expected

    def test_no_think_only_fences(self):
        raw = "```python\nx = 1\n```"
        assert sanitize_llm_output(raw) == "x = 1"

    def test_already_clean_code(self):
        raw = "import yfinance as yf\ndata = yf.Ticker('AAPL')"
        assert sanitize_llm_output(raw) == raw

    def test_empty_or_none(self):
        assert sanitize_llm_output("") == ""
        assert sanitize_llm_output(None) == ""


class TestSanitizeYfinanceParams:
    def test_strips_group_by_ticker(self):
        from utils.sanitize import sanitize_yfinance_params
        code = "data = yf.download(tickers=symbols, period='1y', group_by='ticker', progress=False)"
        clean = sanitize_yfinance_params(code)
        assert "group_by" not in clean
        assert "progress=False" in clean

    def test_strips_group_by_with_double_quotes(self):
        from utils.sanitize import sanitize_yfinance_params
        code = 'data = yf.download(tickers=symbols, group_by="ticker")'
        clean = sanitize_yfinance_params(code)
        assert "group_by" not in clean

    def test_preserves_code_without_group_by(self):
        from utils.sanitize import sanitize_yfinance_params
        code = "data = yf.download(tickers=symbols, period='1y', progress=False)"
        assert sanitize_yfinance_params(code) == code


class TestSanitizeImports:
    def test_fixes_matplotlib_pyplot_pyplot(self):
        from utils.sanitize import sanitize_imports
        code = "import matplotlib.pyplot.pyplot as plt\nplt.figure()"
        assert sanitize_imports(code) == "import matplotlib.pyplot as plt\nplt.figure()"

    def test_fixes_from_matplotlib_pyplot(self):
        from utils.sanitize import sanitize_imports
        code = "from matplotlib.pyplot import pyplot as plt"
        assert sanitize_imports(code) == "import matplotlib.pyplot as plt"

    def test_sanitize_llm_output_integration(self):
        raw = "```python\nimport matplotlib.pyplot.pyplot as plt\nimport yfinance as yf\n```"
        clean = sanitize_llm_output(raw)
        assert "import matplotlib.pyplot as plt" in clean
        assert "pyplot.pyplot" not in clean



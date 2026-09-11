"""Sanitization utilities for LLM output."""

import re


def strip_thinking_tags(text: str) -> str:
    """Strips <think>...</think> blocks from DeepSeek-R1 and similar reasoning models.
    
    Handles multi-line thinking blocks, multiple blocks, and unclosed thinking tags.
    """
    if not text:
        return ""
    # Remove complete <think>...</think> blocks
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # If an unclosed <think> tag exists (e.g. truncated output), remove everything after <think>
    cleaned = re.sub(r"<think>.*$", "", cleaned, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()


def extract_code_block(text: str) -> str:
    """Extracts Python code from markdown code fences if present.
    
    If ```python ... ``` or ``` ... ``` blocks are found, extracts the inner code.
    If multiple code blocks are found, prefers the python block or joins them.
    If no fences are found, returns the cleaned text.
    """
    if not text:
        return ""

    # Look for fenced code blocks, e.g. ```python ... ``` or ``` ... ```
    # Support 3 or more backticks
    pattern = r"```(?:python|py)?\s*\n?(.*?)```"
    matches = re.findall(pattern, text, flags=re.DOTALL | re.IGNORECASE)
    if matches:
        # Return the first non-empty code block stripped of outer whitespace
        for block in matches:
            trimmed = block.strip()
            if trimmed:
                return trimmed

    # If an unclosed code block begins (e.g. ```python at the start without closing)
    unclosed_match = re.search(r"^```(?:python|py)?\s*\n?(.*)$", text, flags=re.DOTALL | re.IGNORECASE)
    if unclosed_match:
        return unclosed_match.group(1).strip()

    return text.strip()


def sanitize_yfinance_params(code: str) -> str:
    """Removes problematic group_by parameter from yfinance calls.
    
    In modern yfinance (0.2.x+), group_by='ticker' inverts MultiIndex column levels
    and causes KeyError: 'Close' when accessing df['Close'].
    """
    if not code:
        return ""
    # Strip any group_by parameter (e.g. group_by='ticker', group_by="ticker", etc.)
    code = re.sub(r",\s*group_by\s*=\s*['\"][^'\"]*['\"]", "", code)
    code = re.sub(r"group_by\s*=\s*['\"][^'\"]*['\"]\s*,?", "", code)
    return code


def sanitize_imports(code: str) -> str:
    """Corrects common LLM hallucinated import statements (e.g. matplotlib.pyplot.pyplot)."""
    if not code:
        return ""
    # Fix repeated submodules like matplotlib.pyplot.pyplot
    code = re.sub(r"\bimport\s+matplotlib\.pyplot\.pyplot\b", "import matplotlib.pyplot", code)
    code = re.sub(r"\bfrom\s+matplotlib\.pyplot\s+import\s+pyplot\b", "import matplotlib.pyplot", code)
    code = re.sub(r"\bimport\s+yfinance\.yfinance\b", "import yfinance", code)
    code = re.sub(r"\bimport\s+pandas\.pandas\b", "import pandas", code)
    return code


def sanitize_llm_output(output: str) -> str:
    """Sanitizes raw LLM output into clean, executable Python code.
    
    1. Removes <think>...</think> reasoning blocks.
    2. Extracts code from markdown code fences (```python ... ```).
    3. Cleans problematic yfinance parameters (group_by='ticker').
    4. Corrects common hallucinated imports (e.g. matplotlib.pyplot.pyplot).
    5. Strips extraneous leading/trailing whitespace.
    """
    if not output or not isinstance(output, str):
        return ""
    
    # Step 1: Strip thinking blocks
    cleaned = strip_thinking_tags(output)
    
    # Step 2: Extract code block if markdown fences are present
    cleaned = extract_code_block(cleaned)

    # Step 3: Remove incompatible yfinance parameters
    cleaned = sanitize_yfinance_params(cleaned)

    # Step 4: Correct hallucinated imports
    cleaned = sanitize_imports(cleaned)
    
    # Step 5: Final trim
    return cleaned.strip()

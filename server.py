"""FastMCP server exposing AI Financial Analyst tools."""

from utils.env_setup import configure_utf8

configure_utf8()

import asyncio
import json
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

from finance_crew import run_financial_analysis
from utils.sanitize import sanitize_llm_output
from utils.validate import validate_python_code
from utils.files import (
    ensure_outputs_dir,
    generate_filename,
    get_associated_chart_path,
    get_latest_saved_script,
    list_saved_analyses as get_all_saved_analyses,
    DEFAULT_OUTPUTS_DIR,
)
from utils.executor import execute_script
from utils.types import ToolResponse
from utils.logging_config import setup_logger

logger = setup_logger("mcp_server")

# Create FastMCP instance
mcp = FastMCP("financial-analyst")


@mcp.tool()
async def analyze_stock(query: str) -> str:
    """Analyzes stock market data based on natural language query and generates executable Python code.

    The query can contain one or more stock symbols (e.g. TSLA, AAPL, NVDA), a timeframe 
    (e.g., 1d, 1mo, 1y, ytd), and an action (e.g., plot, compare, analyze volume).

    Example queries:
    - "Show me Tesla's stock performance over the last 3 months"
    - "Compare Apple and Microsoft stocks for the past year"
    - "Analyze the trading volume of Amazon stock for the last month"

    Args:
        query: Free-text financial query in natural language.

    Returns:
        JSON string with 'success', 'message', and 'data' containing the sanitized Python code.
    """
    logger.info(f"Received analyze_stock query: '{query}'")
    try:
        raw_code = await asyncio.to_thread(run_financial_analysis, query)
        cleaned_code = sanitize_llm_output(raw_code)

        # Syntax check defense-in-depth
        is_valid, error_msg = validate_python_code(cleaned_code)
        if not is_valid:
            resp = ToolResponse(
                success=False,
                message="Generated code failed syntax validation.",
                error=error_msg,
                data=cleaned_code,
            )
            return json.dumps(resp.to_dict(), indent=2)

        resp = ToolResponse(
            success=True,
            message="Analysis code successfully generated and validated.",
            data=cleaned_code,
        )
        return json.dumps(resp.to_dict(), indent=2)

    except Exception as e:
        logger.error(f"analyze_stock failed: {str(e)}")
        # Check for common issues like Ollama connection failure
        err_str = str(e)
        if "Connection refused" in err_str or "11434" in err_str:
            friendly_err = (
                "Could not connect to local Ollama LLM server at localhost:11434. "
                "Ensure Ollama is running ('ollama serve') and model 'deepseek-r1:7b' is pulled."
            )
        else:
            friendly_err = err_str

        resp = ToolResponse(
            success=False,
            message="Failed to analyze stock query.",
            error=friendly_err,
        )
        return json.dumps(resp.to_dict(), indent=2)


@mcp.tool()
def save_code(code: str, filename: Optional[str] = None) -> str:
    """Validates and persists the generated Python analysis script to the outputs/ directory.

    Performs AST syntax validation before writing to disk. If no filename is provided,
    generates a unique timestamped filename.

    Args:
        code: Clean, executable Python code string.
        filename: Optional custom filename (e.g., 'TSLA_ytd.py'). If omitted, a timestamped name is used.

    Returns:
        JSON string with 'success', 'message', and 'data' containing the saved file path.
    """
    logger.info("Received save_code request")
    try:
        # Sanitize any stray markdown fences or thoughts
        cleaned_code = sanitize_llm_output(code)

        # Validate syntax via ast.parse
        is_valid, error_msg = validate_python_code(cleaned_code)
        if not is_valid:
            resp = ToolResponse(
                success=False,
                message="Cannot save code: syntax validation failed.",
                error=error_msg,
            )
            return json.dumps(resp.to_dict(), indent=2)

        out_dir = ensure_outputs_dir()

        if filename:
            file_path = out_dir / (filename if filename.endswith(".py") else f"{filename}.py")
        else:
            gen_name = generate_filename("ANALYSIS", timeframe="query", extension="py")
            file_path = out_dir / gen_name

        # Ensure the script outputs the chart to the matching .png path if savefig is used
        chart_path = get_associated_chart_path(file_path)
        # If the code saves to a generic filename, we can adapt it or write as-is
        file_path.write_text(cleaned_code, encoding="utf-8")
        logger.info(f"Code saved successfully to {file_path}")

        resp = ToolResponse(
            success=True,
            message=f"Code successfully validated and saved to {file_path.name}",
            data={
                "script_path": str(file_path.resolve()),
                "chart_path": str(chart_path.resolve()),
            },
        )
        return json.dumps(resp.to_dict(), indent=2)

    except Exception as e:
        logger.error(f"save_code failed: {str(e)}")
        resp = ToolResponse(
            success=False,
            message="Failed to save code.",
            error=str(e),
        )
        return json.dumps(resp.to_dict(), indent=2)


@mcp.tool()
async def run_code_and_show_plot(script_path: Optional[str] = None) -> str:
    """Executes a saved Python analysis script in an isolated subprocess with timeout and safety guarantees.

    Captures stdout, stderr, and verifies the generated chart image file (.png).

    Args:
        script_path: Optional path to the script to execute. If omitted, the most recently saved script in outputs/ is used.

    Returns:
        JSON string with execution details, stdout, stderr, and chart image path.
    """
    logger.info(f"Received run_code_and_show_plot request (target: {script_path or 'latest'})")
    try:
        if not script_path:
            latest = get_latest_saved_script()
            if not latest:
                resp = ToolResponse(
                    success=False,
                    message="No saved analysis script found in outputs/ directory.",
                    error="Run analyze_stock and save_code before executing.",
                )
                return json.dumps(resp.to_dict(), indent=2)
            target = latest
        else:
            target = Path(script_path)

        exec_res = await asyncio.to_thread(execute_script, target, timeout_seconds=30)
        if exec_res.success:
            chart_status = f" Chart generated: {exec_res.chart_path}" if exec_res.chart_path else " (No chart file generated)"
            resp = ToolResponse(
                success=True,
                message=f"Script executed successfully.{chart_status}",
                data=exec_res.model_dump(),
            )
        else:
            resp = ToolResponse(
                success=False,
                message="Script execution failed.",
                error=exec_res.error,
                data=exec_res.model_dump(),
            )

        return json.dumps(resp.to_dict(), indent=2)

    except Exception as e:
        logger.error(f"run_code_and_show_plot failed: {str(e)}")
        resp = ToolResponse(
            success=False,
            message="Unexpected error executing script.",
            error=str(e),
        )
        return json.dumps(resp.to_dict(), indent=2)


@mcp.tool()
def list_saved_analyses() -> str:
    """Lists all saved Python analysis scripts and charts in the outputs/ directory.

    Returns:
        JSON string listing saved scripts, generated chart status, modified timestamps, and file sizes.
    """
    try:
        analyses = get_all_saved_analyses()
        resp = ToolResponse(
            success=True,
            message=f"Found {len(analyses)} saved analyses.",
            data=analyses,
        )
        return json.dumps(resp.to_dict(), indent=2)
    except Exception as e:
        logger.error(f"list_saved_analyses failed: {str(e)}")
        resp = ToolResponse(
            success=False,
            message="Failed to list saved analyses.",
            error=str(e),
        )
        return json.dumps(resp.to_dict(), indent=2)


# Run the server locally over stdio transport
if __name__ == "__main__":
    mcp.run(transport="stdio")
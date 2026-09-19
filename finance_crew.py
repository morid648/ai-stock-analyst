"""Multi-agent financial analysis crew built with CrewAI."""

from utils.env_setup import configure_utf8

configure_utf8()

import re
import asyncio
import concurrent.futures
from pathlib import Path
from typing import Optional, List, Any
from pydantic import BaseModel, Field
from crewai import Agent, Task, Crew, Process
from dotenv import load_dotenv

from utils.llm import get_llm
from utils.sanitize import sanitize_llm_output
from utils.validate import validate_python_code
from utils.logging_config import setup_logger

PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")
logger = setup_logger("finance_crew")


class QueryAnalysisOutput(BaseModel):
    """Structured output for the query analysis task."""
    symbols: List[str] = Field(..., description="List of stock ticker symbols (e.g., ['TSLA', 'AAPL']).")
    timeframe: str = Field(..., description="Time period (e.g., '1d', '1mo', '1y', 'ytd', 'max').")
    action: str = Field(..., description="Action to be performed (e.g., 'plot', 'compare', 'analyze_volume').")


def create_financial_crew(llm=None) -> Crew:
    """Factory to construct the financial analysis crew with configured agents and tasks."""
    if llm is None:
        llm = get_llm()

    # 1) Query parser agent
    query_parser_agent = Agent(
        role="Stock Data Analyst",
        goal="Extract stock details, ticker symbols, timeframe, and user action from this user query: {query}.",
        backstory="""You are a financial analyst specializing in stock market data retrieval. 
                     You convert company names (e.g. Tesla -> TSLA, Apple -> AAPL) to official exchange ticker symbols.""",
        llm=llm,
        verbose=True,
    )

    query_parsing_task = Task(
        description="""Analyze the user query: '{query}'.
                       Extract stock details and output a structured format containing:
                       - symbols: list of ticker symbols (e.g. ['TSLA'])
                       - timeframe: yfinance valid interval/period (e.g. 'ytd', '1mo', '1y')
                       - action: action to be taken (e.g. 'plot', 'compare', 'analyze_volume').""",
        expected_output="A structured QueryAnalysisOutput with symbols, timeframe, and action.",
        output_pydantic=QueryAnalysisOutput,
        agent=query_parser_agent,
    )

    # 2) Code writer agent
    code_writer_agent = Agent(
        role="Senior Python Developer",
        goal="Write robust, executable Python code to fetch and visualize stock data using yfinance and matplotlib.",
        backstory="""You are a Senior Python developer specializing in stock market data visualization. 
                     You are a Pandas, Matplotlib, and yfinance library expert.
                     You strictly write clean, production-ready Python scripts.
                     CRITICAL RULES:
                     - Always 'import yfinance as yf' and use 'yf.download()' or 'yf.Ticker()' — NEVER use 'yfinance.download()'.
                     - NEVER use group_by='ticker' in yf.download() as it causes KeyError: 'Close' in modern pandas/yfinance. Call yf.download(tickers=symbols, period=period, progress=False).
                     - Access closing prices directly with data['Close'] (which returns closing prices for plotting).
                     - Always 'import matplotlib.pyplot as plt' (EXACTLY this import, NEVER 'matplotlib.pyplot.pyplot').
                     - Always save the figure to disk using 'plt.savefig(...)' before or instead of calling 'plt.show()'.
                     - Never use nested quotes inside f-strings that cause syntax errors in Python (e.g. avoid f'...{dict["key"]}').
                     - Output only valid Python code.""",
        llm=llm,
        verbose=True,
    )

    code_writer_task = Task(
        description="""Based on the structured outputs from the stock data analyst (symbols, timeframe, action):
                       Write a complete, self-contained, executable Python script to download data and plot the visualization.
                       
                       Requirements:
                       1. 'import yfinance as yf' and 'import matplotlib.pyplot as plt'.
                       2. Use 'yf.download()' to retrieve historical prices without 'group_by'.
                       3. Access prices via data['Close'] and plot against data.index.
                       4. Must save the output chart using 'plt.savefig(...)'.
                       5. Ensure all syntax is valid Python with no nested quoting errors.
                       6. Do not include markdown commentary or code block markers if possible, just the executable code.""",
        expected_output="A clean and executable Python script file (.py) for stock visualization.",
        agent=code_writer_agent,
    )

    # 3) Code execution agent
    code_execution_agent = Agent(
        role="Senior Code Execution Expert",
        goal="Review and verify the generated Python code for stock data visualization, fixing any syntax or runtime errors.",
        backstory="""You are a code execution expert. You inspect and verify Python scripts for syntax, 
                     import correctness, and proper matplotlib file saving.""",
        allow_code_execution=True,
        allow_delegation=True,
        llm=llm,
        verbose=True,
    )

    code_execution_task = Task(
        description="""Review the generated Python code from the code writer agent.
                       Verify that 'import yfinance as yf' is used, 'yf.download()' is used without 'group_by', data['Close'] is used, and 'plt.savefig()' is included.
                       Ensure the code is free of syntax errors and ready for execution.""",
        expected_output="A clean, working and executable Python script file (.py) for stock visualization.",
        agent=code_execution_agent,
    )

    crew = Crew(
        agents=[query_parser_agent, code_writer_agent, code_execution_agent],
        tasks=[query_parsing_task, code_writer_task, code_execution_task],
        process=Process.sequential,
        verbose=True,
    )
    return crew


def kickoff_crew_safely(crew: Crew, inputs: dict) -> Any:
    """Kicks off a CrewAI crew safely, isolating execution from any running event loop.

    CrewAI's agent_executor raises RuntimeError if invoked synchronously from within
    a running event loop (e.g. FastMCP or an async server). Running kickoff in a worker
    thread ensures agent execution runs without an active event loop on that thread.
    """
    try:
        asyncio.get_running_loop()
        in_event_loop = True
    except RuntimeError:
        in_event_loop = False

    if in_event_loop:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(crew.kickoff, inputs=inputs).result()
    return crew.kickoff(inputs=inputs)


def run_financial_analysis(query: str, max_retries: int = 3) -> str:
    """Orchestrates the CrewAI pipeline to generate sanitized, AST-validated financial analysis code.

    Args:
        query: Natural language query (e.g. 'Plot YTD stock gain of Tesla').
        max_retries: Maximum attempts to generate syntactically valid code (FR4).

    Returns:
        Clean, executable Python script as a string.

    Raises:
        RuntimeError: If code generation fails or remains invalid after max_retries.
    """
    logger.info(f"Initiating financial analysis for query: '{query}'")

    crew = create_financial_crew()
    attempts = 0
    last_error = None

    while attempts < max_retries:
        attempts += 1
        logger.info(f"Execution attempt {attempts}/{max_retries}")
        try:
            result = kickoff_crew_safely(crew, inputs={"query": query})
            raw_output = result.raw if hasattr(result, "raw") else str(result)
            
            # Step 1: Sanitize LLM output (strip <think> tags, code fences)
            cleaned_code = sanitize_llm_output(raw_output)
            
            # Step 2: Validate syntax using AST
            is_valid, error_msg = validate_python_code(cleaned_code)
            if is_valid:
                logger.info(f"Successfully generated valid Python code on attempt {attempts}.")
                return cleaned_code

            logger.warning(f"Attempt {attempts} produced invalid code: {error_msg}")
            last_error = error_msg

        except Exception as e:
            logger.error(f"Error during attempt {attempts}: {str(e)}")
            last_error = str(e)

    failure_msg = (
        f"Failed to generate valid Python script after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
    logger.error(failure_msg)
    raise RuntimeError(failure_msg)


if __name__ == "__main__":
    test_query = "Plot YTD stock gain of Tesla"
    try:
        code = run_financial_analysis(test_query)
        print("Generated Code:\n" + "=" * 40)
        print(code)
    except Exception as exc:
        print(f"Failed: {exc}")
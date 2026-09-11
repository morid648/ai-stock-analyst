# Product Requirements Document
## AI Financial Analyst Agent (Multi-Agent Stock Research & Visualization Tool)

**Author:** Anshul
**Version:** 1.0
**Status:** Draft — Build Spec
**Last Updated:** September 10, 2026

---

## 1. Overview

### 1.1 Problem Statement
Retrieving, analyzing, and visualizing stock market data today requires manually writing Python code, remembering library syntax (yfinance, matplotlib), and iterating on errors. There's no natural-language interface that goes from a plain English query ("show me Tesla's YTD performance") to a working, executable analysis script and rendered chart — locally, without depending on a paid LLM API.

### 1.2 Solution Summary
A multi-agent AI system, built on **CrewAI**, that takes a natural language financial query and autonomously:
1. Parses the query into structured parameters (ticker symbol(s), timeframe, action)
2. Writes Python code to fetch and visualize the requested stock data using `yfinance` + `matplotlib`
3. Reviews, executes, and self-corrects that code until it runs cleanly
4. Exposes the whole pipeline as a set of **MCP (Model Context Protocol) tools**, so it can be called from any MCP-compatible client (e.g., Claude Desktop, Claude Code) as a natural extension of chat

### 1.3 Goals
- Turn a single free-text prompt into a working, saved, executable `.py` script and a rendered plot
- Run entirely on a local, free, open-weight LLM (Ollama + DeepSeek-R1) — no per-call API cost
- Package the agent crew as reusable MCP tools rather than a one-off notebook script
- Demonstrate an end-to-end agentic AI architecture as a portfolio project (multi-agent orchestration + tool use + MCP server)

### 1.4 Non-Goals (v1)
- Real-time/streaming price data or trade execution
- Multi-user hosting / authentication
- Fundamental analysis (P/E, balance sheet parsing) — technical/price-chart analysis only
- Non-US-listed / non-Yahoo-Finance-covered tickers guaranteed to work (NSE/BSE tickers need `.NS`/`.BO` suffixes — flagged as a known limitation)
- A polished end-user UI (v1 is developer/CLI/MCP-client facing)

---

## 2. Users & Use Cases

### 2.1 Primary User
Anshul himself, and by extension anyone using an MCP-enabled AI client (Claude Desktop/Code) who wants ad hoc stock charts without leaving the chat interface.

### 2.2 Core Use Cases
| # | User says | System does |
|---|---|---|
| 1 | "Plot YTD stock gain of Tesla" | Generates and executes a script plotting TSLA YTD price series |
| 2 | "Compare Apple and Microsoft stocks for the past year" | Generates a multi-ticker comparison chart (AAPL vs MSFT, 1y) |
| 3 | "Analyze the trading volume of Amazon stock for the last month" | Generates a volume bar/line chart for AMZN, 1mo |
| 4 | "Show me Reliance's 6-month performance" | Should resolve to `RELIANCE.NS`; flagged as a stretch goal (see §7) |

---

## 3. Current State (What Exists Today — from uploaded code)

You already have a working prototype across three files. This PRD formalizes and hardens it:

- **`building-financial-analyst.ipynb`** — exploratory notebook where the 3-agent CrewAI pipeline (query parser → code writer → code executor) was first prototyped against a local `ollama/deepseek-r1:7b` model.
- **`finance_crew.py`** — the productionized version of the same pipeline: adds `.env` loading, upgrades `symbol: str` to `symbols: list[str]` (multi-ticker support), enables `allow_delegation=True` on the execution agent so it can hand fixes back to the code writer, and exposes `run_financial_analysis(query)` as an importable function.
- **`server.py`** — wraps `finance_crew.py` in a **FastMCP** server exposing three tools: `analyze_stock(query)`, `save_code(code)`, and `run_code_and_show_plot()`, run over stdio transport.

**Known issues in the current prototype (to fix in this build):**
1. `code_execution_agent` has `allow_code_execution=True` (auto-adds `CodeInterpreterTool`) **and** a separately instantiated but unused `code_interpreter_tool` — dead code to remove.
2. The DeepSeek-R1 model emits `<think>...</think>` reasoning blocks and markdown code fences in its final answer; nothing currently strips these before the code is treated as "clean, executable Python" — this caused the sample notebook run to output a broken script (used `yfinance.download` instead of the imported `yf.download`, and an unescaped nested f-string quote `f'... - {config['timeframe']}'` which is a `SyntaxError` in Python <3.12).
3. `run_code_and_show_plot()` uses a raw `exec()` on file contents with no sandboxing, timeout, or error capture — a correctness and safety gap.
4. No automated tests, no logging of intermediate agent outputs, no retry limit (an execution agent stuck in a delegation loop could run indefinitely).
5. `save_code` always writes to the same fixed filename `stock_analysis.py`, so concurrent/repeated queries overwrite each other with no history.

---

## 4. Proposed Architecture

### 4.1 High-Level Flow
```
User query (natural language)
        │
        ▼
[MCP Client: Claude Desktop / Claude Code]
        │  calls tool: analyze_stock(query)
        ▼
[server.py — FastMCP server, stdio transport]
        │
        ▼
[finance_crew.py — CrewAI Sequential Process]
        │
  ┌─────┴──────────────────────────────┐
  │ Agent 1: Stock Data Analyst         │  → structured output (Pydantic): symbols[], timeframe, action
  │ Agent 2: Senior Python Developer     │  → draft .py script (yfinance + matplotlib)
  │ Agent 3: Code Execution Expert       │  → executes, catches errors, delegates fixes back to Agent 2, retries
  └─────┬──────────────────────────────┘
        │  cleaned Python code (string)
        ▼
[server.py: save_code(code)]  → writes to /outputs/{symbol}_{timestamp}.py
        │
        ▼
[server.py: run_code_and_show_plot()]  → sandboxed execution → saves chart PNG + returns path
        │
        ▼
Response returned to MCP client → chart shown / script shared with user
```

### 4.2 Agents (CrewAI)
| Agent | Role | Input | Output | Notes |
|---|---|---|---|---|
| Query Parser | Stock Data Analyst | Raw NL query | `QueryAnalysisOutput` (Pydantic: `symbols: list[str]`, `timeframe: str`, `action: str`) | Add ticker-symbol validation/normalization step |
| Code Writer | Senior Python Developer | Parsed query object | Draft Python script string | Must target `yf.download`/`yf.Ticker`, matplotlib, save fig to file (not just `plt.show()`) |
| Code Executor | Senior Code Execution Expert | Draft script | Working script + execution result | Runs in sandbox, has bounded retry/delegation loop back to Code Writer |

### 4.3 LLM
- **Primary:** local `ollama/deepseek-r1:7b` via Ollama (`base_url=http://localhost:11434`) — zero API cost, fully offline capable
- **Fallback (already stubbed in code, commented out):** `openai/gpt-4o` — enable via env var switch (`LLM_PROVIDER=ollama|openai`) for cases where local model quality is insufficient (e.g., complex multi-ticker comparisons)
- Add a **post-processing / output-cleaning layer** to strip `<think>...</think>` blocks and markdown code fences from DeepSeek-R1 output before it's treated as final code — this is the single highest-priority fix.

### 4.4 Tools (MCP Server — `server.py`)
| Tool | Purpose | Changes needed |
|---|---|---|
| `analyze_stock(query: str) -> str` | Run the full crew, return cleaned Python code | Add output sanitization (strip `<think>` + code fences); add structured error return instead of bare string |
| `save_code(code: str) -> str` | Persist code to disk | Change to timestamped/ticker-based filenames under an `outputs/` folder; validate with `ast.parse()` before saving; return the file path |
| `run_code_and_show_plot() -> str` | Execute saved script, produce chart | Replace raw `exec()` with a subprocess call (`subprocess.run([...], timeout=30, capture_output=True)`) for isolation; capture stdout/stderr; return path to saved PNG instead of relying on `plt.show()` (which won't render inside an MCP tool call context) |
| *(new)* `list_saved_analyses() -> list[str]` | Browse past generated scripts/charts | New tool — nice-to-have for v1.1 |

### 4.5 Data Layer
- **Source:** `yfinance` (Yahoo Finance) — free, no API key, sufficient for daily/intraday OHLCV
- **Known limitation:** Yahoo Finance rate-limits aggressive polling; no caching layer exists yet (see §7 future work)

---

## 5. Functional Requirements

1. **FR1 — Query Parsing:** System must extract ticker symbol(s), a yfinance-valid timeframe (`1d, 5d, 1mo, 3mo, 6mo, 1y, ytd, max`, etc.), and an action (`plot`, `compare`, `analyze volume`) from free text, with graceful handling of ambiguous company names (e.g., "Tesla" → `TSLA`).
2. **FR2 — Multi-Ticker Support:** Must support 1–5 tickers in a single query (already partially supported via `symbols: list[str]` in `finance_crew.py`, not yet in the notebook version).
3. **FR3 — Code Generation:** Generated code must be syntactically valid Python (validated via `ast.parse` before save), must not use undefined names (fix the `yfinance.download` vs `yf.download` bug class), and must save the figure to disk (`plt.savefig(...)`) rather than only calling `plt.show()`.
4. **FR4 — Self-Correction Loop:** If execution fails, the Code Execution agent must delegate a fix back to the Code Writer agent, with a **maximum of 3 retry attempts** before returning a clear failure message to the user (currently unbounded — must be capped).
5. **FR5 — Output Sanitization:** All LLM output must be stripped of `<think>` reasoning tags and markdown fences before being treated as code or being saved.
6. **FR6 — File Management:** Saved scripts and charts must use unique, descriptive filenames (e.g., `TSLA_ytd_20260910_1432.py` / `.png`) written to a dedicated `outputs/` directory, never overwritten silently.
7. **FR7 — Safe Execution:** Code execution must run in an isolated subprocess with a timeout, not via in-process `exec()`.
8. **FR8 — MCP Exposure:** All three (four, with FR-new) tools must be discoverable and callable from an MCP client with clear docstrings/argument schemas (already mostly done — keep consistent).
9. **FR9 — Error Transparency:** Any failure (bad ticker, network error, execution error after max retries) must return a human-readable error string, not a raw stack trace or silent empty result.

---

## 6. Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Performance** | End-to-end query → chart should complete in under ~60 seconds on local hardware running a 7B model |
| **Cost** | $0 marginal cost per query using the local Ollama path |
| **Reliability** | Bounded retries (FR4); no infinite agent delegation loops |
| **Portability** | Should run on the developer's machine with just Ollama + a Python venv — documented setup steps in README |
| **Security** | No arbitrary code execution outside the sandboxed subprocess; no secrets in generated/saved files |
| **Observability** | `verbose=True` agent logs should be optionally redirected to a log file per run for debugging |

---

## 7. Future Work / Stretch Goals (post-v1)
- **NSE/BSE support:** auto-append `.NS`/`.BO` suffix for Indian tickers; useful given your finance/India focus and ITC valuation model background — natural extension of [[itc-valuation-model]] work
- **Caching layer:** local SQLite/parquet cache for repeated ticker+timeframe requests to reduce Yahoo Finance calls
- **Streamlit/web front-end** as an alternative to MCP-only access, for demoing to non-technical audiences (recruiters)
- **Fundamentals agent:** a fourth agent pulling P/E, EPS, market cap via `yfinance.Ticker().info` for lightweight fundamental context alongside the price chart
- **Swap-in cloud LLM benchmarking:** compare DeepSeek-R1 7B (local) vs GPT-4o (API) output quality/reliability on the same query set, and document findings — good portfolio talking point
- **`list_saved_analyses` MCP tool** for browsing history

---

## 8. Milestones / Build Plan

| Phase | Deliverable |
|---|---|
| **P1 — Harden core pipeline** | Fix output sanitization (strip `<think>`/fences), fix code-writer bugs (`yf.download`, f-string quoting), add `ast.parse` validation, add bounded retry (FR4) |
| **P2 — Safe execution** | Replace `exec()` with sandboxed subprocess + timeout; save figures to file instead of `plt.show()` |
| **P3 — File management** | Timestamped output filenames, dedicated `outputs/` folder, `.gitignore` for generated artifacts |
| **P4 — MCP polish** | Add `list_saved_analyses` tool, improve tool docstrings/examples, test end-to-end from Claude Desktop |
| **P5 — Documentation & repo packaging** | README with architecture diagram, setup steps (Ollama install, model pull, `.env`), example queries, known limitations — package as a GitHub repo consistent with your other portfolio projects |
| **P6 (stretch)** | NSE/BSE ticker support, caching, fundamentals agent |

---

## 9. Success Metrics
- ≥90% of well-formed single-ticker queries produce a working chart on first or retried attempt (within the 3-retry cap)
- Zero raw stack traces surfaced to the end user
- Full pipeline runs end-to-end via an MCP client call, not just a local script invocation
- Repo is portfolio-ready: README + architecture diagram + example run screenshots, consistent with your existing GitHub project presentation style

---

## 10. Open Questions
1. Should the system resolve company *names* ("Tesla") to tickers via the LLM alone, or should it validate against a known ticker list to avoid hallucinated symbols?
2. Should chart images be returned as base64/inline to the MCP client, or only as a file path (current design)?
3. Local model choice: is `deepseek-r1:7b` sufficient long-term, or should the fallback `gpt-4o` path become the default given reliability gaps observed in the sample run?

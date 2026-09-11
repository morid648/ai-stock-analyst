# Tasks — AI Financial Analyst Agent

> Derived from [prd.md](file:///c:/Users/anshu/code/financial%20analysis/prd.md)
> Each task is atomic — one PR / one commit scope. Phases are ordered by dependency.

---

## Phase 0 — Project Setup & Hygiene

- [x] **T0.1 — Initialize project structure**
  Create a clean directory layout: `outputs/`, `logs/`, `tests/`, `utils/`, `notebooks/`.
- [x] **T0.2 — Create `.gitignore`**
  Add rules for `outputs/`, `logs/`, `*.pyc`, `__pycache__/`, `.env`, `*.png`, and virtual environments.
- [x] **T0.3 — Create / verify `.env` template**
  Ensure `.env.example` exists with all required variables: `OLLAMA_BASE_URL`, `LLM_PROVIDER`, `OPENAI_API_KEY`, etc.
- [x] **T0.4 — Pin dependencies in `requirements.txt`**
  List and pin: `crewai`, `crewai-tools`, `yfinance`, `matplotlib`, `python-dotenv`, `fastmcp`, `pydantic`, plus dev dependencies.
- [x] **T0.5 — Set up virtual environment & install deps**
  Created `.venv` and installed all runtime and test packages.

---

## Phase 1 — Output Sanitization (Highest Priority Fix)

> **Dependency:** None — standalone fixes on `finance_crew.py`.

- [x] **T1.1 — Write `sanitize_llm_output()` utility function**
  Created [utils/sanitize.py](file:///c:/Users/anshu/code/financial%20analysis/utils/sanitize.py) to strip `<think>...</think>` blocks, markdown fences, and extraneous whitespace.
- [x] **T1.2 — Unit tests for `sanitize_llm_output()`**
  14 passing unit tests in [tests/test_sanitize.py](file:///c:/Users/anshu/code/financial%20analysis/tests/test_sanitize.py).
- [x] **T1.3 — Integrate sanitizer into `finance_crew.py` pipeline**
  Sanitizer applied directly in `run_financial_analysis()`.
- [x] **T1.4 — Integrate sanitizer into `server.py` `analyze_stock` tool**
  Sanitization integrated in `analyze_stock()` and `save_code()` for defense-in-depth.

---

## Phase 2 — Code Writer Agent Bug Fixes

> **Dependency:** Phase 1 (sanitized output needed to verify fixes).

- [x] **T2.1 — Fix `yfinance.download` → `yf.download` bug class**
  Updated Code Writer agent prompt to strictly mandate `import yfinance as yf` and `yf.download()` / `yf.Ticker()`.
- [x] **T2.2 — Fix f-string quoting issue**
  Prompt explicitly bans nested quotes inside f-strings for Python <3.12 compatibility.
- [x] **T2.3 — Add `plt.savefig()` requirement to Code Writer prompt**
  Prompt mandates `plt.savefig(...)` so charts are saved to file rather than just relying on `plt.show()`.
- [x] **T2.4 — Remove dead `code_interpreter_tool` variable**
  Deleted unused instantiated `CodeInterpreterTool` variable from `finance_crew.py`.
- [x] **T2.5 — Write integration test: single-ticker code generation**
  Integration test verified in [tests/test_crew.py](file:///c:/Users/anshu/code/financial%20analysis/tests/test_crew.py).

---

## Phase 3 — AST Validation & Bounded Retry Loop

> **Dependency:** Phase 2 (code writer must produce cleaner code for validation to be meaningful).

- [x] **T3.1 — Add `ast.parse()` validation utility**
  Created [utils/validate.py](file:///c:/Users/anshu/code/financial%20analysis/utils/validate.py) with `validate_python_code()`.
- [x] **T3.2 — Unit tests for `validate_python_code()`**
  7 unit tests in [tests/test_validate.py](file:///c:/Users/anshu/code/financial%20analysis/tests/test_validate.py).
- [x] **T3.3 — Implement bounded retry loop (max 3 retries) in `finance_crew.py`**
  Loop capped at 3 attempts with clear `RuntimeError` failure reporting.
- [x] **T3.4 — Integrate `ast.parse` check before save**
  `save_code()` rejects syntactically invalid code before writing to disk.
- [x] **T3.5 — Test bounded retry: force a failing scenario**
  Mocked retry test passing in [tests/test_crew.py](file:///c:/Users/anshu/code/financial%20analysis/tests/test_crew.py).

---

## Phase 4 — Safe Execution (Subprocess Sandbox)

> **Dependency:** Phase 3 (validated code is required before executing).

- [x] **T4.1 — Replace `exec()` with `subprocess.run()` in `run_code_and_show_plot()`**
  Implemented isolated subprocess execution in [utils/executor.py](file:///c:/Users/anshu/code/financial%20analysis/utils/executor.py).
- [x] **T4.2 — Return structured execution result**
  Created `ExecutionResult` model capturing stdout, stderr, chart path, and error state.
- [x] **T4.3 — Handle timeout gracefully**
  Catches `subprocess.TimeoutExpired` (30s default) with human-readable error.
- [x] **T4.4 — Handle missing file gracefully**
  Returns descriptive error if script is missing or outputs directory is empty.
- [x] **T4.5 — Unit test: subprocess execution with valid script**
  Verified in [tests/test_executor.py](file:///c:/Users/anshu/code/financial%20analysis/tests/test_executor.py).
- [x] **T4.6 — Unit test: subprocess timeout**
  Verified timeout handling in [tests/test_executor.py](file:///c:/Users/anshu/code/financial%20analysis/tests/test_executor.py).

---

## Phase 5 — File Management (Unique Filenames & `outputs/` Directory)

> **Dependency:** Phase 4 (execution must write to the correct paths).

- [x] **T5.1 — Create `outputs/` directory auto-provisioning**
  Created [utils/files.py](file:///c:/Users/anshu/code/financial%20analysis/utils/files.py) with `ensure_outputs_dir()`.
- [x] **T5.2 — Implement timestamped, ticker-based filenames**
  `generate_filename()` creates names like `TSLA_ytd_20260910_143201.py`.
- [x] **T5.3 — Update `save_code()` to write to `outputs/` with unique name**
  Updated `save_code()` in [server.py](file:///c:/Users/anshu/code/financial%20analysis/server.py).
- [x] **T5.4 — Update `run_code_and_show_plot()` to use the correct saved file**
  Executes specific script or auto-discovers latest saved script from `outputs/`.
- [x] **T5.5 — Ensure generated scripts use matching `.png` output path**
  Auto-derives matching `.png` path and checks for generated chart file.
- [x] **T5.6 — Test: two consecutive queries produce two separate files**
  Verified in [tests/test_server.py](file:///c:/Users/anshu/code/financial%20analysis/tests/test_server.py).

---

## Phase 6 — Error Transparency & Structured Errors (FR9)

> **Dependency:** Phases 1–5 (all error paths must be identified first).

- [x] **T6.1 — Define a standard error response format**
  Created `ToolResponse` model in [utils/types.py](file:///c:/Users/anshu/code/financial%20analysis/utils/types.py).
- [x] **T6.2 — Wrap `analyze_stock()` in try/except with structured error return**
  Returns structured JSON with user-friendly error messages.
- [x] **T6.3 — Wrap `save_code()` in try/except with structured error return**
  Detailed error return on syntax or I/O failure.
- [x] **T6.4 — Wrap `run_code_and_show_plot()` in try/except with structured error return**
  Structured execution summary returned on failure.
- [x] **T6.5 — Test: bad ticker query returns readable error**
  Tested in `tests/test_server.py`.
- [x] **T6.6 — Test: Ollama not running returns readable error**
  Tested in `tests/test_server.py`.

---

## Phase 7 — Logging & Observability

> **Dependency:** Phase 6 (logging should capture structured errors).

- [x] **T7.1 — Set up Python `logging` configuration**
  Created [utils/logging_config.py](file:///c:/Users/anshu/code/financial%20analysis/utils/logging_config.py) with rotating/timestamped file & console logging.
- [x] **T7.2 — Add logging to `finance_crew.py`**
  Logged queries, retry attempts, agent states, and errors.
- [x] **T7.3 — Add logging to `server.py`**
  Logged tool requests and results.
- [x] **T7.4 — Redirect CrewAI `verbose` output to log file**
  Log capture and logger integrated.
- [x] **T7.5 — Add `LOG_LEVEL` env var support**
  Supports `LOG_LEVEL` in `.env`.

---

## Phase 8 — LLM Provider Switch (`LLM_PROVIDER` env var)

> **Dependency:** Phase 1 (sanitization differs per model).

- [x] **T8.1 — Implement `get_llm()` factory function**
  Created [utils/llm.py](file:///c:/Users/anshu/code/financial%20analysis/utils/llm.py) supporting Ollama and OpenAI.
- [x] **T8.2 — Replace hardcoded LLM config in `finance_crew.py`**
  Integrated `get_llm()` into `create_financial_crew()`.
- [x] **T8.3 — Conditionally apply sanitization based on provider**
  Added `is_thinking_model()` in `utils/llm.py`.
- [x] **T8.4 — Test: system starts with `LLM_PROVIDER=ollama`**
  Tested in [tests/test_llm.py](file:///c:/Users/anshu/code/financial%20analysis/tests/test_llm.py).
- [x] **T8.5 — Test: system starts with `LLM_PROVIDER=openai`**
  Tested in [tests/test_llm.py](file:///c:/Users/anshu/code/financial%20analysis/tests/test_llm.py).

---

## Phase 9 — MCP Tool Polish

> **Dependency:** Phases 5–6 (file management and error handling must be in place).

- [x] **T9.1 — Improve `analyze_stock` tool docstring & schema**
  Added parameter descriptions and examples to FastMCP decorator.
- [x] **T9.2 — Improve `save_code` tool docstring & schema**
  Added detailed documentation on validation and parameters.
- [x] **T9.3 — Improve `run_code_and_show_plot` tool docstring & schema**
  Documented subprocess execution model and return schema.
- [x] **T9.4 — Implement `list_saved_analyses()` MCP tool**
  Implemented in [server.py](file:///c:/Users/anshu/code/financial%20analysis/server.py).
- [x] **T9.5 — Test `list_saved_analyses` returns correct results**
  Tested in [tests/test_server.py](file:///c:/Users/anshu/code/financial%20analysis/tests/test_server.py).
- [x] **T9.6 — End-to-end MCP test configuration documented**
  Claude Desktop configuration documented in [README.md](file:///c:/Users/anshu/code/financial%20analysis/README.md).

---

## Phase 10 — Documentation & Repo Packaging

> **Dependency:** All previous phases (document what's built).

- [x] **T10.1 — Write `README.md`**
  Created comprehensive, portfolio-ready [README.md](file:///c:/Users/anshu/code/financial%20analysis/README.md).
- [x] **T10.2 — Create architecture diagram**
  Mermaid diagram embedded in [README.md](file:///c:/Users/anshu/code/financial%20analysis/README.md).
- [x] **T10.3 — Add example run documentation**
  Detailed example queries and workflows documented.
- [x] **T10.4 — Document known limitations**
  Detailed in [README.md](file:///c:/Users/anshu/code/financial%20analysis/README.md).
- [x] **T10.5 — Add `LICENSE` file**
  Created MIT [LICENSE](file:///c:/Users/anshu/code/financial%20analysis/LICENSE).
- [x] **T10.6 — Final repo cleanup**
  Archived notebook to [notebooks/](file:///c:/Users/anshu/code/financial%20analysis/notebooks/).

---

## Phase 11 — Stretch Goals (Post-v1)

> **Dependency:** Full v1 completion.

- [ ] **T11.1 — NSE/BSE ticker auto-suffix**
  Add logic to detect Indian company names and auto-append `.NS` or `.BO` suffix before passing to yfinance.
- [ ] **T11.2 — Local cache layer (SQLite/Parquet)**
  Cache `yfinance` responses keyed by `(ticker, timeframe, date)` to reduce redundant API calls.
- [ ] **T11.3 — Fundamentals agent (4th agent)**
  Add an agent that pulls `yf.Ticker().info` for P/E, EPS, market cap and includes a summary alongside the price chart.
- [x] **T11.4 — Streamlit web front-end**
  Built modern, interactive Streamlit frontend in [app.py](file:///c:/Users/anshu/code/financial%20analysis/app.py) featuring query presets, live agent orchestration, sandbox plot rendering, code inspection, and historical analysis gallery. Tested in [tests/test_streamlit_app.py](file:///c:/Users/anshu/code/financial%20analysis/tests/test_streamlit_app.py).
- [ ] **T11.5 — LLM quality benchmark**
  Run a fixed set of 10 queries against both DeepSeek-R1 7B and GPT-4o, compare success rate, code quality, and chart accuracy.

---

## Dependency Graph (Summary)

```
P0 (Setup)
 └──▶ P1 (Sanitization)
       ├──▶ P2 (Code Writer Fixes)
       │     └──▶ P3 (AST Validation & Retry)
       │           └──▶ P4 (Safe Execution)
       │                 └──▶ P5 (File Management)
       │                       └──▶ P6 (Error Handling)
       │                             ├──▶ P7 (Logging)
       │                             └──▶ P9 (MCP Polish)
       └──▶ P8 (LLM Provider Switch)
                                           
P6 + P9 ──▶ P10 (Documentation)
P10 ──▶ P11 (Stretch)
```

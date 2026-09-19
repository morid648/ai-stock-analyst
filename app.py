"""Streamlit Web Application for AI Financial Analyst Agent.

Provides an interactive GUI for natural language financial stock analysis,
multi-agent CrewAI orchestration, automated code generation & AST validation,
sandboxed subprocess execution, and chart rendering.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from utils.env_setup import configure_utf8

configure_utf8()

import streamlit as st
from dotenv import load_dotenv

# Project modules
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

from finance_crew import run_financial_analysis
from utils.files import (
    ensure_outputs_dir,
    generate_filename,
    get_associated_chart_path,
    list_saved_analyses,
    DEFAULT_OUTPUTS_DIR,
)
from utils.validate import validate_python_code
from utils.executor import execute_script
from utils.sanitize import sanitize_llm_output


# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="AI Financial Analyst",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom Styling ---
st.markdown("""
<style>
    .metric-card {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
    }
    .badge-provider {
        background: #0066cc;
        color: white;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-success {
        background: #28a745;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    .badge-fail {
        background: #dc3545;
        color: white;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.8rem;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


def get_current_provider_info():
    """Reads active LLM provider metadata."""
    provider = os.getenv("LLM_PROVIDER", "groq").lower().strip()
    if provider == "groq":
        model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
        has_key = bool(os.getenv("GROQ_API_KEY"))
    elif provider == "openai":
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        has_key = bool(os.getenv("OPENAI_API_KEY"))
    else:
        model = os.getenv("OLLAMA_MODEL", "deepseek-r1:7b")
        has_key = True
    return provider, model, has_key


# --- Sidebar ---
with st.sidebar:
    st.title("⚙️ Configuration")
    
    provider, active_model, has_key = get_current_provider_info()
    
    st.markdown(f"""
    <div class="metric-card">
        <div style="margin-bottom: 6px;"><b>Active Provider</b></div>
        <span class="badge-provider">{provider.upper()}</span>
        <div style="margin-top: 8px; font-size: 0.85rem; color: #888;">Model: <code>{active_model}</code></div>
        <div style="margin-top: 4px; font-size: 0.85rem;">
            API Key: {"<span class='badge-success'>Configured</span>" if has_key else "<span class='badge-fail'>Missing</span>"}
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("💡 Example Queries")
    
    preset_queries = [
        "Show CUPID.NS stock price performance over the past 1 year",
        "Compare Apple (AAPL) and Microsoft (MSFT) stock performance for past year",
        "Plot Tesla (TSLA) stock gain and volatility YTD",
        "Analyze Amazon (AMZN) trading volume and close price over last 3 months",
        "Compare Indian FMCG peers: MARICO.NS, DABUR.NS, and GODREJCP.NS over 6 months",
    ]

    for q in preset_queries:
        if st.button(q, key=f"preset_{hash(q)}", use_container_width=True):
            st.session_state["query_input"] = q

    st.markdown("---")
    st.caption("AI Financial Analyst Agent • Powered by CrewAI & FastMCP")


# --- Main Application Layout ---
st.title("📈 AI Financial Analyst Agent")
st.markdown(
    "Turn natural language stock market requests into **validated, executable Python scripts** "
    "and **high-resolution charts** using an autonomous multi-agent CrewAI pipeline."
)

tab_analyze, tab_gallery = st.tabs(["🚀 Run Analysis", "📂 Historical Gallery"])

with tab_analyze:
    col_input, col_btn = st.columns([5, 1])
    
    default_text = st.session_state.get("query_input", "Show CUPID.NS stock price performance over the past 1 year")
    with col_input:
        user_query = st.text_input(
            "Enter your financial query:",
            value=default_text,
            placeholder="e.g. Compare TSLA and NVDA stock returns over the last 6 months",
            label_visibility="collapsed",
        )
    with col_btn:
        run_btn = st.button("🚀 Analyze", type="primary", use_container_width=True)

    if run_btn and user_query.strip():
        st.markdown("---")
        progress_placeholder = st.empty()
        
        with progress_placeholder.container():
            st.info("🧠 **Agent Crew Activated** — Analyzing query, generating Python code, and validating syntax...")

        start_time = datetime.now()
        try:
            # 1. Multi-agent code generation
            generated_code = run_financial_analysis(user_query.strip(), max_retries=3)
            cleaned_code = sanitize_llm_output(generated_code)

            # 2. Syntax validation
            is_valid, val_err = validate_python_code(cleaned_code)
            if not is_valid:
                progress_placeholder.error(f"❌ Code validation failed: {val_err}")
            else:
                # 3. Save code to disk
                ensure_outputs_dir()
                filename = generate_filename(symbols="ANALYSIS", timeframe="query", extension="py")
                script_path = DEFAULT_OUTPUTS_DIR / filename
                script_path.write_text(cleaned_code, encoding="utf-8")

                # 4. Execute script in isolated subprocess sandbox
                with progress_placeholder.container():
                    st.info("⚡ **Executing Script** in isolated sandbox...")

                exec_result = execute_script(script_path, timeout_seconds=30)
                elapsed = (datetime.now() - start_time).total_seconds()

                progress_placeholder.empty()

                if exec_result.success:
                    st.success(f"✅ Analysis completed successfully in **{elapsed:.1f}s**!")
                    
                    chart_path = exec_result.chart_path
                    col_chart, col_code = st.columns([3, 2])

                    with col_chart:
                        st.subheader("📊 Generated Chart")
                        if chart_path and Path(chart_path).exists():
                            st.image(chart_path, caption=f"Generated plot: {Path(chart_path).name}", use_container_width=True)
                            
                            # Download chart button
                            with open(chart_path, "rb") as f:
                                st.download_button(
                                    label="⬇️ Download Chart (.png)",
                                    data=f.read(),
                                    file_name=Path(chart_path).name,
                                    mime="image/png",
                                )
                        else:
                            st.warning("⚠️ Script executed successfully, but no matching `.png` chart was saved.")

                    with col_code:
                        st.subheader("🐍 Generated Python Script")
                        st.code(cleaned_code, language="python")
                        
                        st.download_button(
                            label="⬇️ Download Code (.py)",
                            data=cleaned_code,
                            file_name=script_path.name,
                            mime="text/x-python",
                        )

                        with st.expander("🖥️ Subprocess Execution Details"):
                            rc = getattr(exec_result, "returncode", 0)
                            dur = getattr(exec_result, "execution_time_seconds", elapsed)
                            st.write(f"**Status:** Return Code {rc}")
                            st.write(f"**Execution Time:** {dur:.2f}s")
                            if exec_result.stdout:
                                st.text(f"Stdout:\n{exec_result.stdout}")
                            if exec_result.stderr:
                                st.text(f"Stderr:\n{exec_result.stderr}")

                else:
                    st.error(f"❌ Script execution failed:\n{exec_result.error}")
                    with st.expander("Inspect generated code & traceback"):
                        st.code(cleaned_code, language="python")
                        if exec_result.stderr:
                            st.text(exec_result.stderr)

        except Exception as e:
            progress_placeholder.empty()
            st.error(f"❌ Pipeline error: {str(e)}")


with tab_gallery:
    st.subheader("📂 Previously Generated Analyses")
    ensure_outputs_dir()
    analyses = list_saved_analyses()

    if not analyses:
        st.info("No analyses saved yet. Run an analysis in the tab above to see it here!")
    else:
        st.caption(f"Found {len(analyses)} saved analyses in `outputs/`.")
        
        selected_script = st.selectbox(
            "Select an analysis to view:",
            options=[a["script_name"] for a in analyses],
            format_func=lambda s: f"{s} {'(📊 With Chart)' if any(a['script_name'] == s and a['has_chart'] for a in analyses) else ''}"
        )

        if selected_script:
            selected_path = DEFAULT_OUTPUTS_DIR / selected_script
            chart_file = get_associated_chart_path(selected_path)

            g_col1, g_col2 = st.columns([3, 2])
            with g_col1:
                if chart_file.exists():
                    st.image(str(chart_file), caption=chart_file.name, use_container_width=True)
                else:
                    st.info("No matching chart image found for this script.")

            with g_col2:
                if selected_path.exists():
                    code_content = selected_path.read_text(encoding="utf-8")
                    st.code(code_content, language="python")

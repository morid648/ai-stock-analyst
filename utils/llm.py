"""LLM factory and configuration management."""

import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_llm():
    """Initializes and returns the CrewAI LLM instance based on environment configuration."""
    from crewai import LLM

    provider = os.getenv("LLM_PROVIDER", "ollama").lower().strip()

    if provider == "groq":
        raw_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
        api_key = os.getenv("GROQ_API_KEY")
        base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
        if raw_model.startswith("gpt-oss-"):
            raw_model = f"openai/{raw_model}"
        # CrewAI strips the first provider prefix ('openai/'), so prefix with 'openai/'
        # to ensure the full Groq model ID is delivered to Groq's endpoint.
        model = f"openai/{raw_model}"
        return LLM(model=model, base_url=base_url, api_key=api_key)
    elif provider == "openai":
        model = os.getenv("OPENAI_MODEL", "gpt-4o")
        api_key = os.getenv("OPENAI_API_KEY")
        if not model.startswith("openai/"):
            model = f"openai/{model}"
        return LLM(model=model, api_key=api_key)
    else:
        # Default to local Ollama
        model = os.getenv("OLLAMA_MODEL", "deepseek-r1:7b")
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        if not model.startswith("ollama/"):
            model = f"ollama/{model}"
        return LLM(model=model, base_url=base_url)

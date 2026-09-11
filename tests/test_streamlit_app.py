"""Unit tests for app.py Streamlit web frontend."""

import os
import pytest
from unittest.mock import patch
from app import get_current_provider_info


class TestStreamlitApp:
    def test_get_current_provider_info_groq(self):
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "groq",
            "GROQ_MODEL": "openai/gpt-oss-120b",
            "GROQ_API_KEY": "test_groq_key"
        }):
            provider, model, has_key = get_current_provider_info()
            assert provider == "groq"
            assert model == "openai/gpt-oss-120b"
            assert has_key is True

    def test_get_current_provider_info_ollama(self):
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "ollama",
            "OLLAMA_MODEL": "deepseek-r1:7b",
        }):
            provider, model, has_key = get_current_provider_info()
            assert provider == "ollama"
            assert model == "deepseek-r1:7b"
            assert has_key is True

    def test_get_current_provider_info_openai(self):
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "openai",
            "OPENAI_MODEL": "gpt-4o",
            "OPENAI_API_KEY": "test_openai_key"
        }):
            provider, model, has_key = get_current_provider_info()
            assert provider == "openai"
            assert model == "gpt-4o"
            assert has_key is True

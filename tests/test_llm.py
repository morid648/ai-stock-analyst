"""Unit tests for utils/llm.py LLM provider factory."""

import os
import pytest
from unittest.mock import patch, MagicMock
from utils.llm import get_llm


class TestLlmFactory:
    @patch.dict(os.environ, {"LLM_PROVIDER": "ollama", "OLLAMA_MODEL": "deepseek-r1:7b", "OLLAMA_BASE_URL": "http://localhost:11434"})
    @patch("crewai.LLM")
    def test_get_llm_ollama(self, mock_llm_cls):
        get_llm()
        mock_llm_cls.assert_called_once_with(
            model="ollama/deepseek-r1:7b",
            base_url="http://localhost:11434"
        )

    @patch.dict(os.environ, {"LLM_PROVIDER": "openai", "OPENAI_MODEL": "gpt-4o", "OPENAI_API_KEY": "test-key"})
    @patch("crewai.LLM")
    def test_get_llm_openai(self, mock_llm_cls):
        get_llm()
        mock_llm_cls.assert_called_once_with(
            model="openai/gpt-4o",
            api_key="test-key"
        )

    @patch.dict(os.environ, {
        "LLM_PROVIDER": "groq",
        "GROQ_MODEL": "openai/gpt-oss-120b",
        "GROQ_API_KEY": "gsk_test_123",
        "GROQ_BASE_URL": "https://api.groq.com/openai/v1"
    })
    @patch("crewai.LLM")
    def test_get_llm_groq(self, mock_llm_cls):
        get_llm()
        mock_llm_cls.assert_called_once_with(
            model="openai/openai/gpt-oss-120b",
            base_url="https://api.groq.com/openai/v1",
            api_key="gsk_test_123"
        )

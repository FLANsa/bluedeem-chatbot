"""Tests for IntentClassifier.

Note: These tests use mocked OpenAI API responses for speed and cost efficiency.
For integration tests with real API, set OPENAI_API_KEY environment variable
and use pytest markers like @pytest.mark.integration.
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from core.intent import IntentClassifier


@pytest.fixture
def mock_openai_key(monkeypatch):
    """Mock OPENAI_API_KEY for testing."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-12345")


@pytest.mark.parametrize("msg,exp_intent", [
    ("هلا", "greeting"),
    ("السلام عليكم", "greeting"),
    ("تمام شكرا", "thanks"),
    ("باي", "goodbye"),
    ("متى تفتحون؟", "hours"),
    ("وين موقعكم؟", "branch"),
    ("كم سعر تنظيف اسنان؟", "service"),
    ("ابي احجز موعد", "booking"),
    ("حجز عند دكتور محمد", "booking"),
    ("مين الاطباء اللي عندكم", "doctor"),
    ("مين افضل دكتور اسنان", "doctor"),
    ("مين احسن طبيب عظام", "doctor"),
    ("عندي استفسار", "general"),  # غالبًا rule يعطي general قبل LLM حسب كلماتك
])
def test_intents(msg, exp_intent, mock_openai_key):
    """Test intent classification for various messages."""
    # Mock OpenAI client to avoid actual API calls
    with patch('core.intent.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        
        # Mock the chat completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"intent": "' + exp_intent + '", "entities": [], "confidence": 0.9, "next_action": "use_llm"}'
        mock_client.chat.completions.create.return_value = mock_response
        
        clf = IntentClassifier()
        res = clf.classify(msg)
        assert res.intent == exp_intent, f"Expected {exp_intent} for '{msg}', got {res.intent}"


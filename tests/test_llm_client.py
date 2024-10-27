import pytest
from unittest.mock import Mock, AsyncMock, patch
from llm_client import (
    LLMType,
    string_to_enum,
    get_default_llm_model_name,
    OpenAIClient,
    OllamaClient,
    ClaudeClient,
)
import asyncio


def test_llm_type_enum():
    assert LLMType.OLLAMA.value == "ollama"
    assert LLMType.OPENAI.value == "openai"
    assert LLMType.CLAUDE.value == "claude"


def test_string_to_enum():
    assert string_to_enum(LLMType, "ollama") == LLMType.OLLAMA
    assert string_to_enum(LLMType, "openai") == LLMType.OPENAI
    assert string_to_enum(LLMType, "claude") == LLMType.CLAUDE

    with pytest.raises(ValueError):
        string_to_enum(LLMType, "invalid")


def test_get_default_llm_model_name():
    assert get_default_llm_model_name(LLMType.OPENAI) == "gpt-4o-mini"
    assert get_default_llm_model_name(LLMType.OLLAMA) == "llama3.1"
    assert get_default_llm_model_name(LLMType.CLAUDE) == "claude-3-5-sonnet-latest"

    with pytest.raises(Exception):
        get_default_llm_model_name("invalid")


@patch("llm_client.AsyncOpenAI")
@patch("llm_client.OpenAI")
def test_openai_client(mock_openai, mock_async_openai):
    client = OpenAIClient("gpt-4")

    # Test chat_response
    mock_openai.return_value.chat.completions.create.return_value.choices[
        0
    ].message.content = "Test response"
    response = client.chat_response("system", "user", {})
    assert response == "Test response"

    # Test stream_chat
    mock_stream = Mock()
    mock_openai.return_value.chat.completions.create.return_value = mock_stream
    stream = client.stream_chat("system", "user", {})
    assert stream == mock_stream

    # Test async_chat
    async def async_test():
        mock_async_stream = AsyncMock()
        mock_async_openai.return_value.chat.completions.create = AsyncMock(
            return_value=mock_async_stream
        )
        stream = await client.async_chat("system", "user", {})
        assert stream == mock_async_stream

    asyncio.run(async_test())


@patch("llm_client.ollama.AsyncClient")
@patch("llm_client.ollama.Client")
def test_ollama_client(mock_ollama_client, mock_async_ollama_client):
    client = OllamaClient("llama2")

    # Test chat_response
    mock_ollama_client.return_value.chat.return_value = {
        "message": {"content": "Test response"}
    }
    response = client.chat_response(
        "system", "user", {"temperature": 0.7, "top_p": 0.9}
    )
    assert response == "Test response"

    # Test stream_chat
    mock_stream = Mock()
    mock_ollama_client.return_value.chat.return_value = mock_stream
    stream = client.stream_chat("system", "user", {"temperature": 0.7, "top_p": 0.9})
    assert stream == mock_stream

    # Test async_chat
    async def async_test():
        mock_async_stream = AsyncMock()
        mock_async_ollama_client.return_value.chat = AsyncMock(
            return_value=mock_async_stream
        )
        stream = await client.async_chat(
            "system", "user", {"temperature": 0.7, "top_p": 0.9}
        )
        assert stream == mock_async_stream

    asyncio.run(async_test())


@patch("llm_client.AsyncAnthropic")
@patch("llm_client.Anthropic")
@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test_key"})
@pytest.mark.asyncio
async def test_claude_client(mock_anthropic, mock_async_anthropic):
    client = ClaudeClient("claude-3")

    # Test chat_response
    mock_anthropic.return_value.messages.create.return_value.content[0].text = (
        "Test response"
    )
    response = client.chat_response("system", "user", {})
    assert response == "Test response"

    # Test stream_chat
    mock_stream = Mock()
    mock_anthropic.return_value.messages.create.return_value = mock_stream
    stream = client.stream_chat("system", "user", {})
    assert stream == mock_stream

    # Test async_chat
    async def mock_create(**kwargs):
        class MockResponse:
            content = [{"text": "Async test response"}]

        return MockResponse()

    mock_async_anthropic.return_value.messages.create = mock_create

    response = await client.async_chat("system", "user", {})
    assert response.content[0]["text"] == "Async test response"


# Test ClaudeClient initialization without API key
def test_claude_client_no_api_key():
    with patch.dict("os.environ", clear=True):
        with pytest.raises(ValueError):
            ClaudeClient("claude-3")

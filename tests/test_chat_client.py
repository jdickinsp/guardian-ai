import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from chat_client import ChatClient, ChatPrompt, LLMType
from code_prompts import DEFAULT_PROMPT_OPTIONS, CODE_PROMPTS, SYSTEM_PROMPT_DIFF_ENDING, SYSTEM_PROMPT_CODE_ENDING
from llm_client import ClaudeClient, OllamaClient, OpenAIClient

@pytest.fixture
def chat_client():
    with patch('chat_client.OpenAIClient'), \
         patch('chat_client.OllamaClient'), \
         patch('chat_client.ClaudeClient'):
        return ChatClient(LLMType.OPENAI, "gpt-3.5-turbo")

def test_chat_client_init():
    with patch('chat_client.OpenAIClient') as mock_openai, \
         patch('chat_client.OllamaClient') as mock_ollama, \
         patch('chat_client.ClaudeClient') as mock_claude:
        
        client = ChatClient(LLMType.OPENAI, "gpt-3.5-turbo")
        assert client.client_type == LLMType.OPENAI
        assert client.model_name == "gpt-3.5-turbo"
        assert client.client == mock_openai.return_value

        client = ChatClient(LLMType.OLLAMA, "llama2")
        assert client.client_type == LLMType.OLLAMA
        assert client.model_name == "llama2"
        assert client.client == mock_ollama.return_value

        client = ChatClient(LLMType.CLAUDE, "claude-2")
        assert client.client_type == LLMType.CLAUDE
        assert client.model_name == "claude-2"
        assert client.client == mock_claude.return_value

def test_chat_client_init_invalid_type():
    with pytest.raises(Exception):
        ChatClient("INVALID_TYPE", "model")

def test_prepare_prompts_with_prompt_and_diff_patch(chat_client):
    prompt = "Test prompt"
    patch = "diff --git a/file.txt b/file.txt\n..."
    result = chat_client.prepare_prompts(prompt, None, patch)
    
    assert isinstance(result, ChatPrompt)
    assert result.system_prompt == f"{prompt}\n{SYSTEM_PROMPT_DIFF_ENDING}"
    assert result.user_message == f"```{patch}```"
    assert result.options == DEFAULT_PROMPT_OPTIONS

def test_prepare_prompts_with_prompt_and_code_patch(chat_client):
    prompt = "Test prompt"
    patch = "def function():\n    pass"
    result = chat_client.prepare_prompts(prompt, None, patch)
    
    assert isinstance(result, ChatPrompt)
    assert result.system_prompt == f"{prompt}\n{SYSTEM_PROMPT_CODE_ENDING}"
    assert result.user_message == f"```{patch}```"
    assert result.options == DEFAULT_PROMPT_OPTIONS

def test_prepare_prompts_with_prompt_template(chat_client):
    # Use a prompt template that exists in CODE_PROMPTS
    prompt_template = list(CODE_PROMPTS.keys())[0]  # Get the first available template
    patch = "def function():\n    pass"
    result = chat_client.prepare_prompts(None, prompt_template, patch)
    
    assert isinstance(result, ChatPrompt)
    assert result.system_prompt == CODE_PROMPTS[prompt_template]["system_prompt"]
    assert result.user_message == f"```{patch}```"
    assert result.options == CODE_PROMPTS[prompt_template]["options"]

def test_prepare_prompts_no_prompt_or_template(chat_client):
    with pytest.raises(Exception, match="Error: No prompt or prompt_template"):
        chat_client.prepare_prompts(None, None, "patch")

def test_prepare_prompts_invalid_template(chat_client):
    invalid_template = "non_existent_template"
    patch = "def function():\n    pass"
    result = chat_client.prepare_prompts(None, invalid_template, patch)
    
    assert isinstance(result, ChatPrompt)
    assert result.system_prompt == "You are a helpful coding assistant."
    assert result.user_message == f"```{patch}```"
    assert result.options == DEFAULT_PROMPT_OPTIONS

def test_prepare_prompts_valid_template(chat_client):
    valid_template = "code-review"
    patch = "def function():\n    pass"
    result = chat_client.prepare_prompts(None, valid_template, patch)
    
    assert isinstance(result, ChatPrompt)
    assert result.system_prompt == CODE_PROMPTS["code-review"]["system_prompt"]
    assert result.user_message == f"```{patch}```"
    assert result.options == CODE_PROMPTS["code-review"]["options"]

@pytest.mark.asyncio
async def test_async_chat_response(chat_client):
    mock_prompt = ChatPrompt("system", "user", {})
    chat_client.client.async_chat = AsyncMock(return_value="Mock response")
    response = await chat_client.async_chat_response(mock_prompt)
    
    chat_client.client.async_chat.assert_called_once_with("system", "user", {})
    assert response == "Mock response"

def test_chat_response(chat_client):
    mock_prompt = ChatPrompt("system", "user", {})
    chat_client.client.chat_response = MagicMock(return_value="Mock response")
    response = chat_client.chat_response(mock_prompt)
    
    chat_client.client.chat_response.assert_called_once_with("system", "user", {})
    assert response == "Mock response"

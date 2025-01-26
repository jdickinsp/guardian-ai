import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from io import StringIO
import sys

from lemma.cli import process_stream, cli
from lemma.llm_client import LLMType


@pytest.mark.asyncio
async def test_process_stream_openai():
    async def mock_stream():
        yield MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))])
        yield MagicMock(choices=[MagicMock(delta=MagicMock(content=" World"))])

    output = StringIO()
    await process_stream(mock_stream(), output, LLMType.OPENAI)
    assert output.getvalue() == "Hello World"


@pytest.mark.asyncio
async def test_process_stream_ollama():
    async def mock_stream():
        yield {"message": {"content": "Hello"}}
        yield {"message": {"content": " World"}}

    output = StringIO()
    await process_stream(mock_stream(), output, LLMType.OLLAMA)
    assert output.getvalue() == "Hello World"


@pytest.mark.asyncio
async def test_process_stream_claude():
    async def mock_stream():
        yield MagicMock(type="message_start")
        yield MagicMock(type="content_block_start")
        yield MagicMock(type="content_block_delta", delta=MagicMock(text="Hello"))
        yield MagicMock(type="content_block_delta", delta=MagicMock(text=" World"))
        yield MagicMock(type="message_delta", delta=MagicMock(stop_reason=True))

    output = StringIO()
    await process_stream(mock_stream(), output, LLMType.CLAUDE)
    assert output.getvalue() == "Hello World"


@pytest.mark.asyncio
@patch("lemma.cli.load_dotenv")
@patch("lemma.cli.argparse.ArgumentParser")
@patch("lemma.cli.fetch_git_diffs")
@patch("lemma.cli.ChatClient")
@patch.dict(
    os.environ,
    {
        "OPENAI_API_KEY": "test_key",
        "ANTHROPIC_API_KEY": "test_key",
        "GITHUB_TOKEN": "test_token",
    },
)
async def test_cli(
    mock_chat_client, mock_fetch_git_diffs, mock_arg_parser, mock_load_dotenv
):
    # Mock command line arguments
    mock_args = MagicMock(
        url="https://github.com/user/repo/pull/1",
        base_branch=None,
        prompt_template="code-review",
        prompt=None,
        per_file=False,
        whole_file=False,
        stream_off=False,
        model=None,
        client=None,
    )
    mock_arg_parser.return_value.parse_args.return_value = mock_args

    # Mock git diff
    mock_fetch_git_diffs.return_value = MagicMock(
        patches=["patch1", "patch2"], contents=["content1", "content2"]
    )

    # Mock ChatClient
    mock_chat_instance = AsyncMock()
    mock_chat_instance.prepare_prompts.return_value = ["prompt1", "prompt2"]
    mock_chat_instance.async_chat_response.return_value = AsyncMock()
    mock_chat_instance.async_chat_response.return_value.__aiter__.return_value = [
        MagicMock(choices=[MagicMock(delta=MagicMock(content="Response"))])
    ]
    mock_chat_client.return_value = mock_chat_instance

    # Redirect stdout to capture output
    captured_output = StringIO()
    sys.stdout = captured_output

    try:
        # Run the cli function
        await cli()
    except Exception as e:
        pytest.fail(f"cli() raised {type(e).__name__} unexpectedly: {e}")
    finally:
        # Reset stdout
        sys.stdout = sys.__stdout__

    # Assertions
    output = captured_output.getvalue()
    assert "Client: openai" in output
    assert "Model:" in output
    assert "Url: https://github.com/user/repo/pull/1" in output
    assert "Prompt-Template: code-review" in output
    assert "Response" in output

    mock_load_dotenv.assert_called_once()
    mock_fetch_git_diffs.assert_called_once_with(
        "https://github.com/user/repo/pull/1", None
    )
    mock_chat_instance.prepare_prompts.assert_called_once()
    assert mock_chat_instance.async_chat_response.await_count == 1

    # Ensure fetch_git_diffs is not making real API calls
    mock_fetch_git_diffs.assert_called_once_with(
        "https://github.com/user/repo/pull/1", None
    )

    # Verify ChatClient methods are properly mocked
    mock_chat_instance = mock_chat_client.return_value
    mock_chat_instance.prepare_prompts.assert_called_once()
    assert mock_chat_instance.async_chat_response.await_count == 1

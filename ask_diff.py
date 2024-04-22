import argparse
import asyncio
import os
import sys

from dotenv import load_dotenv

from code_prompts import DEFAULT_PROMPT_OPTIONS, CODE_PROMPTS, SYSTEM_PROMPT_ENDING
from github_api import fetch_git_diffs
from llm_client import LLMType, OllamaClient, OpenAIClient, get_default_llm_model_name, string_to_enum


async def terminal_process_chunk(content, output, key=None):
    output.write(content)
    output.flush()


class ChatClient:
    def __init__(self, client_type, model_name, stream=True, terminal=False):
        self.client_type = client_type
        self.model_name = model_name
        self.client = None
        self.stream = stream
        self.terminal = terminal
        if client_type is LLMType.OPENAI:
            self.client = OpenAIClient(model_name, stream=stream)
        elif client_type is LLMType.OLLAMA:
            self.client = OllamaClient(model_name, stream=stream)
        else:
            raise Exception('not a valid client_type')

    async def ask_diff(self, prompt, prompt_template, patch, callback_stream, sys_out=None, key=None):
        message = f"```{patch}```"
        code_prompt = None
        if prompt_template and (prompt is None or prompt == ""):
            code_prompt = CODE_PROMPTS.get(prompt_template)
            if not code_prompt:
                raise Exception(f"Error: Invalid prompt_template")
        if (prompt is None or prompt == '') and (prompt_template is None or prompt_template == ''):
            raise Exception('Error: No prompt or prompt_template')

        prompt_options = DEFAULT_PROMPT_OPTIONS
        if prompt:
            system_prompt = f"{prompt}\n{SYSTEM_PROMPT_ENDING}"
        else:
            prompt_options = code_prompt.get('options') or DEFAULT_PROMPT_OPTIONS
            system_prompt = code_prompt.get('system_prompt')

        if self.terminal:
            await callback_stream(message, sys_out, key=key)

        if self.stream:
            await self.client.async_chat(system_prompt, message, prompt_options, callback_stream, sys_out, key=key)
        else:
            resp = self.client.chat(system_prompt, message, prompt_options)
            await callback_stream(resp, sys_out, key=key)
    

async def cli():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Process PR number, repository name, and prompt")

    parser.add_argument("--url", help="Github Url for Pull Request, Branch or Commit", required=True)
    parser.add_argument("--base_branch", help="Base Branch", required=False)
    parser.add_argument("--prompt_template", help="Prompt Template", required=False)
    parser.add_argument("--prompt", help="Prompt", required=False)
    parser.add_argument("--per_file", help="Per File", action="store_true", required=False)
    parser.add_argument("--whole_file", help="Whole File", action="store_true", required=False)
    parser.add_argument("--stream_off", help="Stream Off", action="store_true", required=False)
    parser.add_argument("--model", help="Model", required=False)
    parser.add_argument("--client", help="Client Type", required=False, type=LLMType)

    args = parser.parse_args()
    prompt_template = args.prompt_template
    prompt = args.prompt
    per_file = args.per_file
    whole_file = args.whole_file
    stream = not args.stream_off
    model_name = args.model
    client_type = args.client
    github_url = args.url
    base_branch = args.base_branch

    if client_type is None:
        client_type = string_to_enum(LLMType, os.getenv('DEFAULT_LLM_CLIENT', "openai"))

    if model_name is None:
        model_name = get_default_llm_model_name(client_type)
    
    if prompt is None and prompt_template is None:
        prompt_template = 'code-review'

    sys.stdout.write(f"Client: {client_type.name.lower()}\n")
    sys.stdout.write(f"Model: {model_name}\n")
    sys.stdout.write(f"Url: {github_url}\n")
    if prompt_template:
        sys.stdout.write(f"Prompt-Template: {prompt_template}\n")
    else:
        sys.stdout.write(f"Prompt: {prompt}\n")
    
    sys_out = sys.stdout
    git_diff = fetch_git_diffs(github_url, base_branch)
    chat_client = ChatClient(client_type, model_name, stream, terminal=True)

    if per_file:
        for idx, _  in enumerate(git_diff.patches):
            patch = git_diff.contents[idx] if whole_file else git_diff.patches[idx]
            await chat_client.ask_diff(prompt, prompt_template, patch, terminal_process_chunk, sys_out)
    else:
        patches = git_diff.contents if whole_file else git_diff.patches
        patch = "\n".join(patches)
        await chat_client.ask_diff(prompt, prompt_template, patch, terminal_process_chunk, sys_out)


if __name__ == "__main__": 
    asyncio.run(cli())

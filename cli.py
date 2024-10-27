import argparse
import asyncio
import os
import sys
from dotenv import load_dotenv

from chat_client import ChatClient
from llm_client import LLMType, string_to_enum, get_default_llm_model_name
from github_api import fetch_git_diffs


async def process_stream(stream, output, client_type):
    async for chunk in stream:
        if client_type is LLMType.OPENAI:
            content = chunk.choices[0].delta.content
        elif client_type is LLMType.OLLAMA:
            content = chunk['message']['content']
        elif client_type is LLMType.CLAUDE:
            if hasattr(chunk, 'type'):
                if chunk.type == 'message_start':
                    continue
                elif chunk.type == 'content_block_start':
                    content = ''
                elif chunk.type == 'content_block_delta':
                    content = chunk.delta.text if hasattr(chunk.delta, 'text') else ''
                elif chunk.type == 'message_delta':
                    if hasattr(chunk.delta, 'stop_reason') and chunk.delta.stop_reason:
                        break
                    content = ''
                else:
                    content = ''
        else:
            raise Exception('unkown client_type')
        if content:
            output.write(content)
            output.flush()


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
    stream_on = not args.stream_off
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

    sys_out = sys.stdout
    sys_out.write(f"""Client: {client_type.name.lower()}\n""")
    sys_out.write(f"""Model: {model_name}\n""")
    sys_out.write(f"""Url: {github_url}\n""")
    if prompt_template:
        sys_out.write(f"""Prompt-Template: {prompt_template}\n""")
    else:
        sys_out.write(f"""Prompt: {prompt}\n""")
    
    git_diff = fetch_git_diffs(github_url, base_branch)
    chat = ChatClient(client_type, model_name)

    patches = []
    if per_file:
        for idx, _  in enumerate(git_diff.patches):
            patch = git_diff.contents[idx] if whole_file else git_diff.patches[idx]
            patches.append(patch)
    else:
        diffs = git_diff.contents if whole_file else git_diff.patches
        patches.append("""\n""".join(diffs))

    for patch in patches:
        if per_file:
            sys_out.write(f"""{patch}\n""")
        prompts = chat.prepare_prompts(prompt, prompt_template, patch)
        if stream_on:
            stream = await chat.async_chat_response(prompts)
            await process_stream(stream, sys_out, client_type)
        else:
            resp = chat.chat_response(prompts)
            sys_out.write(f"""{resp}\n""")


if __name__ == "__main__": 
    asyncio.run(cli())

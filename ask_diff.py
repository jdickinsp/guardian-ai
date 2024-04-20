import argparse
import asyncio
import os
from typing import NamedTuple

from dotenv import load_dotenv

from code_prompts import DEFAULT_PROMPT_OPTIONS, CODE_PROMPTS, SYSTEM_PROMPT_ENDING
from github_api import (
    GitHubURLType,
    extract_repo_and_branch_name, 
    extract_repo_and_commit_hash, 
    extract_repo_and_pr_number, 
    get_github_branch_diff,
    get_github_commit_diff,
    get_github_pr_diff,
    identify_github_url_type
)
from llm_client import LLMClient, LLMType, get_default_llm_model_name, string_to_enum


ReviewResponse = NamedTuple("Review", [("message", str), ("response", str)])


# git_diff can be a BranchDiff, CommitDiff or PullRequestDiff
async def review_git_diff(llm_client, git_diff, prompt=None, prompt_template=None, per_file=False, whole_file=False):
    prompt_options = DEFAULT_PROMPT_OPTIONS
    if prompt_template:
        prompt_options = prompt_template.get('options') or DEFAULT_PROMPT_OPTIONS
        system_prompt = prompt_template.get('system_prompt')
    else:
        system_prompt = f"{prompt}\n{SYSTEM_PROMPT_ENDING}"
    patches = git_diff.contents if whole_file else git_diff.patches
    reviews = []
    if per_file:
        for patch in patches:
            message = f"```{patch}```"
            if per_file:
                print("Content:\n", message)
            resp = await llm_client.chat(system_prompt, message, prompt_options)
            if llm_client.stream is False:
                print("Response:\n", resp)
            reviews.append(ReviewResponse(message=message, response=resp))
    else:
        patch = "\n".join(patches)
        message = f"```{patch}```"
        resp = await llm_client.chat(system_prompt, message, prompt_options)
        if llm_client.stream is False:
            print("Response:\n", resp)
        reviews.append(ReviewResponse(message=message, response=resp))
    return reviews


async def cli():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Process PR number, repository name, and prompt")

    parser.add_argument("--url", help="Github Url for Pull Request, Branch or Commit", required=True)
    parser.add_argument("--base_branch", help="Base Branch", required=False)
    parser.add_argument("--prompt_template", help="Prompt Template", required=False, default='code-review')
    parser.add_argument("--prompt", help="Prompt", required=False)
    parser.add_argument("--per_file", help="Per File", action="store_true", required=False)
    parser.add_argument("--whole_file", help="Whole File", action="store_true", required=False)
    parser.add_argument("--stream", help="Stream", action="store_true", required=False)
    parser.add_argument("--model", help="Model", required=False)
    parser.add_argument("--client", help="Client Type", required=False, type=LLMType)

    args = parser.parse_args()
    prompt_template = args.prompt_template
    prompt = args.prompt
    per_file = args.per_file
    whole_file = args.whole_file
    stream = args.stream
    model_name = args.model
    client_type = args.client

    if client_type is None:
        client_type = string_to_enum(LLMType, os.getenv('DEFAULT_LLM_CLIENT', "openai"))

    if model_name is None:
        model_name = os.getenv('DEFAULT_LLM_MODEL', get_default_llm_model_name(client_type))

    print("Client:", client_type.name.lower())
    print("Model:", model_name)
    print("Url:", args.url)
    code_prompt = None
    if prompt_template:
        code_prompt = CODE_PROMPTS.get(prompt_template)
        if not code_prompt:
            raise Exception(f"Error: Invalid prompt template")
        print("Prompt-Template:", prompt_template)
    else:
        print("Prompt:", prompt)

    git_diff = None
    github_url_type = identify_github_url_type(args.url)

    if github_url_type is GitHubURLType.PULL_REQUEST:
        info = extract_repo_and_pr_number(args.url)
        git_diff = get_github_pr_diff(info['pr_number'], info['repo_name'])
    elif github_url_type is GitHubURLType.BRANCH:
        info = extract_repo_and_branch_name(args.url)
        git_diff = get_github_branch_diff(info['repo_name'], info['branch'], args.base_branch)
    elif github_url_type is GitHubURLType.COMMIT:
        info = extract_repo_and_commit_hash(args.url)
        git_diff = get_github_commit_diff(info['repo_name'], info['commit_hash'])
    else:
        raise Exception(f"Error: Invalid github url for --url argument")
    
    llm_client = LLMClient(client_type, model_name, stream=stream)
    await review_git_diff(llm_client, git_diff, prompt, code_prompt, per_file, whole_file)


if __name__ == "__main__": 
    asyncio.run(cli())

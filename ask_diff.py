import argparse
import os
from typing import NamedTuple
from openai import OpenAI

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


ReviewResponse = NamedTuple("Review", [("message", str), ("response", str)])


def get_llm_client():
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    return client


def get_chat_response(llm_client, model, prompt_options, system_prompt, message):
    response = llm_client.chat.completions.create(
        model=model,
        messages=[
            { "role": "system", "content": system_prompt },
            { "role": "user", "content": message }
        ],
        **prompt_options,
    )
    return response


# git_diff can be a BranchDiff, CommitDiff or PullRequestDiff
def review_git_diff(llm_client, git_diff, prompt=None, prompt_template=None, per_file=False, model="gpt-3.5-turbo"):
    prompt_options = DEFAULT_PROMPT_OPTIONS
    if prompt_template:
        prompt_options = prompt_template.get('options') or DEFAULT_PROMPT_OPTIONS
        system_prompt = prompt_template.get('system_prompt')
    else:
        system_prompt = f"{prompt}\n{SYSTEM_PROMPT_ENDING}"
    patches = "\n".join(git_diff.patches)
    message = f"```{patches}```"

    reviews = []
    if per_file:
        for patch in git_diff.patches:
            message = f"```{patch}```"
            response = get_chat_response(model, prompt_options, system_prompt, message)
            reviews.append(ReviewResponse(message=message,response=response.choices[0].message.content.strip()))
        return reviews
    else:
        response = get_chat_response(llm_client, model, prompt_options, system_prompt, message)
        reviews.append(ReviewResponse(message=message, response=response.choices[0].message.content.strip()))
    return reviews


def cli():
    parser = argparse.ArgumentParser(description="Process PR number, repository name, and prompt")

    parser.add_argument("--url", help="Github Url for Pull Request, Branch or Commit", required=True)
    parser.add_argument("--base_branch", help="Base Branch", required=False)
    parser.add_argument("--prompt_template", help="Prompt Template", required=False, default='code-review')
    parser.add_argument("--prompt", help="Prompt", required=False)
    parser.add_argument("--per_file", help="Per File", action="store_true", required=False)

    args = parser.parse_args()
    prompt_template = args.prompt_template
    prompt = args.prompt

    print("Url:", args.url)
    code_prompt = None
    if prompt_template:
        code_prompt = CODE_PROMPTS.get(prompt_template)
        if not code_prompt:
            print(f"Error: Invalid prompt template")
            return
        print("Prompt-Template:", prompt_template)
    else:
        print("Prompt:", prompt)

    git_data = None
    github_url_type = identify_github_url_type(args.url)

    if github_url_type is GitHubURLType.PULL_REQUEST:
        info = extract_repo_and_pr_number(args.url)
        git_data = get_github_pr_diff(info['pr_number'], info['repo_name'])
    elif github_url_type is GitHubURLType.BRANCH:
        info = extract_repo_and_branch_name(args.url)
        git_data = get_github_branch_diff(info['repo_name'], info['branch'], args.base_branch)
    elif github_url_type is GitHubURLType.COMMIT:
        info = extract_repo_and_commit_hash(args.url)
        git_data = get_github_commit_diff(info['repo_name'], info['commit_hash'])
    else:
        print(f"Error: Must have valid github url for --url argument")
        return
    
    llm_client = get_llm_client()
    reviews = review_git_diff(llm_client, git_data, prompt, code_prompt, args.per_file)
    for code, review in reviews:
        if args.per_file:
            print("Content:\n", code)
        print("Response:\n", review)
        print("\n")


if __name__ == "__main__": 
    cli()

import argparse
import os
import re
from typing import NamedTuple
from openai import OpenAI

from code_prompts import DEFAULT_PROMPT_OPTIONS, CODE_PROMPTS, SYSTEM_PROMPT_ENDING
from github_api import get_github_pr_diff

ReviewResponse = NamedTuple("Review", [("message", str), ("response", str)])

# Set up OpenAI API credentials
client = OpenAI(
    api_key=os.environ.get("OPENAI_API_KEY"),
)

def extract_pr_and_repo(url):
    # Regular expression pattern to extract PR number and repository name
    pattern = r"https://github.com/([^/]+)/([^/]+)/pull/(\d+)"

    # Match the URL with the pattern
    match = re.match(pattern, url)

    if match:
        # Extracting groups
        org_name = match.group(1)
        repo_name = match.group(2)
        pr_number = match.group(3)

        return {
            "pr_number": int(pr_number, 10),
            "repo_name": f"{org_name}/{repo_name}"
        }
    else:
        print("Warning: The URL format is not correct.")
        return None


def get_pr_review_per_patch(pr_number, repo_name, prompt=None, prompt_template=None):
    prompt_options = DEFAULT_PROMPT_OPTIONS
    if prompt_template:
        prompt_options = prompt_template.get('options') or DEFAULT_PROMPT_OPTIONS
        system_prompt = prompt_template.get('system_prompt')
    else:
        system_prompt = f"{prompt}\n{SYSTEM_PROMPT_ENDING}"
    pr = get_github_pr_diff(pr_number, repo_name)
    reviews = []
    for patch in pr.patches:
        message = f"```{patch}```"
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                { "role": "system", "content": system_prompt },
                { "role": "user", "content": message }
            ],
            **prompt_options,
        )
        reviews.append(ReviewResponse(message=message,response=response.choices[0].message.content.strip()))
    return reviews


def get_pr_review(pr_number, repo_name, prompt=None, prompt_template=None):
    prompt_options = DEFAULT_PROMPT_OPTIONS
    if prompt_template:
        prompt_options = prompt_template.get('options') or DEFAULT_PROMPT_OPTIONS
        system_prompt = prompt_template.get('system_prompt')
    else:
        system_prompt = f"{prompt}\n{SYSTEM_PROMPT_ENDING}"
    pr = get_github_pr_diff(pr_number, repo_name)
    patches = "\n".join(pr.patches)
    message = f"```{patches}```"
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            { "role": "system", "content": system_prompt },
            { "role": "user", "content": message }
        ],
        **prompt_options,
    )
    review = ReviewResponse(message=message, response=response.choices[0].message.content.strip())
    return review


def cli():
    parser = argparse.ArgumentParser(description="Process PR number, repository name, and prompt")

    # Add arguments
    parser.add_argument("--pr_url", help="Pull Request Github Url", required=True)
    parser.add_argument("--prompt_template", help="Prompt Template", required=False)
    parser.add_argument("--prompt", help="Prompt", required=False, default=CODE_PROMPTS['code-review'])
    parser.add_argument("--per_file", help="Per File", action="store_true", required=False)

    # Parse the arguments
    args = parser.parse_args()

    # Extract named arguments
    pr_info = extract_pr_and_repo(args.pr_url)
    pr_number = pr_info['pr_number']
    repo_name = pr_info['repo_name']
    prompt_template = args.prompt_template
    prompt = args.prompt

    print("PR:", args.pr_url)
    code_prompt = None
    if prompt_template:
        code_prompt = CODE_PROMPTS.get(prompt_template)
        if not code_prompt:
            print(f"Error: Invalid prompt template.")
            return
        print("Prompt-Template:", prompt_template)
    else:
        print("Prompt:", prompt)

    if args.per_file:
        reviews = get_pr_review_per_patch(pr_number, repo_name, prompt, code_prompt)
        for code, review in reviews:
            print("Content:\n", code)
            print("Response:\n", review)
            print("\n")
    else:
        pr_review = get_pr_review(pr_number, repo_name, prompt, code_prompt)
        print("Response:\n", pr_review.response)
        print("\n")


if __name__ == "__main__": 
    cli()

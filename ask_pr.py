import argparse
import os
import re
from typing import NamedTuple
from openai import OpenAI

from code_prompts import SYSTEM_PROMPTS_FOR_CODE
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
        # Log a warning if the URL format is not correct
        print("Warning: The URL format is not correct.")
        return None


def get_pr_review_per_diff(pr_number, repo_name, system_prompt):
    pr_diffs = get_github_pr_diff(pr_number, repo_name)
    reviews = []
    for diff in pr_diffs:
        message = diff
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": message,
                }
            ],
            model="gpt-3.5-turbo",
            top_p=0.9,
            temperature=1.0,
            max_tokens=4094,
        )
        reviews.append(ReviewResponse(message=message,response=response.choices[0].message.content.strip()))
    return reviews


def get_pr_review(pr_number, repo_name, prompt):
    pr_diffs = get_github_pr_diff(pr_number, repo_name)
    content_diff = [diff for diff in pr_diffs]
    message = "\n".join(content_diff)
    system_prompt = f"Your message is a diff of a PR. \n{prompt}\n"
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": message,
            }
        ],
        model="gpt-4-turbo",
        top_p=0.9,
        temperature=1.0,
        max_tokens=4094,
    )
    review = ReviewResponse(message=message, response=response.choices[0].message.content.strip())
    return review


def cli():
    parser = argparse.ArgumentParser(description="Process PR number, repository name, and prompt")

    # Add arguments
    parser.add_argument("--pr_url", help="Pull Request Github Url", required=True)
    parser.add_argument("--prompt_template", help="Prompt Template", required=False)
    parser.add_argument("--prompt", help="Prompt", required=False, default=SYSTEM_PROMPTS_FOR_CODE['code-review-short'])
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
    if prompt_template:
        prompt = SYSTEM_PROMPTS_FOR_CODE.get(prompt_template)
        print("Prompt-Template:", prompt_template)
    else:
        print("Prompt:", prompt)

    if args.per_file:
        reviews = get_pr_review_per_diff(pr_number, repo_name, prompt)
        for code, review in reviews:
            print("Code:", code)
            print("Response:\n", review)
            print("\n")
    else:
        pr_review = get_pr_review(pr_number, repo_name, prompt)
        print("Response:\n", pr_review.response)
        print("\n")


if __name__ == "__main__": 
    cli()

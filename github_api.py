from collections import namedtuple
from enum import Enum
import os
import itertools
import re
from github import Github
from github import Auth


BranchDiff = namedtuple("BranchDiff", ["repo_name", "base_branch", "compare_branch", "patches", "contents"])
CommitDiff = namedtuple("CommitDiff", ["repo_name", "commit_hash", "patches", "contents"])
PullRequestDiff = namedtuple("PullRequest", ["repo_name", "pr_number", "title", "body", "patches", "contents"])


class GitHubURLType(Enum):
    PULL_REQUEST = "Pull Request"
    BRANCH = "Branch"
    COMMIT = "Commit"
    UNKNOWN = "Unknown"


def identify_github_url_type(url):
    """
    Identifies the type of GitHub URL (Pull Request, Branch, or Commit).

    Args:
    url (str): The GitHub URL to be analyzed.

    Returns:
    str: A description of the URL type ('Pull Request', 'Branch', 'Commit', or 'Unknown').
    """
    # Regex patterns for different types of GitHub URLs
    pr_pattern = r"https://github\.com/[^/]+/[^/]+/pull/\d+(/[^/]+)?"
    branch_pattern = r"https://github\.com/[^/]+/[^/]+/tree/[^/]+"
    commit_pattern = r"https://github\.com/[^/]+/[^/]+/commit/[0-9a-f]{40}"

    if re.match(pr_pattern, url):
        return GitHubURLType.PULL_REQUEST
    elif re.match(branch_pattern, url):
        return GitHubURLType.BRANCH
    elif re.match(commit_pattern, url):
        return GitHubURLType.COMMIT
    else:
        return  GitHubURLType.UNKNOWN


def extract_repo_and_pr_number(url):
    # Regular expression pattern to extract PR number and repository name
    pattern = r"https://github.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.match(pattern, url)
    if match:
        owner = match.group(1)
        repo_name = match.group(2)
        pr_number = match.group(3)
        return {
            "pr_number": int(pr_number, 10),
            "repo_name": f"{owner}/{repo_name}"
        }
    else:
        print("Warning: The URL format is not correct.")
        return None


def get_github_pr_diff(pr_number, repo_name):
    api_key = os.environ.get("GITHUB_ACCESS_TOKEN")
    auth = Auth.Token(api_key)

    g = Github(auth=auth)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    pr_description = pr.body
    pr_title = pr.title

    head_sha = pr.head.sha
    files = list(itertools.islice(pr.get_files(), 51))
    contents = []
    patches = []

    for file in files:
        path = file.filename
        try:
            content = repo.get_contents(path, ref=head_sha)
            if content.encoding == "base64":
                file_content = content.decoded_content.decode()
                contents.append(file_content)
        except Exception as e:
            print(f"Error retrieving content for {path}: {str(e)}")
        patches.append(file.patch)

    return PullRequestDiff(repo_name, pr_number, pr_title, pr_description, patches, contents)


def extract_repo_and_branch_name(url):
    # Regex to match the GitHub URL and extract the repository and branch name
    pattern = r"https://github\.com/([^/]+)/([^/]+)/tree/([^/]+(?:/[^/]+)*)"
    match = re.search(pattern, url)
    if match:
        owner = match.group(1)
        repo_name = match.group(2)
        branch_name = match.group(3)
        return {
            "repo_name": f"{owner}/{repo_name}",
            "branch": branch_name
        }
    else:
        print("Warning: The URL format is not correct.")
        return None


def get_github_branch_diff(repo_name, compare_branch, base_branch=None):
    api_key = os.environ.get("GITHUB_ACCESS_TOKEN")
    auth = Auth.Token(api_key)

    g = Github(auth=auth)
    repo = g.get_repo(repo_name)

    if base_branch is None:
        base_branch = repo.default_branch

    # Get comparison between base and compare branches
    comparison = repo.compare(base_branch, compare_branch)
    contents = []
    patches = []
    
    for file in comparison.files:
        path = file.filename
        try:
            content = repo.get_contents(path, ref=compare_branch)
            if content.encoding == "base64":
                file_content = content.decoded_content.decode()
                contents.append(file_content)
        except Exception as e:
            print(f"Error retrieving content for {path}: {str(e)}")
        patches.append(file.patch)

    return BranchDiff(repo_name, base_branch, compare_branch, patches, contents)


def extract_repo_and_commit_hash(url):
    # Regex to match the GitHub URL and extract the repository and commit hash
    pattern = r"https://github\.com/([^/]+)/([^/]+)/commit/([0-9a-f]{40})"
    match = re.search(pattern, url)
    if match:
        owner = match.group(1)
        repo_name = match.group(2)
        commit_hash = match.group(3)
        return {
            "repo_name": f"{owner}/{repo_name}",
            "commit_hash": commit_hash
        }
    else:
        print("Warning: The URL format is not correct.")
        return None


def get_github_commit_diff(repo_name, commit_hash):
    api_key = os.environ.get("GITHUB_ACCESS_TOKEN")
    auth = Auth.Token(api_key)

    g = Github(auth=auth)
    repo = g.get_repo(repo_name)

    commit = repo.get_commit(sha=commit_hash)
    contents = []
    patches = []
    
    for file in commit.files:
        path = file.filename
        try:
            content = repo.get_contents(path, ref=commit_hash)
            if content.encoding == "base64":
                file_content = content.decoded_content.decode()
                contents.append(file_content)
        except Exception as e:
            print(f"Error retrieving content for {path}: {str(e)}")
        patches.append(file.patch)

    return CommitDiff(repo_name, commit_hash, patches, contents)


if __name__ == "__main__":
    # pr_diff = get_github_pr_diff(155, "karpathy/llm.c")
    # print(pr_diff.title)
    branch_diff = get_github_branch_diff("karpathy/llm.c", "feature/cublaslt")
    print(branch_diff)

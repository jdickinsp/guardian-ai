from collections import namedtuple
from enum import Enum
import os
import itertools
import re
from github import Github, Auth


BranchDiff = namedtuple("BranchDiff", ["repo_name", "base_branch", "compare_branch", "file_names", "patches", "contents"])
CommitDiff = namedtuple("CommitDiff", ["repo_name", "commit_hash", "file_names", "patches", "contents"])
PullRequestDiff = namedtuple("PullRequest", ["repo_name", "pr_number", "title", "body", "file_names", "patches", "contents"])


class GitHubURLType(Enum):
    PULL_REQUEST = "Pull Request"
    BRANCH = "Branch"
    COMMIT = "Commit"
    PULL_REQUEST_COMMIT = "Pull Request Commit"
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
    pr_commit_pattern = r"https://github\.com/[^/]+/[^/]+/pull/\d+/commits/[0-9a-f]{40}"

    if re.match(pr_commit_pattern, url):
        return GitHubURLType.PULL_REQUEST_COMMIT
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


def get_diff_header(file):
    return (
        f"diff --git a/{file.filename} b/{file.filename}\n"
        f"index {file.sha[:7]}..{file.sha[:7]} 100644\n"  # sha and mode are not directly available, so we use file.sha as placeholder
        f"--- a/{file.filename}\n"
        f"+++ b/{file.filename}\n"
    )


def get_github_pr_diff(pr_number, repo_name):
    g = Github(auth=Auth.Token(os.getenv("GITHUB_ACCESS_TOKEN")))
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    pr_description = pr.body
    pr_title = pr.title

    head_sha = pr.head.sha
    files = list(itertools.islice(pr.get_files(), 51))
    file_names = []
    contents = []
    patches = []

    for file in files:
        path = file.filename
        try:
            content = repo.get_contents(path, ref=head_sha)
            if content.encoding == "base64":
                file_content = content.decoded_content.decode()
                contents.append(file_content)
                patches.append(get_diff_header(file) + file.patch)
                file_names.append(path)
        except Exception as e:
            print(f"Error retrieving content for {path}: {str(e)}")

    return PullRequestDiff(repo_name, pr_number, pr_title, pr_description, file_names, patches, contents)


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
    g = Github(auth=Auth.Token(os.getenv("GITHUB_ACCESS_TOKEN")))
    repo = g.get_repo(repo_name)

    if base_branch is None:
        base_branch = repo.default_branch

    # Get comparison between base and compare branches
    comparison = repo.compare(base_branch, compare_branch)
    file_names = []
    contents = []
    patches = []

    if len(comparison.files) == 0:
        raise Exception('compare branch is not different than base branch')
    
    for file in comparison.files:
        path = file.filename
        try:
            content = repo.get_contents(path, ref=compare_branch)
            if content.encoding == "base64":
                file_content = content.decoded_content.decode()
                contents.append(file_content)
                patches.append(get_diff_header(file) + file.patch)
                file_names.append(path)
        except Exception as e:
            print(f"Error retrieving content for {path}: {str(e)}")

    return BranchDiff(repo_name, base_branch, compare_branch, file_names, patches, contents)


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


def get_commit_hash_from_url(url):
    # Regex to match the GitHub pull request commit URL and extract the repository and commit hash
    pattern = r"https://github.com/([^/]+)/([^/]+)/pull/(\d+)/commits/([a-f0-9]+)"
    match = re.search(pattern, url)
    if match:
        owner = match.group(1)
        repo_name = match.group(2)
        pr_number = match.group(3)
        commit_hash = match.group(4)
        return {
            "repo_name": f"{owner}/{repo_name}",
            "pr_number": pr_number,
            "commit_hash": commit_hash
        }
    else:
        print("Warning: The URL format is not correct.")
        return None


def get_github_commit_diff(repo_name, commit_hash):
    g = Github(auth=Auth.Token(os.getenv("GITHUB_ACCESS_TOKEN")))
    repo = g.get_repo(repo_name)

    commit = repo.get_commit(sha=commit_hash)
    file_names = []
    contents = []
    patches = []
    
    for file in commit.files:
        path = file.filename
        try:
            content = repo.get_contents(path, ref=commit_hash)
            if content.encoding == "base64":
                file_content = content.decoded_content.decode()
                contents.append(file_content)
                patches.append(get_diff_header(file) + file.patch)
                file_names.append(path)
        except Exception as e:
            print(f"Error retrieving content for {path}: {str(e)}")

    return CommitDiff(repo_name, commit_hash, file_names, patches, contents)


def fetch_git_diffs(github_url, base_branch=None):
    diffs = None
    github_url_type = identify_github_url_type(github_url)

    if github_url_type is GitHubURLType.PULL_REQUEST:
        info = extract_repo_and_pr_number(github_url)
        diffs = get_github_pr_diff(info['pr_number'], info['repo_name'])
    elif github_url_type is GitHubURLType.BRANCH:
        info = extract_repo_and_branch_name(github_url)
        diffs = get_github_branch_diff(info['repo_name'], info['branch'], base_branch)
    elif github_url_type is GitHubURLType.COMMIT:
        info = extract_repo_and_commit_hash(github_url)
        diffs = get_github_commit_diff(info['repo_name'], info['commit_hash'])
    elif github_url_type is GitHubURLType.PULL_REQUEST_COMMIT:
        info = get_commit_hash_from_url(github_url)
        diffs = get_github_commit_diff(info['repo_name'], info['commit_hash'])
    else:
        raise Exception(f"Error: Invalid github url")
    return diffs


if __name__ == "__main__":
    pr_diff = get_github_pr_diff(155, "karpathy/llm.c")
    for p in pr_diff.patches:
        print(p)
    # branch_diff = get_github_branch_diff("karpathy/llm.c", "feature/cublaslt")
    # print(branch_diff)
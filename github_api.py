import os
import itertools
from github import Github
from github import Auth


def get_github_pr_content(pr_number, repo_name):
    api_key = os.environ.get("GITHUB_ACCESS_TOKEN")
    auth = Auth.Token(api_key)

    g = Github(auth=auth)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    head_sha = pr.head.sha
    files = list(itertools.islice(pr.get_files(), 51))
    diff_contents = []
    for file in files:
        path = file.filename
        contents = repo.get_contents(path, ref=head_sha)
        content = contents.decoded_content.decode()
        diff_contents.append(content)
    return "\n".join(diff_contents)


def get_github_pr_diff(pr_number, repo_name):
    api_key = os.environ.get("GITHUB_ACCESS_TOKEN")
    auth = Auth.Token(api_key)

    g = Github(auth=auth)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)

    files = list(itertools.islice(pr.get_files(), 51))
    patches = []
    for file in files:
        patches.append(file.patch)
    return patches


if __name__ == "__main__":
    pr_diff = get_github_pr_diff(150, "karpathy/llm.c")
    print(pr_diff)

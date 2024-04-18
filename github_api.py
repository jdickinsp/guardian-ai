from collections import namedtuple
import os
import itertools
from github import Github
from github import Auth

PullRequest = namedtuple("PullRequest", ["pr_number", "repo_name", "title", "body", "patches", "contents"])


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
        content = repo.get_contents(path, ref=head_sha)
        if content.encoding == "base64":
            file_content = content.decoded_content.decode()
            contents.append(file_content)
        patches.append(file.patch)

    return PullRequest(pr_number, repo_name, pr_title, pr_description, patches, contents)

if __name__ == "__main__":
    pr_diff = get_github_pr_diff(155, "karpathy/llm.c")
    print(pr_diff.title)

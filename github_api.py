import base64
import itertools
import os
import re
from collections import namedtuple
from enum import Enum

from github import Github, Auth

from detect import is_ignored_file, is_test_file

BranchDiff = namedtuple("BranchDiff", ["repo_name", "base_branch", "compare_branch", "file_names", "patches", "contents"])
CommitDiff = namedtuple("CommitDiff", ["repo_name", "commit_hash", "file_names", "patches", "contents"])
PullRequestDiff = namedtuple("PullRequest", ["repo_name", "pr_number", "title", "body", "file_names", "patches", "contents"])


class GitHubURLType(Enum):
    PULL_REQUEST = "Pull Request"
    BRANCH = "Branch"
    COMMIT = "Commit"
    PULL_REQUEST_COMMIT = "Pull Request Commit"
    FILE_PATH = "File Path"
    FOLDER_PATH = "Folder Path"
    UNKNOWN = "Unknown"


class GitHubURLIdentifier:
    @staticmethod
    def identify_github_url_type(url, info):
        """
        Identifies the type of GitHub URL (Pull Request, Branch, or Commit).
        """
        pr_pattern = r"https://github\.com/[^/]+/[^/]+/pull/\d+(/[^/]+)?"
        branch_pattern = r"https://github\.com/[^/]+/[^/]+/tree/[^/]+"
        commit_pattern = r"https://github\.com/[^/]+/[^/]+/commit/[0-9a-f]{40}"
        pr_commit_pattern = r"https://github\.com/[^/]+/[^/]+/pull/\d+/commits/[0-9a-f]{40}"
        folder_pattern = r'^https:\/\/github\.com\/[^\/]+\/[^\/]+\/tree\/[^\/]+\/.*$'
        file_pattern = r'^https:\/\/github\.com\/[^\/]+\/[^\/]+\/blob\/[^\/]+\/.+$'

        if info['branch'] and info['folder_path'] is None and re.match(branch_pattern, url):
            return GitHubURLType.BRANCH
        if re.match(pr_commit_pattern, url):
            return GitHubURLType.PULL_REQUEST_COMMIT
        elif re.match(pr_pattern, url):
            return GitHubURLType.PULL_REQUEST
        elif re.match(file_pattern, url):
            return GitHubURLType.FILE_PATH
        elif re.match(folder_pattern, url):
            return GitHubURLType.FOLDER_PATH
        elif re.match(commit_pattern, url):
            return GitHubURLType.COMMIT
        else:
            return GitHubURLType.UNKNOWN

    @staticmethod
    def extract_repo_and_pr_number(url):
        pattern = r"https://github.com/([^/]+)/([^/]+)/pull/(\d+)"
        match = re.match(pattern, url)
        if match:
            owner = match.group(1)
            repo_name = match.group(2)
            pr_number = match.group(3)
            return {"pr_number": int(pr_number, 10), "repo_name": f"{owner}/{repo_name}"}
        else:
            print("Warning: The URL format is not correct.")
            return None

    @staticmethod
    def extract_repo_and_commit_hash(url):
        pattern = r"https://github\.com/([^/]+)/([^/]+)/commit/([0-9a-f]{40})"
        match = re.search(pattern, url)
        if match:
            owner = match.group(1)
            repo_name = match.group(2)
            commit_hash = match.group(3)
            return {"repo_name": f"{owner}/{repo_name}", "commit_hash": commit_hash}
        else:
            print("Warning: The URL format is not correct.")
            return None

    @staticmethod
    def get_commit_hash_from_url(url):
        pattern = r"https://github.com/([^/]+)/([^/]+)/pull/(\d+)/commits/([a-f0-9]+)"
        match = re.search(pattern, url)
        if match:
            owner = match.group(1)
            repo_name = match.group(2)
            pr_number = match.group(3)
            commit_hash = match.group(4)
            return {"repo_name": f"{owner}/{repo_name}", "pr_number": pr_number, "commit_hash": commit_hash}
        else:
            print("Warning: The URL format is not correct.")
            return None


class GitHubRepoHelper:
    @staticmethod
    def get_diff_header(file):
        return (
            f"diff --git a/{file.filename} b/{file.filename}\n"
            f"index {file.sha[:7]}..{file.sha[:7]} 100644\n"
            f"--- a/{file.filename}\n"
            f"+++ b/{file.filename}\n"
        )

    @staticmethod
    def get_github_info_from_url(github_url):
        try:
            url_parts = [part for part in github_url.split('/') if part]
            owner = url_parts[2]
            repo = url_parts[3]
            ref_index = -1
            path_parts = []
            if 'tree' in url_parts or 'blob' in url_parts:
                ref_index = url_parts.index('tree') if 'tree' in url_parts else url_parts.index('blob')
                path_parts = url_parts[ref_index + 1:]
        except (IndexError, ValueError):
            raise ValueError("Invalid GitHub URL")

        g = Github(auth=Auth.Token(os.getenv("GITHUB_ACCESS_TOKEN")))
        repository = g.get_repo(f"{owner}/{repo}")

        # Validate branch exists
        branches = repository.get_branches()
        branch_names = [branch.name for branch in branches]

        branch_name = None
        for i in range(0, len(path_parts) + 1):
            potential_branch = '/'.join(path_parts[:i])
            if potential_branch in branch_names:
                branch_name = potential_branch
                break

        if branch_name:
            # Determine the folder path and file path
            folder_path = '/'.join(path_parts[len(branch_name.split('/')):])
            if len(folder_path) == 0:
                folder_path = None
            file_path = folder_path if folder_path else None
        else:
            folder_path = None
            file_path = None
        
        return {
            "owner": owner,
            "repo": repo,
            "repo_name": f"{owner}/{repo}",
            "branch": branch_name,
            "folder_path": folder_path if not file_path else None,
            "file_path": file_path
        }


class GitHubDiffFetcher:
    def __init__(self):
        self.github = Github(auth=Auth.Token(os.getenv("GITHUB_ACCESS_TOKEN")))

    def get_github_pr_diff(self, pr_number, repo_name, ignore_tests=False):
        repo = self.github.get_repo(repo_name)
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
                if is_ignored_file(content.path):
                    continue
                if ignore_tests and is_test_file(content.path):
                    continue
                if content.encoding == "base64":
                    file_content = content.decoded_content.decode()
                    contents.append(file_content)
                    patches.append(GitHubRepoHelper.get_diff_header(file) + file.patch)
                    file_names.append(path)
            except Exception as e:
                print(f"Error retrieving content for {path}: {str(e)}")

        return PullRequestDiff(repo_name, pr_number, pr_title, pr_description, file_names, patches, contents)

    def get_github_branch_diff(self, repo_name, compare_branch, base_branch=None, ignore_tests=False):
        repo = self.github.get_repo(repo_name)
        if base_branch is None:
            base_branch = repo.default_branch

        paths = []
        files = []
        file_names = []
        contents = []
        patches = []

        if base_branch != compare_branch:
            comparison = repo.compare(base_branch, compare_branch)
            files = comparison.files
            paths = [f.filename for f in comparison.files]
        else:
            master_ref = repo.get_branch(base_branch)
            master_sha = master_ref.commit.sha
            master_tree = repo.get_git_tree(master_sha, recursive=True).tree
            files = [item for item in master_tree if item.type == 'blob']
            paths = [f.path for f in files]

        for idx, path in enumerate(paths):
            try:
                content = repo.get_contents(path, ref=compare_branch)
                if is_ignored_file(content.path):
                    continue
                if ignore_tests and is_test_file(content.path):
                    continue
                if content.encoding == "base64":
                    file_content = content.decoded_content.decode()
                    contents.append(file_content)
                    if base_branch != compare_branch:
                        patches.append(GitHubRepoHelper.get_diff_header(files[idx]) + files[idx].patch)
                    else:
                        patches.append(file_content)
                    file_names.append(path)
            except Exception as e:
                print(f"Error retrieving content for {path}: {str(e)}")

        return BranchDiff(repo_name, base_branch, compare_branch, file_names, patches, contents)

    def get_github_commit_diff(self, repo_name, commit_hash, ignore_tests=False):
        repo = self.github.get_repo(repo_name)
        commit = repo.get_commit(sha=commit_hash)
        file_names = []
        contents = []
        patches = []

        for file in commit.files:
            path = file.filename
            try:
                content = repo.get_contents(path, ref=commit_hash)
                if is_ignored_file(content.path):
                    continue
                if ignore_tests and is_test_file(content.path):
                    continue
                if content.encoding == "base64":
                    file_content = content.decoded_content.decode()
                    contents.append(file_content)
                    patches.append(GitHubRepoHelper.get_diff_header(file) + file.patch)
                    file_names.append(path)
            except Exception as e:
                print(f"Error retrieving content for {path}: {str(e)}")

        return CommitDiff(repo_name, commit_hash, file_names, patches, contents)

    def get_github_file_content(self, url_info):
        owner = url_info["owner"]
        repo = url_info["repo"]
        repo_name = url_info["repo_name"]
        branch = url_info["branch"]
        file_path = url_info["file_path"]

        repo = self.github.get_repo(f"{owner}/{repo}")
        base_branch = repo.default_branch
        if base_branch == branch:
            file_content = repo.get_contents(file_path, ref=branch)
            content = file_content.decoded_content.decode('utf-8')
            contents = [content]
            filenames = [file_path]
            return BranchDiff(repo_name, base_branch, branch, filenames, contents, contents)
        else:
            comparison = repo.compare(base_branch, branch)
        file = None
        for file in comparison.files:
            if file.filename == file_path:
                file = file

        contents = []
        patches = []
        filenames = []
        path = file.filename
        try:
            content = repo.get_contents(path, ref=branch)
            if content.encoding == "base64":
                file_content = content.decoded_content.decode()
                contents.append(file_content)
                patches.append(GitHubRepoHelper.get_diff_header(file) + file.patch)
                filenames.append(path)
        except Exception as e:
            print(f"Error retrieving content for {path}: {str(e)}")
        return BranchDiff(repo_name, base_branch, branch, filenames, patches, contents)

    def get_github_folder_contents(self, url_info, ignore_tests=False):
        owner = url_info["owner"]
        repo = url_info["repo"]
        repo_name = url_info["repo_name"]
        branch = url_info["branch"]
        folder_path = url_info["folder_path"]

        repository = self.github.get_repo(f"{owner}/{repo}")
        base_branch = repository.default_branch
        contents = repository.get_contents(folder_path, ref=branch)

        file_contents = []
        filenames = []

        for content_file in contents:
            if is_ignored_file(content_file.path):
                continue
            if ignore_tests and is_test_file(content_file.path):
                continue
            if content_file.type == 'file':
                file_data = repository.get_contents(content_file.path, ref=branch)
                content = base64.b64decode(file_data.content).decode('utf-8')
                file_contents.append(content)
                filenames.append(content_file.path)

        return BranchDiff(repo_name, base_branch, branch, filenames, file_contents, file_contents)


def fetch_git_diffs(github_url, base_branch=None, ignore_tests=True):
    fetcher = GitHubDiffFetcher()
    info = GitHubRepoHelper.get_github_info_from_url(github_url)
    github_url_type = GitHubURLIdentifier.identify_github_url_type(github_url, info)

    if github_url_type is GitHubURLType.PULL_REQUEST:
        info = GitHubURLIdentifier.extract_repo_and_pr_number(github_url)
        return fetcher.get_github_pr_diff(info['pr_number'], info['repo_name'], ignore_tests=ignore_tests)
    elif github_url_type is GitHubURLType.BRANCH:
        return fetcher.get_github_branch_diff(info['repo_name'], info['branch'], base_branch, ignore_tests=ignore_tests)
    elif github_url_type is GitHubURLType.COMMIT:
        info = GitHubURLIdentifier.extract_repo_and_commit_hash(github_url)
        return fetcher.get_github_commit_diff(info['repo_name'], info['commit_hash'], ignore_tests=ignore_tests)
    elif github_url_type is GitHubURLType.PULL_REQUEST_COMMIT:
        info = GitHubURLIdentifier.get_commit_hash_from_url(github_url)
        return fetcher.get_github_commit_diff(info['repo_name'], info['commit_hash'], ignore_tests=ignore_tests)
    elif github_url_type is GitHubURLType.FILE_PATH:
        return fetcher.get_github_file_content(info)
    elif github_url_type is GitHubURLType.FOLDER_PATH:
        return fetcher.get_github_folder_contents(info, ignore_tests=ignore_tests)
    else:
        raise Exception(f"Error: Invalid github url")


if __name__ == "__main__":
    pr_diff = fetch_git_diffs("https://github.com/karpathy/llm.c/pull/155")
    for p in pr_diff.patches:
        print(p)
    
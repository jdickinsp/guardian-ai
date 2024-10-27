import base64
import os
import re
from collections import namedtuple
from enum import Enum
from typing import List, Union, Dict, Optional
from urllib.parse import urlparse, urlunparse

from github import Github, Auth
from github.Repository import Repository
from github.ContentFile import ContentFile

from detect import is_ignored_file, is_test_file

BranchDiff = namedtuple("BranchDiff", ["repo_name", "base_branch", "compare_branch", "file_names", "patches", "contents"])
CommitDiff = namedtuple("CommitDiff", ["repo_name", "commit_hash", "file_names", "patches", "contents"])
PullRequestDiff = namedtuple("PullRequest", ["repo_name", "pr_number", "title", "body", "file_names", "patches", "contents"])


class GitHubURLType(Enum):
    BRANCH = 'Branch'
    FOLDER_PATH = 'Folder Path'
    PULL_REQUEST = 'Pull Request'
    PULL_REQUEST_COMMIT = 'Pull Request Commit'
    FILE_PATH = 'File Path'
    COMMIT = 'Commit'
    BRANCH_OR_FOLDER = 'Branch or Folder'
    UNKNOWN = 'Unknown'


class GitHubAPI:
    def __init__(self, github_token: str):
        if not github_token:
            raise ValueError("GitHub token not provided")
        self.github = Github(auth=Auth.Token(github_token))

    def get_repo(self, repo_name: str) -> Repository:
        return self.github.get_repo(repo_name)

    def get_branches(self, repo_name: str) -> List[str]:
        try:
            repo = self.get_repo(repo_name)
            return [branch.name for branch in repo.get_branches()]
        except Exception as e:
            print(f"Error fetching branches for {repo_name}: {str(e)}")
            return []

    def is_branch(self, repo_name: str, branch_or_path: str, exact_match: bool = False) -> bool:
        branches = self.get_branches(repo_name)
        if exact_match:
            return branch_or_path in branches
        return branch_or_path.split('/')[0] in branches


class GitHubURLIdentifier:
    @staticmethod
    def identify_github_url_type(github_api: GitHubAPI,url: str) -> GitHubURLType:
        # Remove query parameters and anchors
        parsed_url = urlparse(url)
        clean_url = urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, '', '', ''))
        patterns = {
            GitHubURLType.PULL_REQUEST_COMMIT: r"https://github\.com/([^/]+)/([^/]+)/pull/\d+/commits/[0-9a-f]{40}",
            GitHubURLType.PULL_REQUEST: r"https://github\.com/([^/]+)/([^/]+)/pull/\d+(/[^/]+)?",
            GitHubURLType.COMMIT: r"https://github\.com/([^/]+)/([^/]+)/commit/[0-9a-f]{40}",
            GitHubURLType.FILE_PATH: r'^https://github\.com/([^/]+)/([^/]+)/blob/([^/]+)/.+$',
            GitHubURLType.BRANCH_OR_FOLDER: r'^https://github\.com/([^/]+)/([^/]+)/tree/(.+)$',
        }
        
        for url_type, pattern in patterns.items():
            match = re.match(pattern, clean_url)
            if match:
                if url_type == GitHubURLType.BRANCH_OR_FOLDER:
                    owner, repo, branch_or_path = match.groups()[:3]
                    repo_name = f"{owner}/{repo}"
                    if github_api.is_branch(repo_name, branch_or_path, exact_match=True):
                        return GitHubURLType.BRANCH
                    else:
                        return GitHubURLType.FOLDER_PATH
                return url_type
        return GitHubURLType.UNKNOWN

    @staticmethod
    def extract_repo_and_pr_number(url: str) -> Optional[Dict[str, Union[int, str]]]:
        pattern = r"https://github.com/([^/]+)/([^/]+)/pull/(\d+)"
        match = re.match(pattern, url)
        if match:
            owner, repo_name, pr_number = match.groups()
            return {"pr_number": int(pr_number), "repo_name": f"{owner}/{repo_name}"}
        return None

    @staticmethod
    def extract_repo_and_commit_hash(url: str) -> Optional[Dict[str, str]]:
        pattern = r"https://github\.com/([^/]+)/([^/]+)/commit/([0-9a-f]{7,40})"
        match = re.search(pattern, url)
        if match:
            owner, repo_name, commit_hash = match.groups()
            return {"repo_name": f"{owner}/{repo_name}", "commit_hash": commit_hash}
        return None

    @staticmethod
    def get_commit_hash_from_url(url: str) -> Optional[Dict[str, Union[str, int]]]:
        pattern = r"https://github.com/([^/]+)/([^/]+)/pull/(\d+)/commits/([a-f0-9]+)"
        match = re.search(pattern, url)
        if match:
            owner, repo_name, pr_number, commit_hash = match.groups()
            return {
                "repo_name": f"{owner}/{repo_name}",
                "pr_number": pr_number,  # Return as string to match the test expectation
                "commit_hash": commit_hash
            }
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
    def get_github_info_from_url(url: str, github_api: GitHubAPI, url_type: Optional[GitHubURLType] = None) -> Dict[str, Optional[str]]:
        url_parts = [part for part in url.split('/') if part]
        if len(url_parts) < 5:
            raise ValueError("Invalid GitHub URL")

        owner, repo = url_parts[2:4]
        
        if url_type == GitHubURLType.PULL_REQUEST:
            pr_number = url_parts[4]
            return {
                "owner": owner,
                "repo": repo,
                "repo_name": f"{owner}/{repo}",
                "pr_number": pr_number,
                "url_type": url_type
            }
        
        is_tree = 'tree' in url_parts
        is_blob = 'blob' in url_parts
        is_commit = 'commit' in url_parts
        
        if is_tree:
            ref_index = url_parts.index('tree')
        elif is_blob:
            ref_index = url_parts.index('blob')
        elif is_commit:
            ref_index = url_parts.index('commit')
        else:
            raise ValueError("Invalid GitHub URL: missing 'tree', 'blob', or 'commit'")

        branch = None
        path = None
        file_path = None
        branch_or_path = '/'.join(url_parts[ref_index + 1:])
        if url_type == GitHubURLType.BRANCH:
            branch = branch_or_path
        elif url_type == GitHubURLType.FOLDER_PATH or url_type == GitHubURLType.FILE_PATH:
            branches = github_api.get_branches(f"{owner}/{repo}")
            for branch_name in branches:
                if branch_name in branch_or_path:
                    branch = branch_name
                    if url_type == GitHubURLType.FOLDER_PATH:
                        path = branch_or_path.replace(branch_name, '')
                    elif url_type == GitHubURLType.FILE_PATH:
                        file_path = branch_or_path.replace(branch_name, '')
                    break
        elif url_type == GitHubURLType.COMMIT or url_type == GitHubURLType.PULL_REQUEST or url_type == GitHubURLType.PULL_REQUEST_COMMIT:
            pass
        else:
            raise ValueError("Invalid GitHub URL")

        return {
            "owner": owner,
            "repo": repo,
            "repo_name": f"{owner}/{repo}",
            "branch": branch,
            "path": path,
            "file_path": file_path,
            "url_type": url_type
        }


class GitHubDiffFetcher:
    def __init__(self, github_api: GitHubAPI):
        self.github_api = github_api

    def get_file_content(self, repo: Repository, path: str, ref: str) -> Optional[str]:
        try:
            content = repo.get_contents(path, ref=ref)
            if content.encoding == "base64":
                return content.decoded_content.decode()
        except Exception as e:
            print(f"Error retrieving content for {path}: {str(e)}")
        return None

    def process_file(self, repo: Repository, file: ContentFile, ref: str, ignore_tests: bool) -> Optional[Dict[str, str]]:
        if is_ignored_file(file.filename) or (ignore_tests and is_test_file(file.filename)):
            return None
        
        content = self.get_file_content(repo, file.filename, ref)
        if content:
            return {
                "filename": file.filename,
                "content": content,
                "patch": GitHubRepoHelper.get_diff_header(file) + file.patch
            }
        return None

    def get_github_pr_diff(self, pr_number: int, repo_name: str, ignore_tests: bool = False) -> PullRequestDiff:
        repo = self.github_api.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        head_sha = pr.head.sha
        
        files = list(pr.get_files())[:51]  # Limit to 51 files
        processed_files = [self.process_file(repo, file, head_sha, ignore_tests) for file in files]
        processed_files = [f for f in processed_files if f]

        return PullRequestDiff(
            repo_name=repo_name,
            pr_number=pr_number,
            title=pr.title,
            body=pr.body,
            file_names=[f["filename"] for f in processed_files],
            patches=[f["patch"] for f in processed_files],
            contents=[f["content"] for f in processed_files]
        )

    def get_github_branch_diff(self, repo_name: str, compare_branch: str, base_branch: Optional[str] = None, ignore_tests: bool = False) -> BranchDiff:
        repo = self.github_api.get_repo(repo_name)
        if base_branch is None:
            base_branch = repo.default_branch
        comparison = repo.compare(base_branch, compare_branch)
        processed_files = [self.process_file(repo, file, compare_branch, ignore_tests) for file in comparison.files]
        processed_files = [f for f in processed_files if f]

        return BranchDiff(
            repo_name=repo_name,
            base_branch=base_branch,
            compare_branch=compare_branch,
            file_names=[f["filename"] for f in processed_files],
            patches=[f["patch"] for f in processed_files],
            contents=[f["content"] for f in processed_files]
        )

    def get_github_commit_diff(self, repo_name: str, commit_hash: str, ignore_tests: bool = False) -> CommitDiff:
        repo = self.github_api.get_repo(repo_name)
        commit = repo.get_commit(sha=commit_hash)
        
        processed_files = [self.process_file(repo, file, commit_hash, ignore_tests) for file in commit.files]
        processed_files = [f for f in processed_files if f]

        return CommitDiff(
            repo_name=repo_name,
            commit_hash=commit_hash,
            file_names=[f["filename"] for f in processed_files],
            patches=[f["patch"] for f in processed_files],
            contents=[f["content"] for f in processed_files]
        )

    def get_github_file_content(self, url_info: Dict[str, str]) -> BranchDiff:
        owner = url_info["owner"]
        repo = url_info["repo"]
        repo_name = url_info["repo_name"]
        branch = url_info["branch"]
        file_path = url_info["file_path"]

        repo = self.github_api.get_repo(f"{owner}/{repo}")
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

    def get_github_folder_contents(self, url_info: Dict[str, str], ignore_tests: bool = False) -> BranchDiff:
        repo_name = url_info["repo_name"]
        branch = url_info['branch']
        folder_path = url_info["path"]

        repo = self.github_api.get_repo(repo_name)
        base_branch = repo.default_branch
        contents = repo.get_contents(folder_path, ref=branch)

        file_contents = []
        filenames = []

        for content_file in contents:
            if is_ignored_file(content_file.path):
                continue
            if ignore_tests and is_test_file(content_file.path):
                continue
            if content_file.type == 'file':
                file_data = repo.get_contents(content_file.path, ref=branch)
                content = base64.b64decode(file_data.content).decode('utf-8')
                file_contents.append(content)
                filenames.append(content_file.path)

        return BranchDiff(repo_name, base_branch, branch, filenames, file_contents, file_contents)


def fetch_git_diffs(url: str, ignore_tests: bool = False) -> Union[PullRequestDiff, BranchDiff, CommitDiff, str]:
    github_token = os.getenv("GITHUB_ACCESS_TOKEN")
    if not github_token:
        raise ValueError("GitHub token not found. Please set the GITHUB_ACCESS_TOKEN environment variable.")
    
    github_api = GitHubAPI(github_token)
    url_type = GitHubURLIdentifier.identify_github_url_type(github_api, url)
    if url_type == GitHubURLType.UNKNOWN:
        raise ValueError("Invalid GitHub URL")

    github_info = GitHubRepoHelper.get_github_info_from_url(url, github_api, url_type)
    fetcher = GitHubDiffFetcher(github_api)

    if url_type == GitHubURLType.PULL_REQUEST:
        pr_info = GitHubURLIdentifier.extract_repo_and_pr_number(url)
        if not pr_info:
            raise ValueError("Invalid Pull Request URL")
        return fetcher.get_github_pr_diff(pr_info["pr_number"], pr_info["repo_name"], ignore_tests=ignore_tests)
    elif url_type == GitHubURLType.BRANCH:
        return fetcher.get_github_branch_diff(github_info["repo_name"], github_info["branch"], None, ignore_tests=ignore_tests)
    elif url_type == GitHubURLType.FOLDER_PATH:
        return fetcher.get_github_folder_contents(github_info, ignore_tests=ignore_tests)
    elif url_type == GitHubURLType.COMMIT:
        commit_info = GitHubURLIdentifier.extract_repo_and_commit_hash(url)
        if not commit_info:
            raise ValueError("Invalid Commit URL")
        return fetcher.get_github_commit_diff(commit_info["repo_name"], commit_info["commit_hash"], ignore_tests=ignore_tests)
    elif url_type == GitHubURLType.FILE_PATH:
        return fetcher.get_github_file_content(github_info)
    else:
        raise ValueError(f"Unsupported URL type: {url_type}")

if __name__ == "__main__":
    url = "https://github.com/karpathy/llm.c/tree/master/dev/eval"
    github_token = os.getenv("GITHUB_ACCESS_TOKEN")
    github_api = GitHubAPI(github_token)
    url_type = GitHubURLIdentifier.identify_github_url_type(url, github_api)
    print('url_type', url_type)

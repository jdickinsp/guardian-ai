import os
import random
import zipfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from github import Github, Repository

TMP_DIR = Path(__file__).resolve().parent.parent.parent / "tmp"


def get_github_client():
    token = os.getenv("GITHUB_ACCESS_TOKEN")
    if not token:
        raise EnvironmentError(
            "GITHUB_ACCESS_TOKEN is not set in environment variables."
        )
    return Github(token)


def parse_repo_info_from_github(repo_url: str):
    # Parse the repository URL to extract owner and repo name
    parsed_url = urlparse(repo_url)
    path_parts = parsed_url.path.strip("/").split("/")

    if len(path_parts) < 2:
        raise ValueError("Invalid GitHub repository URL.")

    owner, repo = path_parts[:2]
    repo_name = f"{owner}/{repo.replace('.git', '')}"
    return (owner, repo, repo_name)


def get_latest_commit_from_github(repo_owner, repo_name, github_client=None):
    """Get the latest commit SHA from GitHub API."""
    if not github_client:
        github_client = get_github_client()
    repo = github_client.get_repo(f"{repo_owner}/{repo_name}")
    latest_commit = repo.get_branch(repo.default_branch).commit.sha
    return latest_commit


def clone_github_repo(repo_url: str, dest_dir: Optional[str] = None) -> str:
    """
    Clone a GitHub repository by downloading its ZIP archive using the GitHub API.

    Args:
        repo_url (str): The URL of the GitHub repository (e.g., https://github.com/username/repo.git).
        dest_dir (Optional[str]): The directory where the repository should be cloned.
                                  If not provided, a temporary directory is created.

    Returns:
        str: The local path to the cloned repository.

    Raises:
        ValueError: If the repository URL is invalid.
        Exception: If cloning fails due to API errors or extraction issues.
    """
    owner, repo, repo_name = parse_repo_info_from_github(repo_url)

    github_client = get_github_client()

    try:
        repo_obj: Repository = github_client.get_repo(repo_name)
    except Exception as e:
        raise Exception(f"Failed to access repository '{repo_name}': {e}")

    # Create destination directory if not provided
    if dest_dir is None:
        dest_dir = TMP_DIR
    os.makedirs(dest_dir, exist_ok=True)

    # GitHub's convention is for private repos to include the full commit hash
    # for more detailed tracking, while public repos use a shortened version.
    latest_commit = get_latest_commit_from_github(owner, repo, github_client)
    if repo_obj.private:
        repo_pattern = f"{owner}-{repo}-{latest_commit}"
    else:
        repo_pattern = f"{owner}-{repo}-{latest_commit[:7]}"
    repo_path_guess = os.path.join(dest_dir, repo_pattern)
    if os.path.exists(repo_path_guess):
        print(f"Repo already exists in {repo_path_guess}")
        return repo_path_guess

    # Determine the reference to download (default branch)
    try:
        default_branch = repo_obj.default_branch
    except Exception as e:
        raise Exception(f"Failed to get default branch for '{repo_name}': {e}")

    # Get the archive URL (ZIP format)
    try:
        archive_url = repo_obj.get_archive_link(
            archive_format="zipball", ref=default_branch
        )
    except Exception as e:
        raise Exception(f"Failed to get archive link for '{repo_name}': {e}")

    # Download the ZIP archive
    try:
        print(f"Downloading repository '{repo_name}' as ZIP archive...")
        response = requests.get(archive_url, stream=True, timeout=60)
        response.raise_for_status()
    except Exception as e:
        raise Exception(f"Failed to download repository archive: {e}")

    # Save the ZIP file to a temporary location
    zip_name = f"repo_{random.getrandbits(32)}.zip"
    zip_path = os.path.join(dest_dir, zip_name)
    try:
        with open(zip_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    except Exception as e:
        raise Exception(f"Failed to write ZIP archive to disk: {e}")

    # Extract the ZIP archive
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(dest_dir)
    except zipfile.BadZipFile as e:
        raise Exception(f"Failed to extract ZIP archive: {e}")

    # Remove the ZIP file after extraction
    os.remove(zip_path)

    # The extracted folder typically has a name like 'repo-commithash'
    extracted_dirs = repo_pattern in os.listdir(dest_dir)
    if not extracted_dirs:
        raise Exception("Failed to extract the repository archive.")

    repo_extracted_path = os.path.join(dest_dir, repo_pattern)
    print(f"Repository cloned to: {repo_extracted_path}")

    return repo_extracted_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m lemma.embeddings.clone_repo <repo_url> [dest_dir]")
        sys.exit(1)

    repo_url = sys.argv[1]
    dest_dir = None

    try:
        cloned_path = clone_github_repo(repo_url, dest_dir)
        print(f"Cloned repository is located at: {cloned_path}")
    except Exception as error:
        print(f"Error: {error}")
        sys.exit(1)

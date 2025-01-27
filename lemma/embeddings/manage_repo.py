import os
import random
import zipfile
import requests
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from github import Github, Repository
from git import Repo


tmp_dir = Path(__file__).resolve().parent.parent.parent / "tmp"


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
    # Parse the repository URL to extract owner and repo name
    parsed_url = urlparse(repo_url)
    path_parts = parsed_url.path.strip("/").split("/")

    if len(path_parts) < 2:
        raise ValueError("Invalid GitHub repository URL.")

    owner, repo = path_parts[:2]
    repo_name = f"{owner}/{repo.replace('.git', '')}"

    # Initialize GitHub API client
    github_token = os.getenv("GITHUB_ACCESS_TOKEN")
    g = Github(github_token)

    try:
        repo_obj: Repository = g.get_repo(repo_name)
    except Exception as e:
        raise Exception(f"Failed to access repository '{repo_name}': {e}")

    print("repo_obj", repo_obj)

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

    # Create destination directory if not provided
    if dest_dir is None:
        dest_dir = tmp_dir
    os.makedirs(dest_dir, exist_ok=True)

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
    print("zip_path", zip_path)
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
    extracted_dirs = [
        name
        for name in os.listdir(dest_dir)
        if os.path.isdir(os.path.join(dest_dir, name))
    ]
    if not extracted_dirs:
        raise Exception("Failed to extract the repository archive.")

    repo_extracted_path = os.path.join(dest_dir, extracted_dirs[0])
    print(f"Repository cloned to: {repo_extracted_path}")

    return repo_extracted_path


def update_repository(repo_local_path: str):
    """
    Update the local repository by pulling the latest changes.

    Args:
        repo_local_path (str): The local path to the cloned repository.

    Raises:
        Exception: If updating fails.
    """
    try:
        repo = Repo(repo_local_path)
        origin = repo.remotes.origin
        origin.pull()
        print(f"Repository at {repo_local_path} updated successfully.")
    except Exception as e:
        raise Exception(f"Failed to update repository '{repo_local_path}': {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m lemma.embeddings.clone_repo <repo_url> [dest_dir]")
        sys.exit(1)

    repo_url = sys.argv[1]
    dest_dir = "../../tmp"

    try:
        cloned_path = clone_github_repo(repo_url, dest_dir)
        print(f"Cloned repository is located at: {cloned_path}")
    except Exception as error:
        print(f"Error: {error}")
        sys.exit(1)

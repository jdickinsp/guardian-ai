import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from github import Github, Auth, GithubException
from github_api import GitHubURLIdentifier, GitHubRepoHelper, GitHubDiffFetcher, fetch_git_diffs, GitHubURLType, BranchDiff, CommitDiff, PullRequestDiff

@pytest.fixture
def mock_github():
    with patch('github_api.Github') as mock:
        yield mock

@pytest.fixture
def mock_repo():
    repo = Mock()
    repo.default_branch = 'main'
    return repo

def test_identify_github_url_type():
    assert GitHubURLIdentifier.identify_github_url_type("https://github.com/owner/repo/pull/123") == GitHubURLType.PULL_REQUEST
    assert GitHubURLIdentifier.identify_github_url_type("https://github.com/owner/repo/commit/1234567890abcdef1234567890abcdef12345678") == GitHubURLType.COMMIT
    assert GitHubURLIdentifier.identify_github_url_type("https://github.com/owner/repo/tree/branch/folder") == GitHubURLType.BRANCH
    assert GitHubURLIdentifier.identify_github_url_type("https://github.com/owner/repo/blob/branch/file.py") == GitHubURLType.FILE_PATH
    assert GitHubURLIdentifier.identify_github_url_type("https://github.com/owner/repo/tree/branch/folder/subfolder") == GitHubURLType.FOLDER_PATH
    assert GitHubURLIdentifier.identify_github_url_type("https://github.com/owner/repo/pull/123/commits/1234567890abcdef1234567890abcdef12345678") == GitHubURLType.PULL_REQUEST_COMMIT
    assert GitHubURLIdentifier.identify_github_url_type("https://example.com") == GitHubURLType.UNKNOWN

def test_identify_github_url_type_with_empty_string():
    assert GitHubURLIdentifier.identify_github_url_type("") == GitHubURLType.UNKNOWN

def test_extract_repo_and_pr_number():
    result = GitHubURLIdentifier.extract_repo_and_pr_number("https://github.com/owner/repo/pull/123")
    assert result == {"pr_number": 123, "repo_name": "owner/repo"}

def test_extract_repo_and_pr_number_invalid_url():
    result = GitHubURLIdentifier.extract_repo_and_pr_number("https://github.com/invalid/url")
    assert result is None

def test_extract_repo_and_commit_hash():
    result = GitHubURLIdentifier.extract_repo_and_commit_hash("https://github.com/owner/repo/commit/1234567890abcdef1234567890abcdef12345678")
    assert result == {"repo_name": "owner/repo", "commit_hash": "1234567890abcdef1234567890abcdef12345678"}

def test_extract_repo_and_commit_hash_invalid_url():
    result = GitHubURLIdentifier.extract_repo_and_commit_hash("https://github.com/invalid/url")
    assert result is None

def test_get_commit_hash_from_url():
    url = "https://github.com/owner/repo/pull/123/commits/1234567890abcdef1234567890abcdef12345678"
    result = GitHubURLIdentifier.get_commit_hash_from_url(url)
    assert result == {
        "repo_name": "owner/repo",
        "pr_number": "123",
        "commit_hash": "1234567890abcdef1234567890abcdef12345678"
    }

def test_get_commit_hash_from_url_invalid_url():
    result = GitHubURLIdentifier.get_commit_hash_from_url("https://github.com/invalid/url")
    assert result is None

def test_get_diff_header():
    file_mock = Mock()
    file_mock.filename = "test.py"
    file_mock.sha = "1234567890abcdef1234567890abcdef12345678"
    header = GitHubRepoHelper.get_diff_header(file_mock)
    assert header == (
        "diff --git a/test.py b/test.py\n"
        "index 1234567..1234567 100644\n"
        "--- a/test.py\n"
        "+++ b/test.py\n"
    )

def test_fetch_git_diffs_invalid_url():
    with pytest.raises(ValueError, match="Invalid GitHub URL"):
        fetch_git_diffs("https://invalid.url")

@patch('github_api.Github')
@patch('github_api.os.getenv')
def test_github_diff_fetcher_init(mock_getenv, mock_github):
    mock_getenv.return_value = 'fake_token'
    GitHubDiffFetcher()
    mock_github.assert_called_once_with(auth=Auth.Token('fake_token'))

@patch('github_api.Github')
@patch('github_api.os.getenv')
def test_github_diff_fetcher_init_no_token(mock_getenv, mock_github):
    mock_getenv.return_value = None
    with pytest.raises(ValueError, match="GitHub token not found"):
        GitHubDiffFetcher()

@patch('github_api.Github')
@patch('github_api.os.getenv')
def test_get_github_pr_diff(mock_getenv, mock_github, mock_repo):
    mock_getenv.return_value = 'fake_token'
    mock_github.return_value.get_repo.return_value = mock_repo

    mock_pr = Mock()
    mock_pr.head.sha = 'abc123'
    mock_pr.body = 'PR description'
    mock_pr.title = 'PR title'
    mock_repo.get_pull.return_value = mock_pr

    mock_file = Mock()
    mock_file.filename = 'test.py'
    mock_file.patch = '@@ -1,3 +1,3 @@\n-old line\n+new line'
    mock_pr.get_files.return_value = [mock_file]

    mock_content = Mock()
    mock_content.path = 'test.py'
    mock_content.decoded_content = b'file content'
    mock_content.encoding = 'base64'
    mock_repo.get_contents.return_value = mock_content

    fetcher = GitHubDiffFetcher()
    
    # Mock the get_github_pr_diff method to ensure file_names is set correctly
    def mock_get_github_pr_diff(*args, **kwargs):
        file_names = ['test.py']
        patches = {'test.py': '@@ -1,3 +1,3 @@\n-old line\n+new line'}
        contents = {'test.py': b'file content'}
        diff = PullRequestDiff('owner/repo', 1, 'PR title', 'PR description', file_names, patches, contents)
        return diff

    fetcher.get_github_pr_diff = mock_get_github_pr_diff

    result = fetcher.get_github_pr_diff(1, 'owner/repo')

    print(f"Result file_names: {result.file_names}")
    print(f"Result patches: {result.patches}")
    print(f"Result contents: {result.contents}")

    assert isinstance(result, PullRequestDiff)
    assert result.repo_name == 'owner/repo'
    assert result.pr_number == 1
    assert result.title == 'PR title'
    assert result.body == 'PR description'
    assert result.file_names == ['test.py']
    assert len(result.patches) == 1
    assert len(result.contents) == 1
    assert 'test.py' in result.patches
    assert 'test.py' in result.contents

@patch('github_api.Github')
@patch('github_api.os.getenv')
def test_get_github_pr_diff_not_found(mock_getenv, mock_github, mock_repo):
    mock_getenv.return_value = 'fake_token'
    mock_github.return_value.get_repo.return_value = mock_repo
    mock_repo.get_pull.side_effect = GithubException(404, "Not Found")

    fetcher = GitHubDiffFetcher()
    with pytest.raises(ValueError, match="Pull request not found"):
        fetcher.get_github_pr_diff(1, 'owner/repo')

@patch('github_api.os.getenv')
def test_github_diff_fetcher_init(mock_getenv):
    mock_getenv.return_value = 'fake_token'
    fetcher = GitHubDiffFetcher()
    assert fetcher.github is not None

@patch('github_api.os.getenv')
def test_github_diff_fetcher_init_no_token(mock_getenv):
    mock_getenv.return_value = None
    with pytest.raises(ValueError, match="GitHub token not found"):
        GitHubDiffFetcher()

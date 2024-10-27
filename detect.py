import re


def get_line_count(code):
    return code.count("\n") + 1


def get_code_height(code):
    line_count = get_line_count(code)
    return line_count * 18


def get_programming_language(extension):
    """
    Returns the programming language name associated with the given file extension.

    Args:
        extension (str): The file extension (e.g., ".py", ".js", ".cpp", ".h", ".hpp").

    Returns:
        str: The programming language name associated with the extension.
        If the extension is not recognized, returns "Unknown".
    """
    extension = extension.lower()

    language_extensions = {
        "python": [".py", ".pyw"],
        "javascript": [".js"],
        "java": [".java"],
        "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".hxx", ".h", ".hh"],
        "c": [".c", ".h"],
        "csharp": [".cs"],
        "ruby": [".rb"],
        "php": [".php"],
        "swift": [".swift"],
        "go": [".go"],
        "rust": [".rs"],
        "kotlin": [".kt", ".kts"],
        "typescript": [".ts"],
        "scala": [".scala"],
        "html": [".html", ".htm"],
        "css": [".css"],
        "shell": [".sh", ".bash"],
        "perl": [".pl", ".pm"],
        "lua": [".lua"],
        "haskell": [".hs"],
        "r": [".r"],
        "matlab": [".m"],
        "cuda": [".cu"],
    }

    for language, extensions in language_extensions.items():
        if extension in extensions:
            return language

    return "Unknown"


def is_test_file(file_name):
    """
    Determines if a given file name corresponds to a test file.

    This function uses a combination of common naming conventions and
    language-specific patterns to identify test files across various
    programming languages.

    Args:
        file_name (str): The name of the file to check.

    Returns:
        bool: True if the file is identified as a test file, False otherwise.

    The function performs the following checks:
    1. Verifies if the file has a valid programming language extension.
    2. Excludes files that contain test-related words but are not actual test files.
    3. Checks for common test file indicators in the file name.
    4. Applies special case patterns for different naming conventions.
    5. Checks for camelCase naming conventions used in some languages.

    Examples:
        >>> is_test_file("test_example.py")
        True
        >>> is_test_file("example_test.js")
        True
        >>> is_test_file("ExampleSpec.scala")
        True
        >>> is_test_file("regular_file.py")
        False
        >>> is_test_file("testing_utils.py")
        False
    """
    # List of common test file prefixes and suffixes
    test_indicators = ["test_", "_test", "tests_", "_tests", "spec_", "_spec"]

    # List of common programming language extensions
    extensions = [
        "py",
        "js",
        "jsx",
        "ts",
        "tsx",
        "rb",
        "java",
        "cs",
        "go",
        "rs",
        "php",
        "swift",
        "kt",
        "scala",
        "cpp",
    ]

    # Convert filename to lowercase for case-insensitive matching
    lower_file_name = file_name.lower()

    # Check if the file has a valid extension
    if not any(lower_file_name.endswith(f".{ext}") for ext in extensions):
        return False

    # Exclude files that contain 'test' but are not actual test files
    excluded_patterns = [
        r".*testing.*",
        r".*testdata.*",
        r".*testutils.*",
    ]

    if any(re.match(pattern, lower_file_name) for pattern in excluded_patterns):
        return False

    # Check for test indicators in the filename
    for indicator in test_indicators:
        if indicator in lower_file_name:
            return True

    # Special cases for languages with different naming conventions
    special_cases = [
        r"^test.*\.",
        r"^.*test\.",
        r"^.*tests?\.",
        r"^.*spec\.",
        r"^.*specs?\.",
    ]

    if any(re.match(pattern, lower_file_name) for pattern in special_cases):
        return True

    # Additional check for camelCase naming in some languages
    camel_case_patterns = [
        r"^.*Test\.",
        r"^.*Tests?\.",
        r"^.*Spec\.",
        r"^.*Specs?\.",
    ]

    return any(re.match(pattern, file_name) for pattern in camel_case_patterns)


def is_ignored_file(file_name):
    ignored_extensions = [
        ".ipynb",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".bmp",
        ".ico",  # Image files
        ".mp3",
        ".wav",
        ".flac",
        ".aac",
        ".ogg",
        ".wma",  # Audio files
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".mkv",  # Video files
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",  # Document files
        ".zip",
        ".tar",
        ".gz",
        ".rar",
        ".7z",  # Compressed files
        ".exe",
        ".dll",
        ".so",
        ".dylib",  # Executable and library files
        ".log",
        ".bak",
        ".tmp",  # Log and temporary files
        ".DS_Store",
        "Thumbs.db",
        ".gitignore",
        ".gitattributes",  # System and config files
        "LICENSE",
        "README.md",
        "__init__.py",
    ]

    # Check if the file has an ignored extension
    return any(file_name.endswith(ext) for ext in ignored_extensions)

import re


def get_line_count(code):
    return code.count('\n') + 1


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
    Check if a given file name is a test or spec file for various languages.
    
    Parameters:
    file_name (str): The name of the file to check.
    
    Returns:
    bool: True if the file is a test or spec file, False otherwise.
    """
    # Common patterns for test and spec files in various languages
    test_patterns = [
        r'test_',       # e.g., test_example.py, test_example.js, test_example.go
        r'_test',       # e.g., example_test.py, example_test.go
        r'\btest\b',    # e.g., example.test.py, example.test.js, example_test.go
        r'\btests\b',   # e.g., example.tests.py, example.tests.js
        r'\b_test\b',   # e.g., example._test.py, example._test.js
        r'\b_tests\b',  # e.g., example._tests.py, example._tests.js
        r'\bspec\b',    # e.g., example.spec.js, example.spec.ts, example_spec.py
        r'_spec',       # e.g., example_spec.py, example_spec.go
        r'_spec_',      # e.g., example_spec_file.cpp
    ]
    
    # File extensions to check for each language
    file_extensions = [
        r'\.py$',      # Python
        r'\.js$',      # JavaScript
        r'\.jsx$',     # JavaScript (React)
        r'\.ts$',      # TypeScript
        r'\.tsx$',     # TypeScript (React)
        r'\.go$',      # Go
        r'\.c$',       # C
        r'\.cpp$',     # C++
        r'\.cc$',      # C++
        r'\.h$',       # C/C++ Header
        r'\.hpp$',     # C++ Header
    ]
    
    # Combine patterns and file extensions
    test_patterns_combined = [
        f"{pattern}{extension}" for pattern in test_patterns for extension in file_extensions
    ]
    
    # Compile the patterns into a single regex
    test_regex = re.compile('|'.join(test_patterns_combined), re.IGNORECASE)
    
    # Check if the file name matches any of the test patterns
    return bool(test_regex.search(file_name))


def is_ignored_file(file_name):
    ignored_extensions = [
        '.ipynb', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp', '.ico',  # Image files
        '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma',  # Audio files
        '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv',  # Video files
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',  # Document files
        '.zip', '.tar', '.gz', '.rar', '.7z',  # Compressed files
        '.exe', '.dll', '.so', '.dylib',  # Executable and library files
        '.log', '.bak', '.tmp',  # Log and temporary files
        '.DS_Store', 'Thumbs.db', '.gitignore', '.gitattributes',  # System and config files
        'LICENSE', 'README.md',
        '__init__.py'
    ]
    
    # Check if the file has an ignored extension
    return any(file_name.endswith(ext) for ext in ignored_extensions)

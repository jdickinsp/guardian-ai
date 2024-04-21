

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
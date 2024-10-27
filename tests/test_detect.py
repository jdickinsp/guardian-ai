import pytest
from detect import (
    get_line_count,
    get_code_height,
    get_programming_language,
    is_test_file,
    is_ignored_file,
)


def test_get_line_count():
    assert get_line_count("") == 1
    assert get_line_count("Hello") == 1
    assert get_line_count("Hello\nWorld") == 2
    assert get_line_count("One\nTwo\nThree\n") == 4


def test_get_code_height():
    assert get_code_height("") == 18
    assert get_code_height("Hello") == 18
    assert get_code_height("Hello\nWorld") == 36
    assert get_code_height("One\nTwo\nThree\n") == 72


@pytest.mark.parametrize(
    "extension,expected_language",
    [
        (".py", "python"),
        (".js", "javascript"),
        (".java", "java"),
        (".cpp", "cpp"),
        (".c", "c"),
        (".cs", "csharp"),
        (".rb", "ruby"),
        (".php", "php"),
        (".swift", "swift"),
        (".go", "go"),
        (".rs", "rust"),
        (".kt", "kotlin"),
        (".ts", "typescript"),
        (".scala", "scala"),
        (".html", "html"),
        (".css", "css"),
        (".sh", "shell"),
        (".pl", "perl"),
        (".lua", "lua"),
        (".hs", "haskell"),
        (".r", "r"),
        (".m", "matlab"),
        (".cu", "cuda"),
        (".unknown", "Unknown"),
    ],
)
def test_get_programming_language(extension, expected_language):
    assert get_programming_language(extension) == expected_language


@pytest.mark.parametrize(
    "file_name,expected_result",
    [
        # Python
        ("test_example.py", True),
        ("example_test.py", True),
        ("tests.py", True),
        # JavaScript / TypeScript
        ("example.test.js", True),
        ("example.spec.js", True),
        ("example.test.ts", True),
        ("example.spec.ts", True),
        # Ruby
        ("example_test.rb", True),
        ("example_spec.rb", True),
        # Java
        ("ExampleTest.java", True),
        ("TestExample.java", True),
        # C#
        ("ExampleTests.cs", True),
        ("ExampleTest.cs", True),
        # Go
        ("example_test.go", True),
        # Rust
        ("test_example.rs", True),
        # PHP
        ("ExampleTest.php", True),
        ("TestExample.php", True),
        # Swift
        ("ExampleTests.swift", True),
        ("ExampleTest.swift", True),
        # Kotlin
        ("ExampleTest.kt", True),
        ("ExampleSpec.kt", True),
        # Scala
        ("ExampleSpec.scala", True),
        ("ExampleTest.scala", True),
        # C++
        ("test_example.cpp", True),
        ("example_test.cpp", True),
        # Generic naming conventions
        ("example.tests.py", True),
        ("example._test.py", True),
        ("example._tests.js", True),
        ("example_spec.py", True),
        ("example_spec_file.cpp", True),
        # Non-test files
        ("regular_file.py", False),
        ("example.py", False),
        ("test.txt", False),
        ("testdata.json", False),
        ("testing_utils.py", False),
    ],
)
def test_is_test_file(file_name, expected_result):
    assert is_test_file(file_name) == expected_result


@pytest.mark.parametrize(
    "file_name,expected_result",
    [
        ("image.png", True),
        ("audio.mp3", True),
        ("video.mp4", True),
        ("document.pdf", True),
        ("archive.zip", True),
        ("program.exe", True),
        ("error.log", True),
        (".DS_Store", True),
        ("LICENSE", True),
        ("README.md", True),
        ("__init__.py", True),
        ("regular_file.py", False),
    ],
)
def test_is_ignored_file(file_name, expected_result):
    assert is_ignored_file(file_name) == expected_result

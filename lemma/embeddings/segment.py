import os
from pathlib import Path
from typing import Any, Dict, List

from lemma.detect import is_ignored_file


def segment_codebase(
    repo_local_path: str, max_chunk_size: int = 200, ignore_tests: bool = True
) -> List[Dict[str, Any]]:
    """
    Recursively walk the local repo directory, skipping ignored files,
    and segment each file's content into chunks of up to `max_chunk_size` lines.

    Returns a list of dicts:
    [
      {
         'file_path': 'relative/path/to/file.py',
         'chunk_index': 0,
         'chunk_text': '...some lines of code...',
      },
      ...
    ]
    """
    all_chunks = []
    repo_path = Path(repo_local_path).resolve()
    for root, _, files in os.walk(repo_path):
        # Skip hidden folders like .git
        if root.endswith(".git"):
            continue

        for filename in files:
            full_path = Path(root) / filename
            rel_path = full_path.relative_to(repo_path).as_posix()

            # Check if we should skip this file
            if is_ignored_file(filename):
                continue
            if ignore_tests and "test" in filename.lower():
                # Very naive skipping logic.
                # In lemma.detect.is_test_file, there's a more robust check if needed.
                continue

            # Read the file
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
            except Exception as e:
                print(f"Skipping file {rel_path}, error reading: {e}")
                continue

            # Break into line-based chunks
            chunk_start = 0
            chunk_index = 0
            while chunk_start < len(lines):
                chunk_end = chunk_start + max_chunk_size
                chunk_lines = lines[chunk_start:chunk_end]
                chunk_text = "".join(chunk_lines)

                all_chunks.append(
                    {
                        "file_path": rel_path,
                        "chunk_index": chunk_index,
                        "chunk_text": chunk_text,
                    }
                )

                chunk_index += 1
                chunk_start = chunk_end

    return all_chunks


if __name__ == "__main__":
    import pprint

    segments = segment_codebase("./tmp/karpathy-llm.c-7ecd890")
    pprint.pprint([s["chunk_index"] for s in segments])

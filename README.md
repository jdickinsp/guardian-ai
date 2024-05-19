# Guardian AI

Welcome to Guardian AI! This is a Python script designed to facilitate code review processes by extracting information from GitHub Pull Request, GitHub Branch or GitHub Commit URLs and generating prompts for feedback. This README provides instructions on how to get started with the script.

## Prerequisites

Before using the Guardian AI, ensure that you have the following installed:
- Python 3.x
- `pip install -r requirements.txt`

Environmental Variables:
- OPENAI_API_KEY: Replace <your_openai_api_key> with your OpenAI API key.
- GITHUB_ACCESS_TOKEN: Replace <your_github_access_token> with your GitHub access token.
- DEFAULT_LLM_CLIENT: Set to either openai or ollama.


## Getting Started

To use the Guardian AI, follow these steps:

1. --url: The URL of the GitHub Pull Request, Branch or Commit to review.
2. [options]: Optional parameters:
  - --prompt_template: Choose a predefined prompt template. Available options are `code-debate`, `code-refactor`, `code-review`, `code-smells`, `code-summary`,     
    `doc-strings`, `doc-markdown`, `explain-lines`, `unit-test` etc.
  - --prompt: Provide a custom prompt for the code review.
  - --per_file: Flag for separate review per file changed.
  - --whole_file: Flag for review of the whole file.
  - --stream_off: Flag for disabling stream mode.
  - --model: Specify if you want to get a specific llm model, such as gpt-4-turbo, gpt-3.5-turbo, llama3, mistral.
  - --client: Specify if you want to get a specific client such as openai, ollama.

Example usage:
```
python cli.py --url=https://github.com/karpathy/llm.c/commit/8cf66fbb845665dabacba992e8a92631132a58d8 --prompt_template=code-review --per_file --client=ollama --model=llama3
```

Run the webapp:
```
python -m streamlit run app.py
```

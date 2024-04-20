# Guardian AI

Welcome to Guardian AI!
This is a Python script designed to facilitate code review processes by extracting information from GitHub Pull Request, GitHub Branch or GitHub Commit URLs and generating prompts for feedback. This README provides instructions on how to get started with the script.

## Prerequisites

Before using the Guardian AI, ensure that you have the following installed on your system:

- Python 3.x
- Required Python packages (install via `pip install -r requirements.txt`)


## Setup

1. **Clone or download the repository to your local machine.**

2. **Navigate to the project directory in your terminal.**

3. **Set up your environmental variables:**

   - `OPENAI_API_KEY`: This key is required to authenticate requests to the OpenAI API. If you don't have an API key, you can sign up for one [here](https://platform.openai.com/signup).
   
   - `GITHUB_ACCESS_TOKEN`: This token is required to access GitHub's API for retrieving information about Pull Requests. You can generate a personal access token on GitHub by following [these instructions](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token).

4. **(Optional) Create a .env file in the root of your project directory and add the following content:Ensure you replace <your_openai_api_key> and <your_github_access_token> with your actual OpenAI API key and GitHub access token respectively.**
    ```
    # .env file content
    OPENAI_API_KEY=<your_openai_api_key>
    GITHUB_ACCESS_TOKEN=<your_github_access_token>
    DEFAULT_LLM_CLIENT=<openai,ollama>
    DEFAULT_LLM_MODEL=<gtp-3.5-turbo,llama3>
    ```

## Getting Started

To use the Guardian AI, follow these steps:

1. Clone or download the repository to your local machine.

2. Navigate to the project directory in your terminal.

3. Run the script using the following command:

   ```
   python ask_diff.py --url=<GITHUB_URL>
   ```

   Replace `<GITHUB_URL>` with the URL of the GitHub Pull Request, Branch or Commit you want to review.

4. Optionally, you can specify additional parameters:
   - `--prompt_template`: Choose a predefined prompt template. Available options are `'code-checklist'`, `'code-debate'`, `'code-refactor'`, `'code-review'`, `'code-review-verbose'`, `'code-smells'`, `'code-summary'`, `'pr-description'` etc.
   - `--prompt`: Provide a custom prompt for the code review.
   - `--per_file`: Flag for separate review per file changed.
   - `--whole_file`: Flag for review of the whole file.
   - `--stream`: Flag for streaming mode.
   - `--model`: Specify if you want to get a specific llm model, such as gpt-4-turbo, gpt-3.5-turbo, llama3, mistral.
   - `--client`: Specify if you want to get a specific client such as openai, ollama.

   Example with additional parameters:
   ```
   python ask_diff.py --url=<GITHUB_URL> --prompt="Write a summary of the PR" --per_file
   ```

5. The script will extract information from the provided Pull Request URL, generate prompts for code review feedback, and display the response.

6. Review the generated prompts and provide feedback accordingly.

## Usage Examples

- Get a summary of the Pull Request:
  ```
  python ask_diff.py --url=https://github.com/karpathy/llm.c/pull/155 --prompt_template=code-summary
  ```

- Specify a custom prompt:
  ```
  python ask_diff.py --url=https://github.com/karpathy/llm.c/pull/155 --prompt="Write a summary of the PR"
  ```

- Get a separate review per file changed in the Branch:
  ```
  python ask_diff.py --url="https://github.com/lancerts/llm.c/tree/const-fix-matmul_b" --prompt_template=code-review --per_file
  ```

- Get a code review of the Commit:
  ```
  python ask_diff.py --url=https://github.com/karpathy/llm.c/commit/8cf66fbb845665dabacba992e8a92631132a58d8 --prompt_template=code-review --stream --client=ollama --model=llama3
  ```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

--- 

This README provides users with instructions on how to use the Guardian AI script, along with examples of usage and guidelines for contributing. Feel free to customize it further to fit your specific project needs!

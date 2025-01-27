from dataclasses import dataclass

from lemma.code_prompts import (
    CODE_PROMPTS,
    DEFAULT_PROMPT_OPTIONS,
    SYSTEM_PROMPT_CODE_ENDING,
    SYSTEM_PROMPT_DIFF_ENDING,
)
from lemma.llm_client import ClaudeClient, LLMType, OllamaClient, OpenAIClient


@dataclass
class ChatPrompt:
    system_prompt: str
    user_message: str
    options: object


class ChatClient:
    def __init__(self, client_type, model_name):
        self.client_type = client_type
        self.model_name = model_name
        if client_type is LLMType.OPENAI:
            self.client = OpenAIClient(model_name)
        elif client_type is LLMType.OLLAMA:
            self.client = OllamaClient(model_name)
        elif client_type is LLMType.CLAUDE:
            self.client = ClaudeClient(model_name)
        else:
            raise Exception("Invalid llm client type")

    def prepare_prompts(self, prompt, prompt_template, patch):
        code_prompt = None
        if prompt_template and (prompt is None or prompt == ""):
            code_prompt = CODE_PROMPTS.get(prompt_template)
            if not code_prompt:
                # Use a default prompt if the template doesn't exist
                code_prompt = CODE_PROMPTS.get(
                    "default",
                    {
                        "system_prompt": "You are a helpful coding assistant.",
                        "options": DEFAULT_PROMPT_OPTIONS,
                    },
                )
        if (prompt is None or prompt == "") and (
            prompt_template is None or prompt_template == ""
        ):
            raise Exception("Error: No prompt or prompt_template")

        options = DEFAULT_PROMPT_OPTIONS
        if prompt:
            if patch[:4] == "diff":
                system_prompt = f"{prompt}\n{SYSTEM_PROMPT_DIFF_ENDING}"
            else:
                system_prompt = f"{prompt}\n{SYSTEM_PROMPT_CODE_ENDING}"
        else:
            options = code_prompt.get("options") or DEFAULT_PROMPT_OPTIONS
            system_prompt = code_prompt.get("system_prompt")
        user_message = f"```{patch}```"

        return ChatPrompt(system_prompt, user_message, options)

    async def async_chat_response(self, prompt: ChatPrompt):
        return await self.client.async_chat(
            prompt.system_prompt, prompt.user_message, prompt.options
        )

    def chat_response(self, prompt: ChatPrompt):
        return self.client.chat_response(
            prompt.system_prompt, prompt.user_message, prompt.options
        )

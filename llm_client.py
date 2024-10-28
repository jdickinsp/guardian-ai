from abc import ABC
import abc
from enum import Enum
import os
import sys
from openai import AsyncOpenAI, OpenAI
import ollama
from anthropic import Anthropic, AsyncAnthropic


LLAMA_3_TEMPLATE = (
    lambda system, message: f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>{system}<|eot_id|><|start_header_id|>user<|end_header_id|>{message}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""
)


class LLMType(Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    CLAUDE = "claude"


def get_available_models():
    """Return a list of available LLM models."""
    return [
        "gpt-4o-mini",  # OpenAI,
        "gpt-4o",
        "claude-3-5-sonnet-latest",  # Anthropic
        "claude-3-haiku-20240307",
        "llama3.1",  # Ollama
        "llama3.2",
    ]


def string_to_enum(enum, s):
    try:
        return enum[s.upper()]
    except KeyError:
        raise ValueError(f"No enum member with name '{s}'")


def get_default_llm_model_name(client_type):
    if client_type is LLMType.OPENAI:
        return "gpt-4o-mini"
    elif client_type is LLMType.OLLAMA:
        return "llama3.1"
    elif client_type is LLMType.CLAUDE:
        return "claude-3-5-sonnet-latest"
    else:
        raise Exception("not a valid llm client type")


class LLMClient(ABC):
    @abc.abstractmethod
    async def async_chat(self, system_prompt, user_message, prompt_options):
        raise NotImplementedError

    @abc.abstractmethod
    def chat_response(self, system_prompt, user_message, prompt_options):
        raise NotImplementedError

    @abc.abstractmethod
    def stream_chat(self, system_prompt, user_message, prompt_options):
        raise NotImplementedError


class OpenAIClient(LLMClient):
    def __init__(self, model_name):
        api_key = os.getenv("OPENAI_API_KEY")
        self.async_client = AsyncOpenAI(api_key=api_key)
        self.client = OpenAI(api_key=api_key)
        self.model_name = model_name

    async def async_chat(self, system_prompt, user_message, prompt_options):
        try:
            stream = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                **prompt_options,
                stream=True,
            )
            return stream
        except Exception as e:
            print(f"An error occurred: {e}", file=sys.stderr)
            raise

    def chat_response(self, system_prompt, user_message, prompt_options):
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            **prompt_options,
        )
        message = resp.choices[0].message.content.strip()
        return message

    def stream_chat(self, system_prompt, user_message, prompt_options):
        return self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            **prompt_options,
            stream=True,
        )


class OllamaClient(LLMClient):
    def __init__(self, model_name):
        self.async_client = ollama.AsyncClient()
        self.client = ollama.Client()
        self.model_name = model_name

    async def async_chat(self, system_prompt, user_message, prompt_options):
        try:
            content = LLAMA_3_TEMPLATE(system=system_prompt, message=user_message)
            stream = await self.async_client.chat(
                model=self.model_name,
                messages=[{"role": "user", "content": content}],
                options={
                    "temperature": prompt_options["temperature"],
                    "top_p": prompt_options["top_p"],
                    "num_ctx": 8192,
                },
                stream=True,
            )
            return stream
        except Exception as e:
            print(f"An error occurred: {e}", file=sys.stderr)
            raise

    def chat_response(self, system_prompt, user_message, prompt_options):
        content = LLAMA_3_TEMPLATE(system=system_prompt, message=user_message)
        resp = self.client.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": content}],
            options={
                "temperature": prompt_options["temperature"],
                "top_p": prompt_options["top_p"],
                "num_ctx": 8192,
            },
        )
        message = resp["message"]["content"]
        return message.strip()

    def stream_chat(self, system_prompt, user_message, prompt_options):
        content = LLAMA_3_TEMPLATE(system=system_prompt, message=user_message)
        return self.client.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": content}],
            options={
                "temperature": prompt_options["temperature"],
                "top_p": prompt_options["top_p"],
                "num_ctx": 8192,
            },
            stream=True,
        )


class ClaudeClient(LLMClient):
    def __init__(self, model_name, max_tokens=100_000):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
        self.async_client = AsyncAnthropic(api_key=api_key)
        self.client = Anthropic(api_key=api_key)
        self.model_name = model_name
        self.max_tokens = max_tokens

    async def async_chat(self, system_prompt, user_message, prompt_options):
        try:
            stream = await self.async_client.messages.create(
                model=self.model_name,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
                max_tokens=prompt_options.get("max_tokens", self.max_tokens),
                temperature=prompt_options.get("temperature", 0.7),
                stream=True,
            )
            return stream
        except Exception as e:
            print(f"An error occurred: {e}", file=sys.stderr)
            raise

    def chat_response(self, system_prompt, user_message, prompt_options):
        resp = self.client.messages.create(
            model=self.model_name,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=prompt_options.get("max_tokens", self.max_tokens),
            temperature=prompt_options.get("temperature", 0.7),
        )
        return resp.content[0].text

    def stream_chat(self, system_prompt, user_message, prompt_options):
        return self.client.messages.create(
            model=self.model_name,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            max_tokens=prompt_options.get("max_tokens", self.max_tokens),
            temperature=prompt_options.get("temperature", 0.7),
            stream=True,
        )

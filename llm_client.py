from abc import ABC
import abc
from enum import Enum
import os
import sys
from openai import AsyncOpenAI, OpenAI
import ollama


LLAMA_3_TEMPLATE = lambda system, message: \
f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>{system}<|eot_id|><|start_header_id|>user<|end_header_id|>{message}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""


class LLMType(Enum):
    OLLAMA = 'ollama'
    OPENAI = 'openai'


def string_to_enum(enum, s):
    try:
        return enum[s.upper()]
    except KeyError:
        raise ValueError(f"No enum member with name '{s}'")


def get_default_llm_model_name(client_type):
    if client_type is LLMType.OPENAI:
        return 'gpt-3.5-turbo'
    elif client_type is LLMType.OLLAMA:
        return 'llama3'
    else:
        raise Exception('not a valid llm client type')
    

class LLMClient(ABC):
    @abc.abstractmethod
    async def async_chat(self, system_prompt, user_message, prompt_options, process_chunk, sys_out=sys.stdout):
        raise NotImplementedError

    @abc.abstractmethod
    def chat(self, system_prompt, user_message, prompt_options):
        raise NotImplementedError


class OpenAIClient(LLMClient):
    def __init__(self, model_name, stream=True):
        api_key = os.getenv('OPENAI_API_KEY')
        self.client = AsyncOpenAI(api_key=api_key) if stream else OpenAI(api_key=api_key)
        self.model_name = model_name
        self.stream = stream

    async def async_chat(self, system_prompt, user_message, prompt_options, process_chunk, sys_out=sys.stdout, key=None):
        try:
            stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    { 'role': 'system', 'content': system_prompt },
                    { 'role': 'user', 'content': user_message }
                ],
                **prompt_options,
                stream=True,
            )
            async for chunk in stream:
                chunk_content = chunk.choices[0].delta.content
                if chunk_content:
                    await process_chunk(chunk_content, sys_out, key)
        except Exception as e:
            print(f"An error occurred: {e}", file=sys.stderr)
            raise

    def chat(self, system_prompt, user_message, prompt_options):
        resp = self.client.chat.completions.create(
            model=self.model_name,
            messages=[
                { 'role': 'system', 'content': system_prompt },
                { 'role': 'user', 'content': user_message }
            ],
            **prompt_options,
        )
        message = resp.choices[0].message.content.strip()
        return message


class OllamaClient(LLMClient):
    def __init__(self, model_name, stream=True):
        self.client = ollama.AsyncClient() if stream else ollama.Client()
        self.model_name = model_name
        self.stream = stream

    async def async_chat(self, system_prompt, user_message, prompt_options, process_chunk, sys_out=sys.stdout, key=None):
        try:
            content = LLAMA_3_TEMPLATE(system=system_prompt, message=user_message)
            stream = await self.client.chat(
                model=self.model_name,
                messages=[{ 'role': 'user', 'content': content }],
                options={
                    'temperature': prompt_options['temperature'],
                    'top_p': prompt_options['top_p'],
                    'num_ctx': 8192,
                },
                stream=True,
            )
            async for chunk in stream:
                chunk_content = chunk['message']['content']
                if chunk_content:
                    await process_chunk(chunk_content, sys_out, key)
        except Exception as e:
            print(f"An error occurred: {e}", file=sys.stderr)
            raise

    def chat(self, system_prompt, user_message, prompt_options):
        content = LLAMA_3_TEMPLATE(system=system_prompt, message=user_message)
        resp = self.client.chat(
            model=self.model_name,
            messages=[ { 'role': 'user', 'content': content } ],
            options={
                'temperature': prompt_options['temperature'],
                'top_p': prompt_options['top_p'],
                'num_ctx': 8192,
            },
        )
        message = resp['message']['content']
        return message.strip()

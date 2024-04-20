from enum import Enum
import os
from openai import AsyncOpenAI, OpenAI
import ollama

from code_prompts import DEFAULT_PROMPT_OPTIONS


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


class LLMClient():
    def __init__(self, client_type, model_name, stream=True):
        self.client = None
        self.client_type = client_type
        self.model_name = model_name
        self.stream = stream
        if client_type is LLMType.OPENAI:
            if stream:
                self.client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            else:
                self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        elif client_type is LLMType.OLLAMA:
            self.client = ollama.AsyncClient() if stream else ollama.Client()
        else:
            raise Exception('not a valid client_type', client_type)


    async def _async_chat(self, system_prompt, user_message, prompt_options=DEFAULT_PROMPT_OPTIONS):
        if self.stream is False:
            raise Exception('stream is not on')

        messages = []
        if self.client_type is LLMType.OPENAI:
            async_stream = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    { 'role': 'system', 'content': system_prompt },
                    { 'role': 'user', 'content': user_message }
                ],
                **prompt_options,
                stream=True,
            )
            async for chunk in async_stream:
                content = chunk.choices[0].delta.content
                if content is not None:
                    print(content, end='', flush=True)
                    messages.append(content)
            return "".join(messages).strip()
        elif self.client_type is LLMType.OLLAMA:
            content = LLAMA_3_TEMPLATE(system=system_prompt, message=user_message)
            async_stream = await self.client.chat(
                model=self.model_name,
                messages=[{ 'role': 'user', 'content': content }],
                options={
                    'temperature': prompt_options['temperature'],
                    'top_p': prompt_options['top_p'],
                    'num_ctx': 8192,
                },
                stream=True,
            )
            async for chunk in async_stream:
                content = chunk['message']['content']
                if content is not None:
                    print(content, end='', flush=True)
                    messages.append(content)
            return "".join(messages).strip()
        else:
            raise Exception('Failed async chat')


    def _chat(self, system_prompt, user_message, prompt_options=None):
        if self.client_type is LLMType.OPENAI:
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
        elif self.client_type is LLMType.OLLAMA:
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
        else:
            raise Exception('Failed chat')


    async def chat(self, system_prompt, message, prompt_options):
        if self.stream:
            return await self._async_chat(system_prompt, message, prompt_options)
        else:
            return self._chat(system_prompt, message, prompt_options)

import json
import httpx
from typing import Any, AsyncGenerator, Optional, Dict, List
from abc import ABC, abstractmethod

import dashscope
from dashscope import Generation
from openai import AsyncOpenAI

from app.config import get_settings

settings = get_settings()

MessageList = List[Dict[str, str]]


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, messages: MessageList, stream: bool = False) -> Any:
        pass

    @abstractmethod
    async def generate_stream(self, messages: MessageList) -> AsyncGenerator[str, None]:
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass


class DashScopeProvider(LLMProvider):
    def __init__(self):
        dashscope.api_key = settings.dashscope_api_key
        self._model = settings.dashscope_model

    @property
    def provider_name(self) -> str:
        return "dashscope"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, messages: MessageList, stream: bool = False) -> Any:
        response = Generation.call(
            model=self._model,
            messages=messages,
            result_format="message",
            stream=stream,
        )
        if response.status_code != 200:
            raise Exception(f"DashScope API error: {response.message}")
        return response.output.choices[0].message.content

    async def generate_stream(self, messages: MessageList) -> AsyncGenerator[str, None]:
        response = Generation.call(
            model=self._model,
            messages=messages,
            result_format="message",
            stream=True,
        )

        last_content = ""
        for chunk in response:
            if chunk.status_code != 200:
                continue
            raw = chunk.output.choices[0].message.content or ""
            if isinstance(raw, dict):
                raw = raw.get("content", "") or ""
            if not raw:
                continue
            delta = raw[len(last_content):]
            last_content = raw
            if delta:
                yield delta

    async def generate_json(self, messages: MessageList) -> Dict[str, Any]:
        response = Generation.call(
            model=self._model,
            messages=messages,
            result_format="message",
            stream=False,
        )
        if response.status_code != 200:
            raise Exception(f"DashScope API error: {response.message}")

        content = response.output.choices[0].message.content
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        return json.loads(content)


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._model = settings.openai_model

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(self, messages: MessageList, stream: bool = False) -> Any:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=stream,
        )
        return response.choices[0].message.content

    async def generate_stream(self, messages: MessageList) -> AsyncGenerator[str, None]:
        stream_response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            stream=True,
        )

        async for chunk in stream_response:
            content = chunk.choices[0].delta.content
            if content:
                yield content

    async def generate_json(self, messages: MessageList) -> Dict[str, Any]:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        return json.loads(content)


def get_llm_provider(provider: Optional[str] = None) -> LLMProvider:
    provider = provider or settings.llm_provider
    if provider == "openai":
        return OpenAIProvider()
    if provider == "qianfan":
        return QianfanProvider()
    return DashScopeProvider()


class QianfanProvider(LLMProvider):
    def __init__(self):
        self._model = settings.qianfan_model
        self._api_url = settings.qianfan_api_url.rstrip("/")
        self._api_key = settings.qianfan_api_key
        self._client = httpx.AsyncClient(timeout=120.0)

    async def close(self):
        await self._client.aclose()

    @property
    def provider_name(self) -> str:
        return "qianfan"

    @property
    def model_name(self) -> str:
        return self._model

    def _build_messages(self, messages: MessageList) -> list[dict]:
        """Convert messages to API format"""
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            if role not in ("system", "user", "assistant"):
                role = "user"
            formatted.append({
                "role": role,
                "content": msg.get("content", ""),
            })
        return formatted

    async def _post(self, endpoint: str, body: dict) -> dict:
        url = f"{self._api_url}{endpoint}"
        headers = {
            "Authorization": self._api_key,
            "Content-Type": "application/json",
        }
        resp = await self._client.post(url, json=body, headers=headers)
        resp.raise_for_status()
        return resp.json()

    async def _post_stream(self, endpoint: str, body: dict) -> AsyncGenerator[str, None]:
        url = f"{self._api_url}{endpoint}"
        headers = {
            "Authorization": self._api_key,
            "Content-Type": "application/json",
        }
        async with self._client.stream("POST", url, json=body, headers=headers) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    break
                try:
                    data = json.loads(payload)
                    delta = data.get("choices", {}).get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        yield content
                except json.JSONDecodeError:
                    continue

    async def generate(self, messages: MessageList, stream: bool = False) -> Any:
        body = {
            "messages": self._build_messages(messages),
            "model": self._model,
        }
        if stream:
            return self._post_stream("/chat/completions", body)
        resp = await self._post("/chat/completions", body)
        return resp["choices"][0]["message"]["content"]

    async def generate_stream(self, messages: MessageList) -> AsyncGenerator[str, None]:
        body = {
            "messages": self._build_messages(messages),
            "model": self._model,
        }
        async for chunk in self._post_stream("/chat/completions", body):
            yield chunk

    async def generate_json(self, messages: MessageList) -> Dict[str, Any]:
        body = {
            "messages": self._build_messages(messages),
            "model": self._model,
        }
        resp = await self._post("/chat/completions", body)
        content = resp["choices"][0]["message"]["content"].strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        return json.loads(content.strip())

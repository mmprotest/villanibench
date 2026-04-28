from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib import request


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ChatResponse:
    content: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class ChatClient(Protocol):
    def create_chat_completion(self, *, model: str, messages: list[ChatMessage], max_tokens: int, temperature: int) -> ChatResponse:
        ...


class OpenAICompatibleChatClient:
    def __init__(self, *, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def create_chat_completion(self, *, model: str, messages: list[ChatMessage], max_tokens: int, temperature: int) -> ChatResponse:
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        req = request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        choice = body["choices"][0]["message"]
        usage = body.get("usage", {})
        content = choice.get("content", "")
        if isinstance(content, list):
            content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
        return ChatResponse(
            content=str(content),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )

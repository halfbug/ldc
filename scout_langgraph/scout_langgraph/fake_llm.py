"""Scripted chat model for tests/demos (no Bedrock needed). Streams word by word."""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import PrivateAttr


class ScriptedChatModel(BaseChatModel):
    """Each call pops the next step: {"text": str, "tool_calls": [{"name","args","id"}], "delay": s}."""
    _script: List[Dict[str, Any]] = PrivateAttr(default_factory=list)
    _i: int = PrivateAttr(default=0)

    def __init__(self, script: List[Dict[str, Any]], **kw: Any) -> None:
        super().__init__(**kw)
        self._script = script

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Any, **kw: Any) -> "ScriptedChatModel":
        return self

    def _next(self) -> Dict[str, Any]:
        step = self._script[min(self._i, len(self._script) - 1)]
        self._i += 1
        return step

    def _generate(self, messages, stop=None, run_manager=None, **kw) -> ChatResult:
        step = self._next()
        msg = AIMessage(content=step.get("text", ""), tool_calls=step.get("tool_calls", []))
        return ChatResult(generations=[ChatGeneration(message=msg)])

    async def _astream(self, messages, stop=None, run_manager=None, **kw):
        step = self._next()
        for word in step.get("text", "").split(" "):
            if not word:
                continue
            await asyncio.sleep(step.get("delay", 0))
            yield ChatGenerationChunk(message=AIMessageChunk(content=word + " "))
        for idx, call in enumerate(step.get("tool_calls", [])):
            yield ChatGenerationChunk(message=AIMessageChunk(
                content="",
                tool_call_chunks=[{"name": call["name"], "args": json.dumps(call["args"]),
                                   "id": call["id"], "index": idx}]))

"""Stop plumbing (Chapter 8.3): a store every Lambda environment can see.

Production: back this with the same MongoDB `threads` collection the guide uses
(running_turn_id / cancel_turn_id on the thread doc + an `early_cancels` collection with a
1 h TTL). The in-memory version below has identical semantics and is what the tests use.
"""
from __future__ import annotations

import time
from typing import Dict, Literal, Optional, Protocol

CancelResult = Literal["cancelled", "not_running", "not_found"]
EARLY_CANCEL_TTL_S = 3600


class CancelStore(Protocol):
    async def mark_running(self, thread_id: str, turn_id: str, user_id: str) -> None: ...
    async def clear_running(self, thread_id: str, turn_id: str) -> None: ...
    async def request_cancel(self, thread_id: str, user_id: str, turn_id: str) -> CancelResult: ...
    async def cancel_seen(self, thread_id: str, turn_id: str) -> bool: ...


class InMemoryCancelStore:
    def __init__(self) -> None:
        self._running: Dict[str, Dict[str, str]] = {}   # thread_id -> {turn_id, user_id}
        self._cancel: Dict[str, str] = {}               # thread_id -> cancel_turn_id
        self._early: Dict[str, float] = {}              # turn_id -> timestamp
        self._finished: set[str] = set()

    async def mark_running(self, thread_id, turn_id, user_id):
        self._running[thread_id] = {"turn_id": turn_id, "user_id": user_id}

    async def clear_running(self, thread_id, turn_id):
        if self._running.get(thread_id, {}).get("turn_id") == turn_id:
            del self._running[thread_id]
        self._cancel.pop(thread_id, None)
        self._finished.add(turn_id)

    async def request_cancel(self, thread_id, user_id, turn_id) -> CancelResult:
        run = self._running.get(thread_id)
        if run is not None and run["user_id"] != user_id:
            return "not_found"
        if run is not None and run["turn_id"] == turn_id:
            self._cancel[thread_id] = turn_id
            return "cancelled"
        if turn_id in self._finished:
            return "not_running"                        # already finished: a no-op
        self._early[turn_id] = time.time()              # Stop beat the turn: record by turn id
        return "cancelled"

    async def cancel_seen(self, thread_id, turn_id) -> bool:
        if self._cancel.get(thread_id) == turn_id:
            return True
        at = self._early.get(turn_id)
        return at is not None and time.time() - at < EARLY_CANCEL_TTL_S


class CancelSignal:
    """Same idea as the guide's CancelSignal: an event plus the reason it fired."""
    def __init__(self) -> None:
        import asyncio
        self.event = asyncio.Event()
        self.reason: Optional[str] = None

    def set(self, reason: str) -> None:
        if not self.event.is_set():
            self.reason = reason
            self.event.set()

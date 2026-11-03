"""FastAPI surface: POST /v2/turn (SSE) and POST /v2/turn/cancel."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from .cancel import CancelStore, InMemoryCancelStore
from .streaming import CoreConfig, PreflightError, preflight, stream_turn

SSE_HEADERS = {
    "Cache-Control": "no-cache, no-transform",
    "X-Accel-Buffering": "no",
    "Connection": "keep-alive",
}


class ActionResult(BaseModel):
    id: str
    capability: str = ""            # empty => this answers a question (ask_user)
    status: str = "ok"
    message: str = ""
    stateVersion: Optional[int] = None


class TurnRequest(BaseModel):
    thread_id: str
    user_id: str = ""
    turn_id: Optional[str] = None
    message: str = ""
    action_result: Optional[ActionResult] = None


class CancelRequest(BaseModel):
    thread_id: str
    turn_id: str
    user_id: str = ""


def create_app(graph, store: Optional[CancelStore] = None, cfg: Optional[CoreConfig] = None) -> FastAPI:
    store = store or InMemoryCancelStore()
    app = FastAPI()

    @app.post("/v2/turn")
    async def turn(req: TurnRequest):
        payload: Dict[str, Any] = req.model_dump()
        try:
            prepared = await preflight(graph, payload)     # JSON errors BEFORE any stream
        except PreflightError as failed:
            return JSONResponse(status_code=failed.status, content=failed.body())
        return StreamingResponse(stream_turn(graph, payload, prepared, store, cfg),
                                 media_type="text/event-stream", headers=SSE_HEADERS)

    @app.post("/v2/turn/cancel")
    async def cancel(req: CancelRequest):
        return {"status": await store.request_cancel(req.thread_id, req.user_id, req.turn_id)}

    return app

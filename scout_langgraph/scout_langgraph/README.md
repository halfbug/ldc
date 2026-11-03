# Scout turn: LangGraph version (SSE · pause · resume · stop)

Port of the mechanisms in *Scout Streaming* (Ch. 3, 6, 7, 8) to LangGraph. Tested with a
scripted model (`python -m scout_langgraph.run_tests`, run from the parent folder). Not yet run
against Bedrock or MongoDB.

| File | What it is |
|---|---|
| `graph.py` | `StateGraph`: ingest → agent ⇄ tools → pause (`interrupt()`) → agent → finalize |
| `streaming.py` | `sse()`, `preflight()` (409), `stream_turn()` (queue, heartbeat, ceiling), stop watcher + finalizer |
| `cancel.py` | Cancel store (in-memory; same semantics as the guide's `request_cancel`) |
| `app.py` | FastAPI `POST /v2/turn` (SSE) and `POST /v2/turn/cancel` |
| `fake_llm.py`, `run_tests.py`, `serve_demo.py` | Scripted model, 20 checks, runnable demo server |
| `scout_turn_graph.mmd` | Mermaid export of the compiled graph |

## Production wiring

```python
from langchain_aws import ChatBedrockConverse
from langgraph.checkpoint.mongodb import MongoDBSaver   # pip install langgraph-checkpoint-mongodb

llm = ChatBedrockConverse(model="amazon.nova-micro-v1:0").bind_tools([...schemas...])
graph = build_graph(llm, {"search_curriculum": search_fn}, MongoDBSaver(mongo_client))
app = create_app(graph, store=MongoCancelStore(...))     # implement CancelStore on your threads collection
```

* Use a **shared checkpointer** (Mongo). The resume request can hit a different Lambda environment,
  exactly as in the guide, so `InMemorySaver` is for tests only.
* Implement `CancelStore` on the same Mongo collection (`running_turn_id`, `cancel_turn_id`, plus an
  `early_cancels` collection with a 1 h TTL).
* Keep the Function URL `RESPONSE_STREAM` + Lambda Web Adapter setup unchanged.

## Behaviour notes

* **Pause**: `pause` calls `interrupt()`. Code above it re-runs on resume, so keep it side-effect free.
* **Resume**: `Command(resume=action_result)`; the answer becomes the `ToolMessage` for the paused
  tool-call id. `409 nothing_to_resume` when the thread has no pending interrupt.
* **New message while paused**: `aupdate_state(as_node="pause")` closes the call as `NOT_PERFORMED`,
  adds the message, and the graph continues at `agent`.
* **Stop**: producer task is cancelled (also cancels the model call), then history is trimmed to
  `keep_len` and `STOPPED_NOTE` is appended; only text already streamed is saved.
* **Not ported**: `deterministic_continuation()` (button answer runs the tool without the model),
  thread ownership (404), cost/usage telemetry.

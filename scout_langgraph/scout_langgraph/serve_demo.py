"""Run:  uvicorn scout_langgraph.serve_demo:app --port 8099   (scripted model, no AWS needed)"""
from langgraph.checkpoint.memory import InMemorySaver
from .app import create_app
from .fake_llm import ScriptedChatModel
from .graph import build_graph

llm = ScriptedChatModel([
    {"text": "Opening the Lessons tab now.", "delay": 0.05,
     "tool_calls": [{"name": "page_action", "args": {"capability": "open_tab", "args": {"tab": "Lessons"}}, "id": "tu-1"}]},
    {"text": " ".join(f"word{i}" for i in range(60)), "delay": 0.1},   # long answer to stop
])
app = create_app(build_graph(llm, {}, InMemorySaver()))

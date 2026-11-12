"""FastAPI transport and a bounded three-agent LangGraph workflow."""
from contextlib import asynccontextmanager
from pathlib import Path
import sqlite3
from typing import TypedDict
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from .identity import presenter_gate
from .memory import CapacityReached, Store
from .observability import LimitBody, event, request_log
from .policy import DecisionConflict, TicketDraft
from .tools import ProviderUnavailable


class Turn(TypedDict, total=False):
    message: str
    route: str
    agent: str
    answer: str
    context: str
    sources: list[str]
    citations: list[dict[str, str]]
    draft: TicketDraft
    ticket_call: object
    research_query: str
    research_call: object
    research_observation: str
    research_tool_message: object


class Chat(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    message: str = Field(min_length=1, max_length=1500)


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approve: StrictBool


def build_graph(agents):
    """Compile the real routing/tool graph; agents are only called on invocation."""
    graph = StateGraph(Turn)

    def route(state):
        destination = agents.route(state["message"])
        if destination not in {"qa", "ticket", "research"}:
            raise ProviderUnavailable
        return {"route": destination}

    graph.add_node("router", route)
    graph.add_node("qa_retrieval", lambda state: agents.qa_retrieve(state["message"]))
    graph.add_node("qa_agent", lambda state: {
        **agents.qa_answer(state["message"], state["context"]), "agent": "qa"})
    graph.add_node("ticket_agent", lambda state: {
        "ticket_call": agents.ticket_agent(state["message"])})
    graph.add_node("ticket_draft_tool", lambda state: {
        "draft": agents.ticket_draft_tool(state["ticket_call"]), "agent": "ticket"})
    graph.add_node("research_agent", lambda state: agents.research_agent(state))
    graph.add_node("research_web_tool", lambda state: agents.research_web_tool(
        state["research_query"], state["research_call"]))

    graph.add_edge(START, "router")
    graph.add_conditional_edges("router", lambda state: state["route"], {
        "qa": "qa_retrieval", "ticket": "ticket_agent", "research": "research_agent"})
    for first, second in (("qa_retrieval", "qa_agent"),
                          ("ticket_agent", "ticket_draft_tool")):
        graph.add_edge(first, second)
        graph.add_edge(second, END)
    graph.add_conditional_edges("research_agent", lambda state: "done" if "answer" in state else "search",
                                {"done": END, "search": "research_web_tool"})
    graph.add_edge("research_web_tool", "research_agent")
    return graph.compile()


def save_graph_visualization(output: Path) -> Path:
    """Render the compiled graph without initializing models or calling the provider."""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(build_graph(None).get_graph().draw_mermaid_png())
    return output


def create_app(db: Path, *, agents_factory, token=None, hosted=False):
    gate = presenter_gate(token, hosted)
    store = Store(db)

    @asynccontextmanager
    async def lifespan(app):
        store.initialize()
        app.state.graph = build_graph(agents_factory())
        yield

    app = FastAPI(title="Mini Enterprise AI Support Agent", lifespan=lifespan,
                  docs_url=None if hosted else "/docs",
                  redoc_url=None, openapi_url=None if hosted else "/openapi.json")
    app.add_middleware(LimitBody, limit=8192)
    app.middleware("http")(request_log)

    if not hosted and not token:
        static = Path(__file__).resolve().parent / "static"

        @app.get("/", include_in_schema=False)
        def chat_page():
            return FileResponse(static / "index.html", headers={"Cache-Control": "no-store"})

        @app.get("/ui.js", include_in_schema=False)
        def chat_script():
            return FileResponse(static / "ui.js", media_type="text/javascript",
                                headers={"Cache-Control": "no-store"})

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/chat", dependencies=[Depends(gate)])
    def chat(body: Chat, request: Request):
        try:
            result = request.app.state.graph.invoke({"message": body.message},
                                                    config={"recursion_limit": 8})
            if "draft" not in result:
                return {"kind": "answer", "agent": result["agent"],
                        "answer": result["answer"], "sources": result.get("sources", []),
                        "citations": result.get("citations", [])}
            draft = result["draft"]
            approval = store.propose(draft.content)
        except ProviderUnavailable:
            event("provider_unavailable", request_id=request.state.request_id)
            raise HTTPException(503, "AI or search provider unavailable. Check server logs and retry.") from None
        except CapacityReached:
            raise HTTPException(503, "Ticket store is full; use a fresh database.") from None
        except sqlite3.OperationalError:
            raise HTTPException(503, "Ticket store unavailable.") from None
        event("approval_requested", request_id=request.state.request_id, approval_id=approval)
        return {"kind": "approval_required", "agent": "ticket",
                "approval_id": approval, "draft": draft.model_dump()}

    @app.post("/approvals/{approval_id}", dependencies=[Depends(gate)])
    def approval(approval_id: UUID, body: Decision, request: Request):
        try:
            result = store.decide(str(approval_id), body.approve)
        except DecisionConflict as exc:
            raise HTTPException(409, str(exc)) from None
        except sqlite3.OperationalError:
            raise HTTPException(503, "Ticket store unavailable.") from None
        if result is None:
            raise HTTPException(404, "Approval not found.")
        event("approval_decided", request_id=request.state.request_id,
              approval_id=str(approval_id), decision=result["status"])
        return result

    @app.get("/tickets/{ticket_id}", dependencies=[Depends(gate)])
    def ticket(ticket_id: UUID):
        try:
            result = store.ticket(str(ticket_id))
        except sqlite3.OperationalError:
            raise HTTPException(503, "Ticket store unavailable.") from None
        if result is None:
            raise HTTPException(404, "Ticket not found.")
        return result

    return app

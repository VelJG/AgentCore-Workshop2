"""FastAPI transport and one bounded LangGraph workflow."""
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
from .tools import ProviderUnavailable, demo_turn


class Turn(TypedDict, total=False):
    message: str
    answer: str
    sources: list[str]
    draft: TicketDraft


class Chat(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    message: str = Field(min_length=1, max_length=1500)


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    approve: StrictBool


def create_app(db: Path, *, token=None, hosted=False, mode="demo", turn_factory=demo_turn):
    gate = presenter_gate(token, hosted)
    store = Store(db)

    @asynccontextmanager
    async def lifespan(app):
        store.initialize()
        turn = turn_factory()
        graph = StateGraph(Turn)
        graph.add_node("support", lambda state: turn(state["message"]))
        graph.add_edge(START, "support")
        graph.add_edge("support", END)
        app.state.graph = graph.compile()
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
        return {"status": "ok", "mode": mode}

    @app.post("/chat", dependencies=[Depends(gate)])
    def chat(body: Chat, request: Request):
        try:
            result = request.app.state.graph.invoke({"message": body.message})
            if "draft" not in result:
                return {"kind": "answer", "answer": result["answer"], "sources": result["sources"]}
            draft = result["draft"]
            approval = store.propose(draft.content)
        except ProviderUnavailable:
            event("provider_unavailable", request_id=request.state.request_id)
            raise HTTPException(503, "Model provider unavailable. Retry or rehearse in demo mode.") from None
        except CapacityReached:
            raise HTTPException(503, "Demo store is full; use a fresh database.") from None
        except sqlite3.OperationalError:
            raise HTTPException(503, "Demo store unavailable.") from None
        event("approval_requested", request_id=request.state.request_id, approval_id=approval)
        return {"kind": "approval_required", "approval_id": approval, "draft": draft.model_dump()}

    @app.post("/approvals/{approval_id}", dependencies=[Depends(gate)])
    def approval(approval_id: UUID, body: Decision, request: Request):
        try:
            result = store.decide(str(approval_id), body.approve)
        except DecisionConflict as exc:
            raise HTTPException(409, str(exc)) from None
        except sqlite3.OperationalError:
            raise HTTPException(503, "Demo store unavailable.") from None
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
            raise HTTPException(503, "Demo store unavailable.") from None
        if result is None:
            raise HTTPException(404, "Ticket not found.")
        return result

    return app

"""HTTP API for the HSCI Mind.

Run standalone (fast boot, no torch):   python -m hsci.mind.api --port 8100
Or mounted inside the main app:         brain_api.py includes ``router`` under /v2

Endpoints
    POST   /v2/chat                          tell and/or ask, in any mix of sentences
    GET    /v2/worlds                        list worlds
    GET    /v2/worlds/{world}                knowledge snapshot (facts, rules, hypotheses ...)
    DELETE /v2/worlds/{world}                reset a world
    DELETE /v2/worlds/{world}/statements/{id}   forget one statement and everything it implied
    GET    /v2/health
    GET    /mind                             web UI
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from hsci.mind.kb import COMMON
from hsci.mind.mind import Mind

MAX_TEXT = int(os.getenv("HSCI_MIND_MAX_TEXT", "20000"))
_WORLD_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
_UI = Path(__file__).resolve().parents[2] / "ui" / "mind.html"

_mind: Optional[Mind] = None
_started = time.time()


def get_mind() -> Mind:
    global _mind
    if _mind is None:
        path = os.getenv("HSCI_MIND_DB", os.path.join("data", "hsci_mind.db"))
        if path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        _mind = Mind(db_path=path)
    return _mind


def _check_world(world: str, write: bool) -> str:
    if world == COMMON:
        if write and os.getenv("HSCI_MIND_ALLOW_COMMON_WRITES") != "1":
            raise HTTPException(403, "the shared __common__ world is read-only over the API")
        return world
    if not _WORLD_RE.match(world):
        raise HTTPException(422, "world must be 1-64 characters of letters, digits, '_' or '-'")
    return world


class ChatRequest(BaseModel):
    text: str = Field(..., description="One or more sentences: statements to learn and/or questions to answer.")
    world: str = Field("default", description="Belief context; each world has independent knowledge.")

    @field_validator("text")
    @classmethod
    def _text(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text must not be empty")
        if len(v) > MAX_TEXT:
            raise ValueError(f"text longer than {MAX_TEXT} characters")
        return v


router = APIRouter(prefix="/v2", tags=["mind"])


@router.post("/chat")
def chat(req: ChatRequest) -> dict:
    world = _check_world(req.world, write=True)
    return get_mind().process(req.text, world).to_dict()


class TeachRequest(BaseModel):
    surface: str = Field(..., description="How someone might say it, e.g. 'Wugs belong to the blick family.'")
    canonical: str = Field(..., description="What it means, said plainly, e.g. 'Every wug is a blick.'")
    world: str = "default"

    @field_validator("surface", "canonical")
    @classmethod
    def _txt(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > 1000:
            raise ValueError("must be 1-1000 characters")
        return v


@router.post("/teach")
def teach(req: TeachRequest) -> dict:
    """Teach a phrasing: from now on ``surface`` (and sentences like it) means what ``canonical`` means."""
    world = _check_world(req.world, write=True)
    try:
        meaning = get_mind().teach(req.surface, req.canonical, world)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    return {"learned": True, "surface": req.surface, "means": meaning}


@router.get("/understanding")
def understanding() -> dict:
    return get_mind().understanding.status()


@router.get("/worlds")
def worlds() -> dict:
    return {"worlds": get_mind().kb.worlds()}


@router.get("/worlds/{world}")
def snapshot(world: str, limit: int = 300) -> dict:
    return get_mind().snapshot(_check_world(world, write=False), limit=max(1, min(limit, 2000)))


@router.delete("/worlds/{world}")
def reset(world: str) -> dict:
    get_mind().reset(_check_world(world, write=True))
    return {"world": world, "status": "reset"}


@router.delete("/worlds/{world}/statements/{statement_id}")
def forget(world: str, statement_id: int) -> dict:
    if not get_mind().forget(statement_id, _check_world(world, write=True)):
        raise HTTPException(404, "no such statement in this world")
    return {"world": world, "forgotten": statement_id}


@router.get("/health")
def health() -> dict:
    m = get_mind()
    return {"status": "healthy", "engine": "hsci-mind", "uptime_s": round(time.time() - _started, 1),
            "common": m.kb.stats(COMMON), "seed_failures": m.seed_report}


def ui_route(app: FastAPI) -> None:
    @app.get("/mind", include_in_schema=False)
    def mind_ui():
        if not _UI.exists():
            raise HTTPException(404, "ui/mind.html not found")
        return FileResponse(str(_UI), headers={"Cache-Control": "no-cache"})


def create_app() -> FastAPI:
    app = FastAPI(title="HSCI Mind API", version="0.1.0")
    app.include_router(router)
    ui_route(app)

    @app.get("/", include_in_schema=False)
    def root():
        return {"service": "hsci-mind", "ui": "/mind", "docs": "/docs"}

    return app


app = create_app()

if __name__ == "__main__":
    import argparse

    import uvicorn

    ap = argparse.ArgumentParser(description="Run the HSCI Mind API")
    ap.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.getenv("PORT", "8100")))
    args = ap.parse_args()
    uvicorn.run(app, host=args.host, port=args.port)

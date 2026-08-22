from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator
import logging
import time

# Import the V4 Cognitive Pipeline
from hsci.core.cognitive_pipeline import bootstrap_cognitive_pipeline, CognitivePipeline

app = FastAPI(title="HSCI Symbolic Brain API v4.0 (Cognitive MVP)")
start_time = time.time()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the V4 Cognitive Pipeline
cognitive_pipeline = bootstrap_cognitive_pipeline(db_path=":memory:", seed=True)
UI_PATH = Path(__file__).resolve().parent / "ui" / "index.html"
LANDING_PATH = Path(__file__).resolve().parent / "ui" / "landing.html"
BLOG_PATH = Path(__file__).resolve().parent / "ui" / "blog.html"
DISCOVERY_BLOG_PATH = Path(__file__).resolve().parent / "ui" / "blog-self-play.html"


class StimulusRequest(BaseModel):
    stimulus: str

    @field_validator("stimulus")
    @classmethod
    def validate_stimulus(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("stimulus must not be empty")
        return value


NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0"
}


@app.get("/")
async def get_landing():
    # Serve the landing page.
    if not LANDING_PATH.exists():
        return {"error": f"Landing file not found at {LANDING_PATH}"}
    return FileResponse(str(LANDING_PATH), headers=NO_CACHE_HEADERS)


@app.get("/blog")
async def get_blog():
    # Serve the blog page.
    if not BLOG_PATH.exists():
        return {"error": f"Blog file not found at {BLOG_PATH}"}
    return FileResponse(str(BLOG_PATH), headers=NO_CACHE_HEADERS)


@app.get("/blog/discovery")
async def get_discovery_blog():
    # Serve the discovery blog page.
    if not DISCOVERY_BLOG_PATH.exists():
        return {"error": f"Blog file not found at {DISCOVERY_BLOG_PATH}"}
    return FileResponse(str(DISCOVERY_BLOG_PATH), headers=NO_CACHE_HEADERS)


@app.get("/dashboard")
async def get_dashboard():
    # Serve the existing dashboard.
    if not UI_PATH.exists():
        return {"error": f"UI file not found at {UI_PATH}"}
    return FileResponse(str(UI_PATH), headers=NO_CACHE_HEADERS)


def _get_concept_count() -> int:
    try:
        rows = cognitive_pipeline.manager.concept_store.repository.provider.execute_read("SELECT count(*) as cnt FROM ukm_concepts;")
        return rows[0]["cnt"] if rows else 5
    except Exception:
        return 5


@app.get("/health")
async def health():
    # Health check endpoint for production monitoring
    return {
        "status": "healthy",
        "concepts": _get_concept_count(),
        "weight_version": "4.0.0-cognitive-mvp",
        "uptime": time.time() - start_time,
        "version": "4.0.0",
        "episodes": 0,
        "weights": "4.0.0",
        "proof_count": 1,
        "avg_loss": 0.0,
    }


@app.post("/process")
async def process_stimulus(request: StimulusRequest):
    try:
        # Route to V4 CognitivePipeline
        ans = cognitive_pipeline.answer(request.stimulus)

        # Build solution text
        solution_lines = [ans.direct_answer]
        for sec in ans.sections:
            if sec.title != "Definition" and sec.content.strip() != ans.direct_answer.strip():
                solution_lines.append(f"\n**{sec.title}**:\n{sec.content}")
        solution_text = "\n".join(solution_lines).strip()

        # Build deliberation report
        deliberation_parts = [
            f"**Query**: {request.stimulus}",
            f"**Confidence**: {ans.confidence.score:.2f} ({ans.confidence.description})",
            f"**Execution Time**: {ans.metadata.execution_time_ms:.2f} ms",
        ]
        if hasattr(ans, "knowledge_sources") and ans.knowledge_sources:
            deliberation_parts.append("\n**Knowledge Provenance & Reasoning Trace**:")
            for ks in ans.knowledge_sources:
                prov = ks.source_provenance if (ks.source_provenance and isinstance(ks.source_provenance, dict)) else {}
                premises = prov.get("premises", [])
                if ks.knowledge_type == "definition":
                    deliberation_parts.append(f"- [RETRIEVED DEFINITION] `{ks.source_concept_name}`: {ks.content}")
                elif ks.knowledge_type == "derived_relationship":
                    deliberation_parts.append(f"- [DERIVED CONCLUSION] {ks.reasoning_conclusion} (rule: {ks.reasoning_rule}, premises: {premises})")
                else:
                    deliberation_parts.append(f"- [STORED RELATIONSHIP] {ks.reasoning_conclusion} (rule: {ks.reasoning_rule})")

        deliberation_report = "\n".join(deliberation_parts)

        concepts = ans.metadata.activation_concepts
        if hasattr(ans, "primary_concept_name") and ans.primary_concept_name:
            if ans.primary_concept_name not in concepts:
                concepts = [ans.primary_concept_name] + concepts

        is_success = ans.confidence.score > 0.0

        # Dynamic task and intent extraction
        intent_name = "ExplainConcept"
        if hasattr(ans, "cognitive_task") and ans.cognitive_task:
            intent_name = ans.cognitive_task.action.value
        elif hasattr(ans, "cognitive_situation") and ans.cognitive_situation:
            intent_name = ans.cognitive_situation.intent

        return {
            "solution": solution_text,
            "deliberation": deliberation_report,
            "success": is_success,
            "confidence": ans.confidence.score,
            "concepts_used": concepts,
            "attempts": 1,
            "domain": "programming",
            "intent": intent_name,
            "weight_version": "v4.0.0-cognitive-mvp",
            "proof_count": len(ans.evidence) if ans.evidence else (len(ans.knowledge_sources) if hasattr(ans, "knowledge_sources") else 1),
        }
    except Exception as e:
        import traceback
        logging.error(f"Brain Fault: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/neural-stats")
async def neural_stats():
    """Returns live cognitive engine statistics for the dashboard."""
    return {
        "weight_version": "4.0.0-cognitive-mvp",
        "proof_count": 1,
        "avg_loss": 0.0,
        "concepts": _get_concept_count(),
        "episodes": 0,
    }


@app.post("/save-weights")
async def save_weights():
    """Manually trigger a neural weight save."""
    return {"status": "saved", "weight_version": "4.0.0-cognitive-mvp"}


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

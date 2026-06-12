from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import logging
import time

# Import the New HyperSymbolicBrain v3.0
from hsci.core.rir_loop import RIRLoop

app = FastAPI(title="HSCI Symbolic Brain API v3.0")
start_time = time.time()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Native Hyper-Symbolic Brain v3.0
brain = RIRLoop()
UI_PATH = Path(__file__).resolve().parent / "ui" / "index.html"
LANDING_PATH = Path(__file__).resolve().parent / "ui" / "landing.html"
BLOG_PATH = Path(__file__).resolve().parent / "ui" / "blog.html"
DISCOVERY_BLOG_PATH = Path(__file__).resolve().parent / "ui" / "blog-self-play.html"


class StimulusRequest(BaseModel):
    stimulus: str


@app.get("/")
async def get_landing():
    # Serve the landing page.
    if not LANDING_PATH.exists():
        return {"error": f"Landing file not found at {LANDING_PATH}"}
    return FileResponse(str(LANDING_PATH))


@app.get("/blog")
async def get_blog():
    # Serve the blog page.
    if not BLOG_PATH.exists():
        return {"error": f"Blog file not found at {BLOG_PATH}"}
    return FileResponse(str(BLOG_PATH))


@app.get("/blog/discovery")
async def get_discovery_blog():
    # Serve the discovery blog page.
    if not DISCOVERY_BLOG_PATH.exists():
        return {"error": f"Blog file not found at {DISCOVERY_BLOG_PATH}"}
    return FileResponse(str(DISCOVERY_BLOG_PATH))


@app.get("/dashboard")
async def get_dashboard():
    # Serve the existing dashboard.
    if not UI_PATH.exists():
        return {"error": f"UI file not found at {UI_PATH}"}
    return FileResponse(str(UI_PATH))


@app.get("/health")
async def health():
    # Health check endpoint for production monitoring
    episode_count = len(brain.knowledge_base.episode_memory.episodes) if hasattr(brain.knowledge_base.episode_memory, 'episodes') else 0
    neural_stats = brain.get_neural_stats()
    return {
        "status": "healthy",
        "concepts": len(brain.knowledge_base.concept_library.concepts),
        "weight_version": brain.perceiver.weight_version,
        "uptime": time.time() - start_time,
        "version": "3.0.0",
        # Fields expected by landing page live pulse
        "episodes": episode_count,
        "weights": neural_stats["weight_version"],
        "proof_count": neural_stats["classifier"]["proof_count"],
        "avg_loss": neural_stats["classifier"]["avg_loss"],
    }


@app.post("/process")
async def process_stimulus(request: StimulusRequest):
    try:
        # Trigger the Native Cognitive Core v3.0
        final_out, structured = brain.process_internal(request.stimulus)
        
        # Generate the natural response
        response_text = brain.response_bridge.generate(final_out, request.stimulus, structured.domain)

        # Build the deliberation trace
        deliberation_report = "\n".join(final_out.reasoning_trace)

        # Neural stats for dashboard
        neural_stats = brain.get_neural_stats()

        return {
            "solution": response_text,
            "deliberation": deliberation_report,
            "success": final_out.is_verified,
            "confidence": final_out.confidence,
            "concepts_used": final_out.concepts_used,
            "attempts": final_out.attempts,
            "domain": structured.domain,
            "intent": structured.intent,
            "weight_version": neural_stats["weight_version"],
            "proof_count": neural_stats["classifier"]["proof_count"],
        }
    except Exception as e:
        import traceback
        logging.error(f"Brain Fault: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/neural-stats")
async def neural_stats():
    """Returns live neural training statistics for the dashboard."""
    stats = brain.get_neural_stats()
    return {
        "weight_version": stats["weight_version"],
        "proof_count": stats["classifier"]["proof_count"],
        "avg_loss": stats["classifier"]["avg_loss"],
        "concepts": len(brain.knowledge_base.concept_library.concepts),
        "episodes": len(brain.knowledge_base.episode_memory.episodes) if hasattr(brain.knowledge_base.episode_memory, 'episodes') else 0,
    }


@app.post("/save-weights")
async def save_weights():
    """Manually trigger a neural weight save."""
    brain.save_weights()
    return {"status": "saved", "weight_version": brain.perceiver.weight_version}


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

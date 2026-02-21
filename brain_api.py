from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import logging
import time

# Import the New HyperSymbolicBrain
from hnsds.brain.cognitive_core import HyperSymbolicBrain

app = FastAPI(title="HSCI Symbolic Brain API")
start_time = time.time()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Native Hyper-Symbolic Brain
brain = HyperSymbolicBrain()
UI_PATH = Path(__file__).resolve().parent / "ui" / "index.html"
LANDING_PATH = Path(__file__).resolve().parent / "ui" / "landing.html"


class StimulusRequest(BaseModel):
    stimulus: str


@app.get("/")
async def get_landing():
    # Serve the landing page.
    if not LANDING_PATH.exists():
        return {"error": f"Landing file not found at {LANDING_PATH}"}
    return FileResponse(str(LANDING_PATH))


@app.get("/dashboard")
async def get_dashboard():
    # Serve the existing dashboard.
    if not UI_PATH.exists():
        return {"error": f"UI file not found at {UI_PATH}"}
    return FileResponse(str(UI_PATH))


@app.get("/health")
async def health():
    # Health check endpoint for production monitoring
    # Count primordial episodes + learned episodes if file exists
    learned_count = 0
    if UI_PATH.parent.parent.joinpath("episodes.jsonl").exists():
        with open(UI_PATH.parent.parent / "episodes.jsonl", "r") as f:
            learned_count = sum(1 for _ in f)
            
    return {
        "status": "healthy",
        "episodes": len(brain.memory_lobe.primordial_episodes) + learned_count,
        "weights": len(brain.neural_lobe.cortex.weights) if hasattr(brain.neural_lobe.cortex, "weights") else 0,
        "uptime": time.time() - start_time,
        "version": "2.0.0"
    }


@app.post("/process")
async def process_stimulus(request: StimulusRequest):
    try:
        # ALWAYS start with a fresh brain to prevent trace leaks
        fresh_brain = HyperSymbolicBrain()
        
        # Trigger the Native Cognitive Core
        solution = fresh_brain.process(request.stimulus)

        # Extract the state of the mind after processing
        deliberation_report = fresh_brain.get_mind_state()

        return {
            "solution": solution,
            "deliberation": deliberation_report,
            "success": "COGNITIVE_FAILURE" not in str(solution),
        }
    except Exception as e:
        import traceback

        logging.error(f"Brain Fault: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import logging
import os

# Import the New HyperSymbolicBrain
from hnsds.brain.cognitive_core import HyperSymbolicBrain

app = FastAPI(title="HSCI Symbolic Brain API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the Native Hyper-Symbolic Brain
brain = HyperSymbolicBrain()

class StimulusRequest(BaseModel):
    stimulus: str

@app.get("/")
async def get_ui():
    # Serve the modern dashboard
    ui_path = os.path.join(os.getcwd(), "ui", "index.html")
    if not os.path.exists(ui_path):
        return {"error": "UI file not found. Ensure ui/index.html exists."}
    return FileResponse(ui_path)

@app.post("/process")
async def process_stimulus(request: StimulusRequest):
    try:
        # Trigger the Native Cognitive Core
        solution = brain.process(request.stimulus)
        
        # Extract the state of the mind after processing
        deliberation_report = brain.mind.get_trace()
        
        return {
            "solution": solution,
            "deliberation": deliberation_report,
            "success": "COGNITIVE_FAILURE" not in str(solution)
        }
    except Exception as e:
        import traceback
        logging.error(f"Brain Fault: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

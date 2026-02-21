# Add this to brain_api.py

from datetime import datetime
import time

# Global start time
START_TIME = time.time()


@app.get("/health")
async def health():
    """
    Health check endpoint for monitoring.
    Used by Render for uptime monitoring and container restart decisions.
    """
    import os
    import json

    try:
        # Check core components
        weights_exists = os.path.exists("synaptic_core.json")
        episodes_exists = os.path.exists("episodes.jsonl")

        # Get learning stats
        weights_size = 0
        episodes_count = 0

        if weights_exists:
            weights_size = os.path.getsize("synaptic_core.json")

        if episodes_exists:
            with open("episodes.jsonl", "r") as f:
                episodes_count = sum(1 for _ in f)

        uptime_seconds = time.time() - START_TIME

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": int(uptime_seconds),
            "brain": {
                "state": brain.mind.state if hasattr(brain, "mind") else "unknown",
                "episodes_count": episodes_count,
                "weights_file_kb": round(weights_size / 1024, 2),
                "learning_active": weights_exists and episodes_exists,
            },
            "system": {
                "weights_persisted": weights_exists,
                "episodes_persisted": episodes_exists,
                "version": "1.0",
                "architecture": "self-teaching-cognitive-engine",
            },
        }

    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        }, 503


@app.get("/stats")
async def stats():
    """
    Returns system statistics for monitoring dashboard.
    """
    import os
    import json

    weights_size = 0
    episodes_count = 0
    max_weight = 0

    if os.path.exists("synaptic_core.json"):
        with open("synaptic_core.json", "r") as f:
            weights = json.load(f)
            weights_size = os.path.getsize("synaptic_core.json")
            # Find max weight value
            for token_weights in weights.values():
                for value in token_weights.values():
                    max_weight = max(max_weight, value)

    if os.path.exists("episodes.jsonl"):
        with open("episodes.jsonl", "r") as f:
            episodes_count = sum(1 for _ in f)

    return {
        "learning_metrics": {
            "synaptic_weights_kb": round(weights_size / 1024, 2),
            "episodes_logged": episodes_count,
            "max_weight": round(max_weight, 3),
            "patterns_learned": (
                len(weights) if os.path.exists("synaptic_core.json") else 0
            ),
        },
        "system": {
            "uptime_seconds": int(time.time() - START_TIME),
            "timestamp": datetime.now().isoformat(),
        },
    }


# Usage in Render:
# 1. Health check: GET /health (Render calls every 30s)
# 2. Monitoring: GET /stats (Your dashboard)
#
# Expected response:
# {
#   "status": "healthy",
#   "brain": {
#     "episodes_count": 42,
#     "learning_active": true
#   }
# }

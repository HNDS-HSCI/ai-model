"""Main web app: serves the HSCI Mind (API under /v2, UI at /mind).

Equivalent to ``python -m hsci.mind.api``; kept so ``run_app.py`` and deployments
have one stable entry point (``brain_api:app``).
"""
from hsci.mind.api import app



if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))

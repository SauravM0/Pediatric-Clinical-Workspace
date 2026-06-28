"""Backward-compatible entrypoint.

Prefer:
    python -m uvicorn backend.server:app --reload --port 8077
"""

from backend.server import app


if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", "8077")))

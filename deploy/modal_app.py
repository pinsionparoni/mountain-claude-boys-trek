"""
The hosted demo on Modal: the built frontend and the coach API at one address.

    https://<workspace>--financial-coach-web.modal.run/       the app (installable on phones)
    https://<workspace>--financial-coach-web.modal.run/api/   the coach API (same paths as locally)

Deploy from the project root (frontend built first, Modal secret created once;
see SETUP.md "Hosted demo on Modal"):

    (cd frontend && npm run build)
    .venv/bin/modal deploy deploy/modal_app.py

Settings come from the Modal secret ``coach-env`` (DATABASE_URL, VERDA_BASE_URL,
VERDA_API_KEY, COACH_MODEL, COACH_TODAY), never from files in the image.
"""

from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIST = ROOT / "frontend" / "dist"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install_from_requirements(str(ROOT / "requirements.txt"))
    .add_local_python_source("coach")
    .add_local_dir(str(FRONTEND_DIST), "/frontend")
)

app = modal.App("financial-coach", image=image)


@app.function(
    secrets=[modal.Secret.from_name("coach-env")],
    # Conversations live in the server's memory, so every request must reach
    # the same container: never more than one.
    max_containers=1,
    # Stay warm for 20 minutes after the last request, then scale to zero
    # (a cold start loads the peer comparison data again: ~10-20 s).
    scaledown_window=20 * 60,
    timeout=10 * 60,  # long enough for a streamed chat answer
)
@modal.concurrent(max_inputs=50)
@modal.asgi_app()
def web():
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    from coach import api

    # The frontend calls /api/..., exactly as Vite forwards it in development.
    # A mounted app's own startup doesn't run, so the parent runs the coach's
    # (it preloads the peer comparison data in the background).
    site = FastAPI(title="Financial Coach demo", lifespan=api.lifespan)
    site.mount("/api", api.app)
    site.mount("/", StaticFiles(directory="/frontend", html=True), name="frontend")
    return site

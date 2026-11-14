"""
The hosted demo on Modal: the built frontend and the coach API at one address.

    https://<workspace>--financial-coach.modal.run/       the app (installable on phones)
    https://<workspace>--financial-coach.modal.run/api/   the coach API (same paths as locally)

Deploy from the project root (frontend built first, Modal secret created once;
see SETUP.md "Hosted demo on Modal"):

    (cd frontend && npm run build)
    .venv/bin/modal deploy deploy/modal_app.py

Settings come from the Modal secrets ``coach-env`` (DATABASE_URL, VERDA_BASE_URL,
VERDA_API_KEY, COACH_MODEL, COACH_TODAY) and ``coach-passcode`` (DEMO_PASSCODE),
never from files in the image.
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
    # coach-env: database, Verda and coach settings. coach-passcode: DEMO_PASSCODE,
    # which the app asks for on the login screen (kept apart so it can change alone).
    secrets=[modal.Secret.from_name("coach-env"), modal.Secret.from_name("coach-passcode")],
    # Keep customer data in Europe, next to Aiven (Frankfurt) and Verda.
    region="eu",
    # Conversations live in the server's memory, so every request must reach
    # the same container: never more than one.
    max_containers=1,
    # Stay warm for 20 minutes after the last request, then scale to zero
    # (a cold start loads the peer comparison data again: ~10-20 s).
    scaledown_window=20 * 60,
    timeout=10 * 60,  # long enough for a streamed chat answer
)
@modal.concurrent(max_inputs=50)
# Address: https://arvon-johannes--financial-coach.modal.run. Modal also
# answers at a ".us-east.modal.run" form of it: that's the region of Modal's
# web gateway, which every request passes through (see "Where the data goes"
# in TECH_STACK.md). The server itself runs in the EU (region="eu" above).
@modal.asgi_app(label="financial-coach")
def web():
    from fastapi import FastAPI
    from fastapi.staticfiles import StaticFiles

    from coach import api

    class Frontend(StaticFiles):
        """The built app, with caching that lets phones pick up new deploys.

        Modal's files are dated 1970 and StaticFiles sends no Cache-Control,
        so phones kept an old index.html (and with it the old app) for weeks.
        The page, manifest and service worker are now re-checked on every
        visit; files under assets/ have a content hash in their name, so they
        can be kept for good.
        """

        async def get_response(self, path, scope):
            response = await super().get_response(path, scope)
            if path.startswith("assets/"):
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            else:
                response.headers["Cache-Control"] = "no-cache"
            return response

    # The frontend calls /api/..., exactly as Vite forwards it in development.
    # A mounted app's own startup doesn't run, so the parent runs the coach's
    # (it preloads the peer comparison data in the background).
    site = FastAPI(title="Financial Coach demo", lifespan=api.lifespan)
    site.mount("/api", api.app)
    site.mount("/", Frontend(directory="/frontend", html=True), name="frontend")
    return site

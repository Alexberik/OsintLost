# OsintLost — Privacy Intelligence Lab

OsintLost is a privacy-first web app for self-audits and authorized image research.

## Features
- EXIF metadata inspection (selected fields; GPS presence only, exact coordinates hidden).
- SHA-256 and perceptual dHash file fingerprints.
- EXIF-stripped image export; temporary in-memory download token expires after 15 minutes.
- Manual public username self-audit links.
- Manual reverse-image research links: Google Lens, Bing Visual Search, TinEye, Yandex.
- Browser-local Evidence Vault with JSON export.
- Responsive interface, FastAPI backend, Docker, Render blueprint and CI tests.

## Privacy and safety
No face recognition, face embeddings, identity matching, scraping, private profile discovery, or collection of private addresses, phones or emails. Uploads are processed in memory and are not written to persistent storage. Exact GPS coordinates are never returned by the API. Use only your own images/accounts or content you are authorized to audit.

For public hosting use HTTPS and an edge rate limiter/WAF. External search providers have their own terms and privacy policies.

## Run locally
Python 3.10+:
    
    python -m venv .venv
    # Windows PowerShell: .venv\Scripts\Activate.ps1
    # macOS/Linux: source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn backend.server:app --host 127.0.0.1 --port 8090 --reload

Open http://127.0.0.1:8090

## Docker

    docker build -t osintlost .
    docker run --rm -p 8090:8090 osintlost

## Deploy
A Render blueprint is included in render.yaml. Connect the repository to Render and deploy the Docker web service. Configure a custom domain and HTTPS at the host. GitHub Pages cannot run the Python API; the full app requires a Python-capable host.

## API
- GET /api/health
- POST /api/analyze (multipart: file, consent=self_or_authorized)
- GET /api/clean/{id}
- GET /api/self-search?username=...
- GET /api/reverse-search
- GET /api/docs

## Configuration
- PORT (default 8090)
- LOST_MAX_UPLOAD_MB (default 15)

Run tests with pytest. MIT License.

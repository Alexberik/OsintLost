# OsintLost — Privacy Intelligence Lab

OsintLost is a privacy-first web application for self-audits and authorized image research.

## What it does
- Inspect selected EXIF fields (camera, date, software and GPS presence; exact GPS coordinates are never returned).
- Calculate SHA-256 and perceptual dHash fingerprints.
- Create an EXIF-stripped copy for download (temporary in-memory link, expires after 15 minutes).
- Generate manual public-search links for your own username.
- Open manual reverse-image research tools (Google Lens, Bing Visual Search, TinEye, Yandex).
- Keep an Evidence Vault locally in the browser and export it as JSON.
- Responsive dark UI, FastAPI backend, Docker deployment, Render Blueprint and CI tests.
- Public Privacy Policy and Terms pages at /privacy and /terms.

## Privacy and safety
The application does not perform face recognition, face embeddings, identity matching, scraping, private-profile discovery, or collection of private addresses, phones or emails. Uploaded images are processed in memory and are not written to persistent application storage. A cleaned copy remains in server memory for up to 15 minutes. Exact GPS coordinates are not returned by the API.

Evidence Vault records stay in browser localStorage. Hosting providers, reverse proxies and CDNs may independently process technical request logs such as IP addresses; review the selected host's privacy terms before launch.

Use only your own images/accounts or content you are authorized to audit. External reverse-image providers have their own privacy policies.

## Run locally
Python 3.10+:

    python -m venv .venv
    # Windows PowerShell: .venv\\Scripts\\Activate.ps1
    # macOS/Linux: source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn backend.server:app --host 127.0.0.1 --port 8090 --reload

Open http://127.0.0.1:8090

## Docker

    docker build -t osintlost .
    docker run --rm -p 8090:8090 osintlost

## Publish the public website
The repository includes render.yaml and a Dockerfile. To publish:
1. Sign in to Render and choose **New → Blueprint**.
2. Connect the GitHub repository **Alexberik/OsintLost** and select the branch **main** after the changes are merged.
3. Review the service settings and click **Apply**.
4. Wait for the deploy to finish, then open the generated `*.onrender.com` URL.
5. Test `/api/health`, upload an authorized test image, download the cleaned copy, and open `/privacy` and `/terms`.
6. Add a custom domain only after the generated Render URL works.

GitHub Pages alone cannot run the Python API. The complete application requires a Python-capable web host. The Render free service may sleep when idle and take time to wake up.

## Production notes
- Security response headers and image pixel limits are enabled.
- The built-in request limiter is process-local; use a host-level WAF/rate limiter for a public high-traffic deployment.
- No user accounts or server-side Evidence Vault are implemented. Do not treat this MVP as a multi-user case-management system.
- Before commercial use, the site owner should add contact details and review the legal pages for the applicable jurisdiction.

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
- LOST_MAX_IMAGE_PIXELS (default 40000000)

Run tests with `python -m pytest -q`.

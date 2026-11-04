#!/usr/bin/env python3
"""
OsintLost - OSINT People Search by Photo
v0.2 - local face detection (UltraFace) + social profile discovery
"""

import os
import json
import uuid
import cgi
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, quote

from face_detector import get_detector
from osint_core import (
    BASE_DIR, UPLOAD_DIR, REPORTS_DIR, FRONTEND_DIR, HAS_PIL,
    utcnow, get_file_hash, extract_exif,
    reverse_links, generate_username_candidates,
    social_profile_links, username_tool_links,
)

class LostHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0] if args else fmt}")

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path in ("/", "/index.html"):
            self._serve_file(FRONTEND_DIR / "index.html", "text/html; charset=utf-8")
            return

        if path.startswith("/uploads/"):
            name = path[len("/uploads/"):]
            fpath = UPLOAD_DIR / name
            if fpath.exists() and fpath.is_file():
                ctype = mimetypes.guess_type(str(fpath))[0] or "application/octet-stream"
                self._serve_file(fpath, ctype)
            else:
                self.send_error(404)
            return

        if path.startswith("/api/report/"):
            job_id = path.rstrip("/").split("/")[-1]
            rpath = REPORTS_DIR / f"{job_id}.json"
            if rpath.exists():
                self._json(json.loads(rpath.read_text(encoding="utf-8")))
            else:
                self.send_error(404)
            return

        if path == "/api/health":
            det = get_detector()
            self._json({
                "status": "ok",
                "name": "Lost",
                "version": "0.2.0",
                "pillow": HAS_PIL,
                "face_detector": det.available,
                "time": utcnow(),
            })
            return

        self.send_error(404)

    def do_POST(self):
        if self.path != "/api/analyze":
            self.send_error(404)
            return

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._json({"error": "Expected multipart/form-data"}, 400)
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type},
        )

        if "file" not in form or not form["file"].file:
            self._json({"error": "No file"}, 400)
            return

        fileitem = form["file"]
        data = fileitem.file.read()
        if len(data) > 15 * 1024 * 1024:
            self._json({"error": "File too large (max 15 MB)"}, 400)
            return

        name = (form.getvalue("name") or "").strip()
        username = (form.getvalue("username") or "").strip()
        extra = (form.getvalue("extra") or "").strip()

        job_id = str(uuid.uuid4())[:8]
        orig = fileitem.filename or "photo.jpg"
        ext = Path(orig).suffix.lower() or ".jpg"
        filename = f"{job_id}{ext}"
        save_path = UPLOAD_DIR / filename
        save_path.write_bytes(data)

        file_hash = get_file_hash(data)
        exif = extract_exif(save_path)
        gps = exif.get("gps")

        detector = get_detector()
        face_result = detector.detect(save_path)

        handles = generate_username_candidates(name, username)
        profile_links = social_profile_links(handles)
        tool_links = username_tool_links(handles)

        notes = []
        if face_result.get("count", 0) > 0:
            notes.append(f"Found faces: {face_result['count']} (local UltraFace)")
            for i, f in enumerate(face_result["faces"][:5], 1):
                notes.append(f"  Face #{i}: score={f['score']}, size={f['width']}x{f['height']}px")
        else:
            notes.append("No faces detected locally - still upload photo to Yandex / PimEyes")

        if gps:
            notes.append(f"GPS: {gps['lat']}, {gps['lon']}")
            notes.append(f"Map: https://www.google.com/maps?q={gps['lat']},{gps['lon']}")
        else:
            notes.append("No GPS in EXIF")

        if handles:
            notes.append(f"Username candidates generated: {len(handles)}")
            notes.append("Check profiles manually + run Sherlock/Maigret")

        notes.append("Required: Yandex Images -> PimEyes -> FaceCheck.ID -> Search4Faces")

        result = {
            "job_id": job_id,
            "filename": filename,
            "original_name": orig,
            "uploaded_at": utcnow(),
            "file_hash": file_hash,
            "size_bytes": len(data),
            "exif": {k: v for k, v in exif.items() if k != "raw"},
            "exif_raw": exif.get("raw", {}),
            "gps": gps,
            "faces": face_result,
            "face_detected": face_result.get("count", 0) > 0,
            "reverse_links": reverse_links(),
            "username_candidates": handles,
            "social_links": profile_links,
            "username_tools": tool_links,
            "name": name,
            "username": username,
            "extra": extra,
            "notes": notes,
            "image_url": f"/uploads/{filename}",
            "annotated_url": f"/uploads/{face_result['annotated_path']}" if face_result.get("annotated_path") else None,
        }

        (REPORTS_DIR / f"{job_id}.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self._json(result)

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path: Path, content_type: str):
        if not path.exists():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main():
    port = int(os.environ.get("PORT", 8090))
    det = get_detector()
    print(f"Lost v0.2  ->  http://0.0.0.0:{port}")
    print(f"  Pillow EXIF : {HAS_PIL}")
    print(f"  Face detect : {det.available}")
    server = HTTPServer(("0.0.0.0", port), LostHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
        server.server_close()


if __name__ == "__main__":
    main()

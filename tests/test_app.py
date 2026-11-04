from fastapi.testclient import TestClient
from PIL import Image
import io
from backend.server import app

client = TestClient(app)

def image_file():
    out = io.BytesIO()
    Image.new("RGB", (32, 24), (40, 120, 160)).save(out, format="JPEG")
    out.seek(0)
    return out

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["storage"] == "ephemeral"

def test_consent_required():
    r = client.post("/api/analyze", files={"file": ("x.jpg", image_file(), "image/jpeg")})
    assert r.status_code == 422

def test_analyze_and_clean():
    r = client.post("/api/analyze", data={"consent":"self_or_authorized"}, files={"file":("x.jpg",image_file(),"image/jpeg")})
    assert r.status_code == 200
    d = r.json()
    assert d["sha256"] and d["dhash"]
    assert d["gps_present"] is False
    assert client.get(d["clean_url"]).status_code == 200

def test_username_search_links():
    r = client.get("/api/self-search", params={"username":"my_handle"})
    assert r.status_code == 200
    assert "GitHub" in r.json()["links"]

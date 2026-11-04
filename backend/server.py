from __future__ import annotations
import hashlib, io, os, time, uuid
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, ExifTags, ImageOps, UnidentifiedImageError

ROOT=Path(__file__).resolve().parent.parent
FRONTEND=ROOT/"frontend"
MAX_BYTES=int(os.getenv("LOST_MAX_UPLOAD_MB","15"))*1024*1024
buckets:dict[str,deque[float]]=defaultdict(deque)
clean_images:dict[str,tuple[bytes,str,float]]={}
app=FastAPI(title="OsintLost",version="1.0.0",docs_url="/api/docs")
app.mount("/static",StaticFiles(directory=str(FRONTEND)),name="static")

def rate_check(request:Request):
    ip=request.client.host if request.client else "unknown"; now=time.monotonic(); q=buckets[ip]
    while q and now-q[0]>60:q.popleft()
    if len(q)>=20:raise HTTPException(429,"Too many requests. Wait one minute.")
    q.append(now)

def dhash(image):
    px=list(image.convert("L").resize((9,8)).getdata()); bits=[]
    for y in range(8):
        row=px[y*9:y*9+9]; bits.extend(1 if row[x]>row[x+1] else 0 for x in range(8))
    n=0
    for bit in bits:n=(n<<1)|bit
    return f"{n:016x}"

def metadata(image):
    out={}
    try:
        for key,value in image.getexif().items():
            name=ExifTags.TAGS.get(key,str(key))
            if name=="GPSInfo":out["GPS data"]="Present — exact coordinates hidden"
            elif name in {"Make","Model","DateTime","DateTimeOriginal","DateTimeDigitized","Software","Orientation","ImageDescription","Artist","Copyright"}:out[name]=str(value)[:160]
    except Exception:pass
    return out

@app.get("/",response_class=HTMLResponse)
async def home():return (FRONTEND/"index.html").read_text(encoding="utf-8")

@app.get("/api/health")
async def health():return {"status":"ok","app":"OsintLost","version":app.version,"storage":"ephemeral"}

@app.post("/api/analyze")
async def analyze(request:Request,file:UploadFile=File(...),consent:str=Form(...)):
    rate_check(request)
    if consent!="self_or_authorized":raise HTTPException(400,"Confirm you own this image or are authorized to analyze it.")
    raw=await file.read(MAX_BYTES+1)
    if not raw:raise HTTPException(400,"Empty upload.")
    if len(raw)>MAX_BYTES:raise HTTPException(413,f"Image exceeds {MAX_BYTES//1048576} MB.")
    try:
        im=Image.open(io.BytesIO(raw)); im.verify(); im=Image.open(io.BytesIO(raw)); fmt=(im.format or "").upper(); im=ImageOps.exif_transpose(im)
        w,h=im.size
        if fmt not in {"JPEG","JPG","PNG","WEBP","TIFF"}:raise HTTPException(415,"Supported: JPEG, PNG, WEBP, TIFF.")
        meta=metadata(im); fingerprint=dhash(im); digest=hashlib.sha256(raw).hexdigest()
        clean=im.convert("RGB"); out=io.BytesIO()
        if fmt in {"JPEG","JPG"}:clean.save(out,format="JPEG",quality=92,optimize=True); mime="image/jpeg"
        elif fmt=="WEBP":clean.save(out,format="WEBP",quality=92); mime="image/webp"
        else:clean.save(out,format="PNG",optimize=True); mime="image/png"
    except HTTPException:raise
    except (UnidentifiedImageError,OSError,ValueError):raise HTTPException(415,"Invalid or unsupported image.")
    except Exception:raise HTTPException(400,"Could not process image.")
    token=uuid.uuid4().hex; now=time.time(); clean_images[token]=(out.getvalue(),mime,now+900)
    for k,v in list(clean_images.items()):
        if v[2]<now:clean_images.pop(k,None)
    gps="GPS data" in meta; warnings=[]
    if gps:warnings.append("GPS metadata exists. Exact coordinates are intentionally hidden.")
    if any(k in meta for k in ("DateTime","DateTimeOriginal","DateTimeDigitized")):warnings.append("Capture date/time is embedded.")
    if any(k in meta for k in ("Make","Model")):warnings.append("Camera make/model is embedded.")
    if not meta:warnings.append("No selected EXIF fields found; other metadata formats may still exist.")
    warnings.append("A metadata-stripped copy is ready to download.")
    return {"id":token,"analyzed_at":datetime.now(timezone.utc).isoformat(),"filename":Path(file.filename or "image").name[:120],"size_bytes":len(raw),"sha256":digest,"dhash":fingerprint,"width":w,"height":h,"format":fmt,"metadata":meta,"gps_present":gps,"warnings":warnings,"clean_url":f"/api/clean/{token}","clean_expires_seconds":900,"storage":"not_persisted"}

@app.get("/api/clean/{token}")
async def clean_download(token:str):
    item=clean_images.get(token)
    if not item or item[2]<time.time():clean_images.pop(token,None);raise HTTPException(404,"Clean copy expired. Analyze again.")
    data,mime,_=item
    return Response(data,media_type=mime,headers={"Content-Disposition":'attachment; filename="osintlost-clean-image"',"Cache-Control":"no-store"})

@app.get("/api/self-search")
async def self_search(username:str):
    value=username.strip().lstrip("@")
    if not value or len(value)>80 or any(ord(c)<32 for c in value):raise HTTPException(400,"Enter a valid username.")
    q=quote('"'+value+'"')
    return {"query":value,"links":{"Google exact search":f"https://www.google.com/search?q={q}","Bing exact search":f"https://www.bing.com/search?q={q}","GitHub":f"https://github.com/search?q={quote(value)}&type=users","Reddit":f"https://www.reddit.com/search/?q={quote(value)}","YouTube":f"https://www.youtube.com/results?search_query={quote(value)}","TikTok search":f"https://www.tiktok.com/search?q={quote(value)}"},"note":"Manual public search only; no scraping or identity matching."}

@app.get("/api/reverse-search")
async def reverse_search():
    return {"links":{"Google Lens":"https://lens.google.com/","Bing Visual Search":"https://www.bing.com/visualsearch","TinEye":"https://tineye.com/","Yandex Images":"https://yandex.com/images/"}}

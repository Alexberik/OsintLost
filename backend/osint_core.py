#!/usr/bin/env python3
"""
Lost - OSINT People Search by Photo
v0.2 - local face detection (UltraFace) + social profile discovery
"""

import os
import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

try:
    from PIL import Image
    from PIL.ExifTags import TAGS, GPSTAGS
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
REPORTS_DIR = BASE_DIR / "reports"
FRONTEND_DIR = BASE_DIR / "frontend"

UPLOAD_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def extract_exif(image_path: Path) -> dict:
    result = {
        "camera": None, "datetime": None, "software": None,
        "width": None, "height": None, "format": None, "gps": None, "raw": {}
    }
    if not HAS_PIL:
        result["note"] = "Pillow not installed"
        return result
    try:
        img = Image.open(image_path)
        result["width"], result["height"] = img.size
        result["format"] = img.format
        exif_data = img._getexif()
        if not exif_data:
            return result
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if isinstance(value, bytes):
                try:
                    value = value.decode("utf-8", errors="ignore")
                except Exception:
                    value = str(value)[:80]
            result["raw"][str(tag)] = str(value)[:180]
            if tag == "Make":
                result["camera"] = str(value)
            elif tag == "Model":
                result["camera"] = ((result["camera"] or "") + " " + str(value)).strip()
            elif tag in ("DateTime", "DateTimeOriginal", "DateTimeDigitized") and not result["datetime"]:
                result["datetime"] = str(value)
            elif tag == "Software":
                result["software"] = str(value)
            elif tag == "GPSInfo":
                gps = {GPSTAGS.get(t, t): value[t] for t in value}
                lat = _to_deg(gps.get("GPSLatitude"), gps.get("GPSLatitudeRef"))
                lon = _to_deg(gps.get("GPSLongitude"), gps.get("GPSLongitudeRef"))
                if lat is not None and lon is not None:
                    result["gps"] = {"lat": lat, "lon": lon}
    except Exception as e:
        result["error"] = str(e)
    return result


def _to_deg(value, ref):
    if not value or not ref:
        return None
    try:
        d, m, s = float(value[0]), float(value[1]), float(value[2])
        res = d + m / 60.0 + s / 3600.0
        if ref in ("S", "W"):
            res = -res
        return round(res, 6)
    except Exception:
        return None


def reverse_links() -> dict:
    return {
        "Yandex Images": "https://yandex.com/images/",
        "Google Lens": "https://lens.google.com/",
        "Bing Visual Search": "https://www.bing.com/visualsearch",
        "TinEye": "https://tineye.com/",
        "PimEyes": "https://pimeyes.com/en",
        "FaceCheck.ID": "https://facecheck.id/",
        "Search4Faces": "https://search4faces.com/",
        "Lenso.ai": "https://lenso.ai/",
        "FaceSeek": "https://www.faceseek.online/",
        "VK Watch (RU)": "https://vk.watch/",
        "Geometria Faces (RU)": "https://geometria.ru/facesearch/",
    }


def generate_username_candidates(name: str, username: str = "") -> list:
    """Inspired by EagleEye2 — generate likely handles from a full name."""
    candidates = set()
    if username:
        u = username.strip().lstrip("@").lower()
        candidates.add(u)
        candidates.add(u.replace(".", "").replace("_", "").replace("-", ""))

    if not name:
        return sorted(candidates)

    tr = str.maketrans({
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
        "А": "A", "Б": "B", "В": "V", "Г": "G", "Д": "D", "Е": "E", "Ё": "E",
        "Ж": "Zh", "З": "Z", "И": "I", "Й": "Y", "К": "K", "Л": "L", "М": "M",
        "Н": "N", "О": "O", "П": "P", "Р": "R", "С": "S", "Т": "T", "У": "U",
        "Ф": "F", "Х": "H", "Ц": "Ts", "Ч": "Ch", "Ш": "Sh", "Щ": "Sch",
        "Ъ": "", "Ы": "Y", "Ь": "", "Э": "E", "Ю": "Yu", "Я": "Ya",
    })
    latin = name.translate(tr)
    parts = re.findall(r"[a-zA-Z0-9]+", latin)
    if not parts:
        return sorted(candidates)

    first = parts[0].lower()
    last = parts[-1].lower() if len(parts) > 1 else ""
    full = "".join(p.lower() for p in parts)

    variants = [
        first, last, full,
        f"{first}{last}", f"{first}.{last}", f"{first}_{last}", f"{first}-{last}",
        f"{last}{first}", f"{last}.{first}", f"{last}_{first}",
        f"{first[0]}{last}" if first else "",
        f"{first}{last[0]}" if last else "",
        f"{first[0]}.{last}" if first and last else "",
    ]
    for v in variants:
        if v and len(v) >= 2:
            candidates.add(v)
            candidates.add(v.replace(".", "").replace("_", "").replace("-", ""))

    return sorted(c for c in candidates if 2 <= len(c) <= 30)[:25]


def social_profile_links(handles: list) -> dict:
    platforms = {
        "Instagram": "https://www.instagram.com/{}/",
        "X / Twitter": "https://x.com/{}",
        "TikTok": "https://www.tiktok.com/@{}",
        "VK": "https://vk.com/{}",
        "Facebook": "https://www.facebook.com/{}",
        "GitHub": "https://github.com/{}",
        "Telegram": "https://t.me/{}",
        "YouTube": "https://www.youtube.com/@{}",
        "Reddit": "https://www.reddit.com/user/{}",
        "LinkedIn (search)": "https://www.linkedin.com/search/results/all/?keywords={}",
        "Pinterest": "https://www.pinterest.com/{}/",
        "Twitch": "https://www.twitch.tv/{}",
    }
    out = {}
    for h in handles[:8]:
        for plat, tpl in platforms.items():
            key = f"{plat} · {h}"
            out[key] = tpl.format(quote(h))
    return out


def username_tool_links(handles: list) -> dict:
    if not handles:
        return {}
    primary = handles[0]
    return {
        "Sherlock (all candidates)": f"sherlock {' '.join(handles[:5])}",
        "Maigret": f"maigret {primary}",
        "WhatsMyName": f"https://whatsmyname.app/?q={quote(primary)}",
        "Namechk": "https://namechk.com/",
        "Epieos": f"https://epieos.com/?q={quote(primary)}",
    }

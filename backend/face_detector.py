"""
Local face detection using UltraFace (ONNX) via onnxruntime.
No OpenCV required — pure numpy + Pillow.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

try:
    import onnxruntime as ort
    HAS_ORT = True
except ImportError:
    HAS_ORT = False

try:
    from PIL import Image, ImageDraw
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "version-RFB-320.onnx"

# UltraFace-320 priors (from official config)
_IMAGE_SIZE = (320, 240)  # W, H
_FEATURE_MAPS = [[40, 30], [20, 15], [10, 8], [5, 4]]
_MIN_BOXES = [[10, 16, 24], [32, 48], [64, 96], [128, 192, 256]]
_STEPS = [8, 16, 32, 64]
_CENTER_VARIANCE = 0.1
_SIZE_VARIANCE = 0.2


def _generate_priors() -> np.ndarray:
    priors = []
    for k, f in enumerate(_FEATURE_MAPS):
        min_sizes = _MIN_BOXES[k]
        for i in range(f[1]):
            for j in range(f[0]):
                cx = (j + 0.5) * _STEPS[k] / _IMAGE_SIZE[0]
                cy = (i + 0.5) * _STEPS[k] / _IMAGE_SIZE[1]
                for s in min_sizes:
                    w = s / _IMAGE_SIZE[0]
                    h = s / _IMAGE_SIZE[1]
                    priors.append([cx, cy, w, h])
    return np.clip(np.array(priors, dtype=np.float32), 0.0, 1.0)


_PRIORS = _generate_priors()  # (4420, 4)


def _decode(locations: np.ndarray, priors: np.ndarray) -> np.ndarray:
    """locations: (N, 4)  ->  corner boxes (x1,y1,x2,y2) normalized"""
    boxes = np.concatenate([
        locations[:, :2] * _CENTER_VARIANCE * priors[:, 2:] + priors[:, :2],
        np.exp(locations[:, 2:] * _SIZE_VARIANCE) * priors[:, 2:],
    ], axis=1)
    # center → corner
    boxes[:, :2] -= boxes[:, 2:] / 2
    boxes[:, 2:] += boxes[:, :2]
    return boxes


def _area(box: np.ndarray) -> float:
    return max(0.0, box[2] - box[0]) * max(0.0, box[3] - box[1])


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    inter = np.array([
        max(a[0], b[0]), max(a[1], b[1]),
        min(a[2], b[2]), min(a[3], b[3]),
    ])
    inter_a = _area(inter)
    return inter_a / (_area(a) + _area(b) - inter_a + 1e-6)


def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thresh: float = 0.3, top_k: int = 200) -> List[int]:
    order = scores.argsort()[::-1]
    if top_k > 0:
        order = order[:top_k]
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(int(i))
        if order.size == 1:
            break
        rest = order[1:]
        ious = np.array([_iou(boxes[i], boxes[j]) for j in rest])
        order = rest[ious <= iou_thresh]
    return keep


class FaceDetector:
    def __init__(self, model_path: Optional[Path] = None, conf_threshold: float = 0.65):
        self.conf_threshold = conf_threshold
        self.session = None
        self.input_name = None
        path = Path(model_path) if model_path else MODEL_PATH
        if HAS_ORT and path.exists():
            opts = ort.SessionOptions()
            opts.log_severity_level = 3
            self.session = ort.InferenceSession(str(path), sess_options=opts, providers=["CPUExecutionProvider"])
            self.input_name = self.session.get_inputs()[0].name

    @property
    def available(self) -> bool:
        return self.session is not None

    def detect(self, image_path: Path) -> Dict[str, Any]:
        """
        Returns:
          {
            faces: [{x1,y1,x2,y2, score, width, height}, ...],
            count: int,
            annotated_path: optional path to image with boxes drawn
          }
        """
        result = {"faces": [], "count": 0, "annotated_path": None, "engine": "ultraface-rfb-320"}

        if not self.available or not HAS_PIL:
            result["error"] = "Face detector not available"
            return result

        try:
            img = Image.open(image_path).convert("RGB")
        except Exception as e:
            result["error"] = str(e)
            return result

        orig_w, orig_h = img.size

        # preprocess
        resized = img.resize((320, 240), Image.BILINEAR)
        arr = np.asarray(resized, dtype=np.float32)
        arr = (arr - 127.0) / 128.0
        arr = arr.transpose(2, 0, 1)[np.newaxis, ...]  # 1,3,240,320

        confidences, boxes = self.session.run(None, {self.input_name: arr})
        # confidences: (1, 4420, 2)  boxes: (1, 4420, 4)

        scores = confidences[0][:, 1]  # face class
        locs = boxes[0]

        mask = scores > self.conf_threshold
        if not np.any(mask):
            return result

        scores = scores[mask]
        locs = locs[mask]
        decoded = _decode(locs, _PRIORS[mask])

        # scale to original image
        decoded[:, 0] *= orig_w
        decoded[:, 1] *= orig_h
        decoded[:, 2] *= orig_w
        decoded[:, 3] *= orig_h

        keep = _nms(decoded, scores, iou_thresh=0.3)
        faces = []
        for i in keep:
            x1, y1, x2, y2 = decoded[i]
            x1, y1 = max(0, int(x1)), max(0, int(y1))
            x2, y2 = min(orig_w - 1, int(x2)), min(orig_h - 1, int(y2))
            faces.append({
                "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                "score": float(round(float(scores[i]), 4)),
                "width": x2 - x1,
                "height": y2 - y1,
            })

        result["faces"] = faces
        result["count"] = len(faces)

        # draw annotated image
        if faces:
            draw = ImageDraw.Draw(img)
            for f in faces:
                draw.rectangle([f["x1"], f["y1"], f["x2"], f["y2"]], outline=(0, 229, 255), width=3)
                label = f"{f['score']:.2f}"
                draw.text((f["x1"] + 4, max(0, f["y1"] - 14)), label, fill=(0, 229, 255))
            ann_path = image_path.parent / f"ann_{image_path.name}"
            img.save(ann_path, quality=92)
            result["annotated_path"] = str(ann_path.name)

        return result


# singleton for the server
_detector: Optional[FaceDetector] = None


def get_detector() -> FaceDetector:
    global _detector
    if _detector is None:
        _detector = FaceDetector()
    return _detector

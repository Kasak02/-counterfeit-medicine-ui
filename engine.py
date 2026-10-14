"""
Engine interface for the pack-screening UI.

RIGHT NOW this is a STUB returning deterministic fake results so the UI can be
designed and tested. When the models are ready, replace `analyze_pack()` only.
The decision logic below (`generate_screening_decision`) is ported 1:1 from the
Colab notebook (Step 42), so keep it.

Real pipeline (from the notebook):
  image -> ResNet-18 triplet embedding -> visual distance / classifier
        -> EasyOCR (product, batch, mfg, expiry, confidence, evidence score)
        -> screening decision (visually consistent / review / high risk)
"""
from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass, field

from PIL import Image, ImageDraw

DEFAULT_THRESHOLD = 0.878  # VISUAL_THRESHOLD used in the notebook's final screening logic

# Notebook: calculate_ocr_evidence / interpret_ocr_score
EVIDENCE_LABELS = {
    0.0: "No OCR evidence",
    0.25: "Text detected, weak medicine evidence",
    0.40: "Low-confidence medicine text",
    0.60: "Medium-confidence medicine text",
    0.80: "High-confidence medicine text",
}


@dataclass
class OCR:
    method: str
    text_regions: int
    confidence: float
    raw_text: str
    product: str | None
    batch: str | None
    mfg: str | None
    expiry: str | None
    evidence_score: float

    @property
    def evidence_level(self) -> str:
        return EVIDENCE_LABELS[self.evidence_score]


@dataclass
class Screening:
    decision: str  # VISUALLY_CONSISTENT | REVIEW_REQUIRED | HIGH_SCREENING_RISK
    visual_consistent: bool
    warnings: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)


@dataclass
class Result:
    distance: float
    threshold: float
    ocr: OCR
    screening: Screening
    seconds: float = 0.0


def generate_screening_decision(distance, threshold, ocr_score, batch, mfg, expiry) -> Screening:
    """Ported from the notebook. Unreadable fields are WARNINGS, never red flags."""
    consistent = distance <= threshold
    warnings, red_flags = [], []
    if not consistent:
        red_flags.append("Visual appearance differs from the genuine reference profile")
    if ocr_score == 0:
        warnings.append("No readable text detected by OCR")
    elif ocr_score < 0.60:
        warnings.append("OCR text quality is limited")
    if batch is None:
        warnings.append("Batch number could not be verified from the image")
    if mfg is None:
        warnings.append("Manufacturing date could not be verified from the image")
    if expiry is None:
        warnings.append("Expiry date could not be verified from the image")
    if not consistent:
        decision = "HIGH_SCREENING_RISK"
    elif ocr_score >= 0.60:
        decision = "VISUALLY_CONSISTENT"
    else:
        decision = "REVIEW_REQUIRED"
    return Screening(decision, consistent, warnings, red_flags)


def analyze_pack(front_bytes: bytes, back_bytes: bytes,
                 threshold: float = DEFAULT_THRESHOLD, force: str | None = None) -> Result:
    """STUB. Visual check uses the FRONT photo; OCR reads FRONT + BACK (batch/dates are
    usually on the back). `force` in {"consistent","review","risk"} is for demo samples."""
    n = int(hashlib.sha256(front_bytes).hexdigest(), 16)
    m = int(hashlib.sha256(back_bytes).hexdigest(), 16)
    u = lambda k: ((n >> (k * 8)) & 0xFF) / 255.0
    ub = lambda k: ((m >> (k * 8)) & 0xFF) / 255.0

    if force == "consistent":
        dist, score = 0.45 + u(0) * 0.25, 0.60 + 0.20 * (u(1) > 0.5)
    elif force == "review":
        dist, score = 0.45 + u(0) * 0.25, [0.0, 0.25, 0.40][int(u(1) * 2.99)]
    elif force == "risk":
        dist, score = threshold + 0.08 + u(0) * 0.3, [0.25, 0.40, 0.60][int(u(1) * 2.99)]
    else:
        dist = 0.35 + u(0) * 0.9
        score = [0.0, 0.25, 0.40, 0.60, 0.80][int(u(1) * 4.99)]

    readable = score >= 0.40
    products = ["Paracetamol IP 500 mg", "Aceclofenac Tablets", "Azithromycin 500 mg",
                "Thiocolchicoside Tablets"]
    product = products[(n >> 16) % 4] if readable else None
    has_fields = score >= 0.60 and ub(2) > 0.25
    batch = f"C{240000 + m % 9999}" if has_fields else None
    mfg = "JAN 2024" if has_fields else None
    expiry = "DEC 2027" if has_fields else None
    conf = {0.0: 0.0, 0.25: 0.2, 0.40: 0.25, 0.60: 0.55, 0.80: 0.82}[score] + u(3) * 0.1
    raw = (f"Cipla | 10 x 15 Tablets | {product} | Analgesic | Effective relief" if readable
           else "Videx 6810 0 EOSFF GCLD 101 Faiaonls QC+O/O" if score else "")
    ocr = OCR("upscaled_primary" if score >= 0.6 else "upscaled_clahe_fallback",
              int(6 + u(4) * 30), round(conf, 4), raw, product, batch, mfg, expiry, score)
    scr = generate_screening_decision(dist, threshold, score, batch, mfg, expiry)
    return Result(round(dist, 6), threshold, ocr, scr, seconds=round(1.2 + u(5), 1))


def demo_image(kind: str, side: str = "front") -> bytes:
    """Draws a placeholder pack (front or back) so the demo works with no uploads."""
    palette = {"consistent": "#0f766e", "review": "#b45309", "risk": "#9f1239"}
    img = Image.new("RGB", (640, 420), "#ffffff")
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 620, 400], outline=palette[kind], width=6)
    d.rectangle([20, 20, 620, 110], fill=palette[kind])
    d.text((40, 55), f"DEMO PACK - {side.upper()}  (placeholder image)", fill="white")
    d.text((40, 150), f"Sample: {kind}", fill="#12201e")
    if side == "back":
        for i, t in enumerate(["Batch No.: ------", "Mfg. Date: ------", "Exp. Date: ------"]):
            d.text((40, 200 + i * 40), t, fill="#12201e")
    else:
        for i in range(4):
            d.rectangle([40, 200 + i * 40, 400 - i * 30, 215 + i * 40], fill="#d4dcda")
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()

"""
Engine interface for PharmaLens.

RIGHT NOW this is a STUB returning deterministic, plausible-looking results so the UI can be
designed and tested. When the models are ready, replace the body of `analyze_pack()` and keep
the dataclasses, so app.py does not change. Raw model numbers (distances, scores, confidences)
are deliberately NOT part of the Report: the UI shows plain-language statuses only.

Rule carried over from the notebook: a field that could not be READ is "unread" (neutral),
never a red flag.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date

# (key, question, roles)  - "No" is treated as a concern
QUESTIONS = [
    ("seal", "Is the carton or strip seal intact, with no sign of re-gluing?", ("Consumer", "Pharmacist")),
    ("print", "Is the printing sharp, with no smudges or spelling mistakes?", ("Consumer", "Pharmacist")),
    ("holo", "Does the hologram or security mark (if this brand has one) look right and shift as you tilt it?", ("Consumer", "Pharmacist")),
    ("pills", "Do the tablets or capsules look uniform in colour, size and markings?", ("Consumer", "Pharmacist")),
    ("source", "Did you buy it from a licensed pharmacy at a normal price?", ("Consumer",)),
    ("invoice", "Do the batch number and expiry date match the supplier invoice?", ("Pharmacist",)),
    ("distributor", "Was it supplied by an authorised distributor?", ("Pharmacist",)),
]

STATUS_LABEL = {"pass": "Looks consistent", "review": "Worth a closer look",
                "concern": "Concern", "unread": "Couldn't check"}


@dataclass
class Check:
    key: str
    label: str
    status: str  # pass | review | concern | unread
    detail: str


@dataclass
class PackInfo:
    product: str | None
    strength: str | None
    form: str | None
    manufacturer: str | None
    batch: str | None
    mfg: str | None
    expiry: str | None
    expiry_status: str | None  # in_date | expiring_soon | expired | None
    months_left: int | None


@dataclass
class Report:
    level: str  # low | moderate | high
    checks: list[Check]
    info: PackInfo
    answers: list[dict] = field(default_factory=list)  # {"q","a","concern"}
    role: str = "Consumer"
    closeup_given: bool = False


PRODUCTS = [
    ("Paracetamol", "500 mg", "Tablets", "Cipla Ltd."),
    ("Azithromycin", "500 mg", "Tablets", "Alkem Laboratories"),
    ("Amoxicillin", "250 mg", "Capsules", "Sun Pharmaceutical"),
    ("Cetirizine", "10 mg", "Tablets", "Mankind Pharma"),
    ("Aceclofenac + Paracetamol", "100 mg + 325 mg", "Tablets", "Micro Labs"),
]
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _fmt(y, m):
    return f"{MON[m - 1]} {y}"


def analyze_pack(front: bytes, back: bytes, closeup: bytes | None = None,
                 answers: dict | None = None, role: str = "Consumer") -> Report:
    """STUB. Replace with: visual check on `front`, OCR on `front`+`back`, security check on
    `closeup`, then combine. Must return a Report."""
    answers = answers or {}
    n = int(hashlib.sha256(front).hexdigest(), 16)
    m = int(hashlib.sha256(back).hexdigest(), 16)
    u = lambda k: ((n >> (k * 8)) & 0xFF) / 255.0
    ub = lambda k: ((m >> (k * 8)) & 0xFF) / 255.0

    base = u(0)
    level = "low" if base < 0.5 else ("moderate" if base < 0.8 else "high")

    # user's quick checks can raise the level, never lower it
    asked = [(k, q) for k, q, roles in QUESTIONS if role in roles]
    ans_rows = []
    concerns = 0
    for k, q in asked:
        a = answers.get(k)
        if a:
            bad = a == "No"
            concerns += bad
            ans_rows.append({"q": q, "a": a, "concern": bad})
    if concerns >= 3 or (level == "moderate" and concerns >= 2):
        level = "high"
    elif level == "low" and concerns >= 2:
        level = "moderate"

    s = {"low": "pass", "moderate": "review", "high": "concern"}[level]
    jitter = lambda x: "review" if (x > 0.8 and s == "pass") else s

    prod, strength, form, mfr = PRODUCTS[(n >> 16) % len(PRODUCTS)]
    text_ok = ub(1) > 0.12
    batch_ok = text_ok and ub(2) > 0.25
    dates_ok = text_ok and ub(3) > 0.25
    today = date.today()
    mfg_y, mfg_m = today.year - 1 - int(ub(4) * 1.5), 1 + int(ub(5) * 11)
    exp_months = -3 if ub(6) > 0.92 else int(1 + ub(7) * 34)
    exp_total = today.year * 12 + today.month - 1 + exp_months
    exp_y, exp_m = exp_total // 12, exp_total % 12 + 1
    batch = f"{'ABCDEFGH'[int(ub(8) * 7)]}{240000 + m % 99999}" if batch_ok else None
    expiry_status = None
    if dates_ok:
        expiry_status = "expired" if exp_months < 0 else ("expiring_soon" if exp_months <= 2 else "in_date")

    info = PackInfo(
        product=prod if text_ok else None, strength=strength if text_ok else None,
        form=form if text_ok else None, manufacturer=mfr if text_ok else None,
        batch=batch, mfg=_fmt(mfg_y, mfg_m) if dates_ok else None,
        expiry=_fmt(exp_y, exp_m) if dates_ok else None,
        expiry_status=expiry_status, months_left=exp_months if dates_ok else None)

    design = {"pass": "Layout, colours and logo placement match reference packaging.",
              "review": "Some differences from reference packaging, such as colour tone or logo spacing.",
              "concern": "Clear differences from reference packaging in layout and colour."}
    prnt = {"pass": "Text is crisp and evenly printed.",
            "review": "Print looks slightly uneven in places. A sharper photo may help.",
            "concern": "Blurred or misaligned text, with possible spelling errors."}
    sec = {"pass": "Seal and security mark look consistent with reference packs.",
           "review": "The security mark is hard to judge from this angle. Try a straighter, brighter photo.",
           "concern": "The seal or security mark looks different from reference packs."}

    checks = [
        Check("design", "Packaging design", jitter(ub(9)), design[jitter(ub(9))]),
        Check("print", "Print quality and spelling", s, prnt[s]),
        Check("text", "Label text",
              "pass" if text_ok else "unread",
              "Product name and composition were read clearly." if text_ok
              else "The text was too faint or blurry to read reliably."),
        Check("batch", "Batch number", "pass" if batch_ok else "unread",
              f"Batch {batch} found on the pack." if batch_ok
              else "No batch number could be read. Retake the back photo in better light."),
    ]
    if dates_ok:
        st_ = "concern" if expiry_status == "expired" else ("review" if expiry_status == "expiring_soon" else "pass")
        d = (f"Printed expiry date ({info.expiry}) has passed." if expiry_status == "expired"
             else f"Manufactured {info.mfg}, expires {info.expiry}.")
        checks.append(Check("dates", "Manufacture and expiry dates", st_, d))
    else:
        checks.append(Check("dates", "Manufacture and expiry dates", "unread",
                            "Dates could not be read from the photos."))
    if closeup:
        checks.append(Check("security", "Seal and security features", s, sec[s]))
    else:
        checks.append(Check("security", "Seal and security features", "unread",
                            "Not assessed. Add a close-up of the seal or hologram to check this."))
    return Report(level, checks, info, ans_rows, role, closeup is not None)

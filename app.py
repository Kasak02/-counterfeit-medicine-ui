"""PharmaLens – medicine pack screening (UI only, models stubbed)."""
import io
import json
import time
from datetime import datetime

import streamlit as st
from PIL import Image

import engine

APP_NAME = "PharmaLens"

st.set_page_config(page_title=APP_NAME, page_icon="💊", layout="wide",
                   initial_sidebar_state="collapsed")

CSS = """
<style>
:root{--teal:#0f766e;--ink:#12201e;--mute:#5b6b68;--line:#dfe6e4;
--ok:#0f766e;--okbg:#e6f4f1;--warn:#b45309;--warnbg:#fdf2e0;--bad:#9f1239;--badbg:#fde8ee;}
[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"]{display:none}
.block-container{padding-top:2.2rem;max-width:1180px}
h1,h2,h3{letter-spacing:-.01em}
.hero{background:linear-gradient(135deg,#0f766e 0%,#115e59 100%);color:#fff;border-radius:18px;
padding:26px 30px;margin-bottom:18px}
.hero h1{color:#fff;margin:0 0 4px;font-size:1.9rem}
.hero p{margin:0;opacity:.88;font-size:1rem}
.card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin-bottom:14px}
.card h4{margin:0 0 10px;font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;color:var(--mute)}
.verdict{border-radius:16px;padding:20px 24px;margin-bottom:14px;border:1px solid}
.verdict .t{font-size:1.6rem;font-weight:700;margin:0}
.verdict .s{margin:4px 0 0;font-size:.95rem}
.v-genuine{background:var(--okbg);border-color:#b7dfd8;color:#0a4f49}
.v-review{background:var(--warnbg);border-color:#f0d3a2;color:#7a3a05}
.v-counterfeit{background:var(--badbg);border-color:#f2b5c5;color:#6e0c27}
.meter{position:relative;height:12px;border-radius:99px;margin:26px 0 8px;
background:linear-gradient(90deg,#0f766e 0%,#0f766e 35%,#d9a441 50%,#9f1239 65%,#9f1239 100%)}
.meter .dot{position:absolute;top:-5px;width:22px;height:22px;border-radius:50%;background:#fff;
border:4px solid var(--ink);transform:translateX(-50%)}
.meter .tick{position:absolute;top:-8px;width:2px;height:28px;background:var(--ink);opacity:.55}
.scale{display:flex;justify-content:space-between;font-size:.75rem;color:var(--mute)}
.kv{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #eef2f1;font-size:.93rem}
.kv:last-child{border-bottom:0}.kv span:first-child{color:var(--mute)}.kv b{font-weight:600}
.pill{display:inline-block;padding:2px 10px;border-radius:99px;font-size:.78rem;font-weight:600}
.p-ok{background:var(--okbg);color:var(--ok)}.p-warn{background:var(--warnbg);color:var(--warn)}
.p-bad{background:var(--badbg);color:var(--bad)}
.step{display:flex;gap:14px;align-items:flex-start;padding:14px 0;border-bottom:1px solid #eef2f1}
.step:last-child{border:0}
.num{flex:0 0 34px;height:34px;border-radius:50%;background:var(--teal);color:#fff;display:flex;
align-items:center;justify-content:center;font-weight:700}
.step b{display:block}.step span{color:var(--mute);font-size:.92rem}
.disclaimer{font-size:.8rem;color:var(--mute);margin-top:6px}
.stButton>button[kind="primary"]{border-radius:10px;font-weight:600}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

ss = st.session_state
ss.setdefault("history", [])
ss.setdefault("current", None)

DECISIONS = {
    "VISUALLY_CONSISTENT": ("genuine", "🟢 Visually consistent",
        "The pack looks consistent with genuine reference packaging and the printed text was read with reasonable confidence."),
    "REVIEW_REQUIRED": ("review", "🟡 Review required",
        "The packaging looks consistent, but the printed text was too weak to back that up. Check the pack manually."),
    "HIGH_SCREENING_RISK": ("counterfeit", "🔴 High screening risk",
        "The packaging differs from the genuine reference profile. Do not use it until verified; consider reporting it."),
}


def pill(text, kind):
    return f'<span class="pill p-{kind}">{text}</span>'


def meter(frac, tick=None, left="", right=""):
    t = f'<div class="tick" style="left:{tick*100:.1f}%"></div>' if tick is not None else ""
    return (f'<div class="meter">{t}<div class="dot" style="left:{frac*100:.1f}%"></div></div>'
            f'<div class="scale"><span>{left}</span><span>{right}</span></div>')


def run_analysis(name, front, back, force=None):
    with st.status("Analysing pack…", expanded=True) as status:
        for msg in ("Preprocessing front and back photos", "Extracting visual embedding (front)",
                    "Comparing with genuine references", "Reading printed text (OCR, both sides)",
                    "Combining visual + text evidence"):
            st.write(msg)
            time.sleep(0.45)
        res = engine.analyze_pack(front, back, engine.DEFAULT_THRESHOLD, force)
        status.update(label="Analysis complete", state="complete", expanded=False)
    ss.current = {"name": name, "result": res, "time": datetime.now().strftime("%d %b %H:%M")}
    ss.history.insert(0, {"Time": ss.current["time"], "Pack": name,
                          "Result": DECISIONS[res.screening.decision][1][2:],
                          "Distance": res.distance, "Batch": res.ocr.batch or "—"})


def render_result(cur):
    r = cur["result"]
    kind, title, sub = DECISIONS[r.screening.decision]
    st.markdown(f'<div class="verdict v-{kind}"><p class="t">{title}</p><p class="s">{sub}</p></div>',
                unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Visual distance", f"{r.distance:.3f}", help="Lower = closer to genuine packaging")
    c2.metric("Threshold", f"{r.threshold:.3f}")
    c3.metric("OCR evidence", f"{r.ocr.evidence_score:.2f}", help=r.ocr.evidence_level)

    if r.screening.red_flags:
        st.markdown('<div class="card"><h4>🚨 Red flags</h4>' + "".join(
            f"<div class='kv' style='justify-content:flex-start'>{x}</div>"
            for x in r.screening.red_flags) + "</div>", unsafe_allow_html=True)
    if r.screening.warnings:
        st.markdown('<div class="card"><h4>⚠️ Could not verify</h4>' + "".join(
            f"<div class='kv' style='justify-content:flex-start'>{x}</div>"
            for x in r.screening.warnings) +
            '<div class="disclaimer">Fields the scan could not read are not signs of a fake pack. '
            "They are simply unverified.</div></div>", unsafe_allow_html=True)

    t_vis, t_ocr, t_rep = st.tabs(["Visual check", "Text on the pack", "Report"])
    with t_vis:
        pos = min(1.0, r.distance / 1.4)
        st.markdown('<div class="card"><h4>Distance from genuine reference profile</h4>' +
                    meter(pos, r.threshold / 1.4, "Close (consistent)", "Far (mismatch)") +
                    f'<div class="disclaimer">Black line = threshold ({r.threshold:.3f}). '
                    "Distance at or below the line is visually consistent.</div></div>",
                    unsafe_allow_html=True)
    with t_ocr:
        o = r.ocr
        lvl = "ok" if o.evidence_score >= 0.6 else "warn" if o.evidence_score >= 0.25 else "bad"
        nd = "Not detected"
        rows = [("Product name", o.product or nd), ("Batch number", o.batch or nd),
                ("Manufacturing date", o.mfg or nd), ("Expiry date", o.expiry or nd),
                ("Evidence level", pill(o.evidence_level, lvl)),
                ("OCR confidence", f"{o.confidence:.2f}"),
                ("Text regions", str(o.text_regions)), ("OCR method", o.method)]
        st.markdown('<div class="card"><h4>Extracted fields</h4>' +
                    "".join(f'<div class="kv"><span>{k}</span><b>{v}</b></div>' for k, v in rows) +
                    "</div>", unsafe_allow_html=True)
        with st.expander("Raw OCR text"):
            st.code(o.raw_text or "(nothing read)", language=None)
    with t_rep:
        payload = {"pack": cur["name"], "time": cur["time"], "decision": r.screening.decision,
                   "visual": {"distance": r.distance, "threshold": r.threshold,
                              "consistent": r.screening.visual_consistent},
                   "ocr": {**r.ocr.__dict__, "evidence_level": r.ocr.evidence_level},
                   "warnings": r.screening.warnings, "red_flags": r.screening.red_flags}
        st.json(payload, expanded=False)
        st.download_button("⬇️ Download report (JSON)", json.dumps(payload, indent=2),
                           file_name="pharmalens_report.json", mime="application/json")
    st.markdown('<div class="disclaimer">Screening aid only. It cannot confirm a medicine is genuine. '
                "Verify with the manufacturer or a licensed pharmacist.</div>", unsafe_allow_html=True)


def show_photo(col, data, label):
    with col:
        try:
            st.image(Image.open(io.BytesIO(data)), caption=label, use_container_width=True)
        except Exception:
            st.error(f"The {label.lower()} photo couldn't be read. Try a JPG or PNG.")


# ---------- header ----------
st.markdown(f'<div class="hero"><h1>💊 {APP_NAME}</h1>'
            "<p>Check a medicine pack. Add a photo of the front and the back; we compare the "
            "packaging design and read the printed text.</p></div>", unsafe_allow_html=True)

tab_check, tab_hist, tab_how = st.tabs(["🔍 Check a pack", "🕘 Scan history", "ℹ️ How it works"])

# ---------- check ----------
with tab_check:
    left, right = st.columns([5, 6], gap="large")
    with left:
        src = st.radio("Image source", ["Upload photos", "Try a demo"], horizontal=True,
                       label_visibility="collapsed")
        front = back = force = None
        name = "pack"
        if src == "Upload photos":
            cf, cb = st.columns(2)
            f = cf.file_uploader("Front of pack", type=["jpg", "jpeg", "png", "webp"],
                                 key="up_front", help="Brand name and artwork side.")
            b = cb.file_uploader("Back of pack", type=["jpg", "jpeg", "png", "webp"],
                                 key="up_back", help="Batch number and dates are usually here.")
            if f and b:
                front, back, name = f.getvalue(), b.getvalue(), f.name
            if f or b:
                p1, p2 = st.columns(2)
                if f:
                    show_photo(p1, f.getvalue(), "Front")
                if b:
                    show_photo(p2, b.getvalue(), "Back")
            if not (f or b):
                st.markdown('<div class="card"><h4>Tips for good photos</h4>'
                            "• Flat, front-facing, no glare<br>• Back photo should show batch "
                            "number and dates<br>• One pack per scan<br>• On a phone, the upload "
                            "button also opens the camera</div>", unsafe_allow_html=True)
        else:
            kind = st.segmented_control("Demo outcome", ["consistent", "review", "risk"],
                                        default="consistent", format_func=str.capitalize) or "consistent"
            front = engine.demo_image(kind, "front")
            back = engine.demo_image(kind, "back")
            force, name = kind, f"demo_{kind}"
            p1, p2 = st.columns(2)
            show_photo(p1, front, "Front")
            show_photo(p2, back, "Back")

        ready = front is not None and back is not None
        if not ready and src == "Upload photos":
            st.caption("Add both the front and the back photo to continue.")
        if st.button("🔍 Check pack", type="primary", disabled=not ready, use_container_width=True):
            run_analysis(name, front, back, force)

    with right:
        if ss.current:
            render_result(ss.current)
        else:
            st.markdown('<div class="card" style="text-align:center;padding:60px 20px">'
                        '<div style="font-size:2.6rem">📦</div><b>No result yet</b><br>'
                        '<span style="color:var(--mute)">Add both photos and press Check pack.</span></div>',
                        unsafe_allow_html=True)

# ---------- history ----------
with tab_hist:
    if not ss.history:
        st.info("Nothing scanned in this session yet.")
    else:
        labels = ["Visually consistent", "Review required", "High screening risk"]
        opts = st.multiselect("Filter by result", labels, default=labels)
        st.dataframe([h for h in ss.history if h["Result"] in opts], use_container_width=True,
                     hide_index=True,
                     column_config={"Distance": st.column_config.NumberColumn(format="%.3f")})
        if st.button("Clear history"):
            ss.history, ss.current = [], None
            st.rerun()

# ---------- how it works ----------
with tab_how:
    steps = [
        ("Front photo: image check", "A ResNet-18 model turns the front of the pack into a fingerprint "
                                    "and measures how far it is from the genuine reference profile."),
        ("Both photos: text check", "OCR reads the product name, batch number and dates from both "
                                   "sides and scores how trustworthy the printed text looks."),
        ("Decision", "Far from genuine means high screening risk. Close to genuine with readable "
                     "text means visually consistent. Close but unreadable means review required."),
        ("Warnings", "Fields the scan could not read are listed as unverified. They are never "
                     "treated as proof of a fake."),
    ]
    st.markdown('<div class="card">' + "".join(
        f'<div class="step"><div class="num">{i}</div><div><b>{t}</b><span>{d}</span></div></div>'
        for i, (t, d) in enumerate(steps, 1)) + "</div>", unsafe_allow_html=True)
    st.warning("Limits: tested on a small dataset, and OCR often misses batch numbers and dates. "
               "Treat results as a screening aid.", icon="⚠️")
    st.caption("UI preview · models not connected yet")

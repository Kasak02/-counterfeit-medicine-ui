"""PharmaLens – medicine pack screening. UI only: models are not connected yet."""
import html
import io
import time
from datetime import datetime

import streamlit as st
from PIL import Image

import engine

APP_NAME = "PharmaLens"
st.set_page_config(page_title=APP_NAME, page_icon="💊", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
:root{--teal:#0f766e;--ink:#12201e;--mute:#5b6b68;--line:#dfe6e4;
--ok:#0f766e;--okbg:#e6f4f1;--warn:#b45309;--warnbg:#fdf2e0;--bad:#9f1239;--badbg:#fde8ee;}
[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"]{display:none}
.block-container{padding-top:2.2rem;max-width:1120px}
.hero{background:linear-gradient(135deg,#0f766e 0%,#115e59 100%);color:#fff;border-radius:18px;
padding:26px 30px;margin-bottom:14px}
.hero h1{color:#fff;margin:0 0 6px;font-size:1.9rem;letter-spacing:-.01em}
.hero p{margin:0;opacity:.9;font-size:1.02rem;max-width:720px}
.card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin-bottom:14px}
.card h4{margin:0 0 10px;font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;color:var(--mute)}
.stepper{display:flex;gap:10px;margin:6px 0 18px;flex-wrap:wrap}
.stp{display:flex;align-items:center;gap:8px;font-size:.9rem;color:var(--mute)}
.stp i{font-style:normal;width:26px;height:26px;border-radius:50%;display:flex;align-items:center;
justify-content:center;background:#e3eae8;color:var(--mute);font-weight:700;font-size:.8rem}
.stp.on{color:var(--ink);font-weight:600}.stp.on i{background:var(--teal);color:#fff}
.stp.done i{background:var(--okbg);color:var(--ok)}
.stp.sep{color:#c3cfcc}
.lvl-card{border-radius:16px;padding:22px 26px;margin-bottom:14px;border:1px solid}
.lvl-card .t{font-size:1.7rem;font-weight:700;margin:0}
.lvl-card .s{margin:6px 0 14px;font-size:.98rem;max-width:640px}
.lvl-low{background:var(--okbg);border-color:#b7dfd8;color:#0a4f49}
.lvl-moderate{background:var(--warnbg);border-color:#f0d3a2;color:#7a3a05}
.lvl-high{background:var(--badbg);border-color:#f2b5c5;color:#6e0c27}
.bar{display:flex;gap:6px;max-width:420px}
.bar span{flex:1;height:8px;border-radius:99px;background:rgba(0,0,0,.1)}
.lvl-low .bar span:nth-child(1){background:#0f766e}
.lvl-moderate .bar span:nth-child(-n+2){background:#d9890f}
.lvl-high .bar span{background:#9f1239}
.barlab{display:flex;gap:6px;max-width:420px;font-size:.72rem;margin-top:5px;opacity:.8}
.barlab span{flex:1}
.chk{display:flex;gap:12px;align-items:flex-start;padding:11px 0;border-bottom:1px solid #eef2f1}
.chk:last-child{border:0}
.ico{flex:0 0 26px;height:26px;border-radius:50%;display:flex;align-items:center;justify-content:center;
font-weight:700;font-size:.85rem}
.s-pass{background:var(--okbg);color:var(--ok)}.s-review{background:var(--warnbg);color:var(--warn)}
.s-concern{background:var(--badbg);color:var(--bad)}.s-unread{background:#eceff0;color:#6b7775}
.chk b{display:block;font-size:.95rem}.chk .d{color:var(--mute);font-size:.88rem}
.chk .st{margin-left:auto;font-size:.74rem;font-weight:600;white-space:nowrap;padding:2px 9px;border-radius:99px}
.kv{display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-bottom:1px solid #eef2f1;font-size:.92rem}
.kv:last-child{border:0}.kv span:first-child{color:var(--mute)}.kv b{font-weight:600;text-align:right}
.pill{display:inline-block;padding:2px 10px;border-radius:99px;font-size:.76rem;font-weight:600}
.alert{border-radius:12px;padding:12px 16px;margin-bottom:14px;font-size:.92rem;border:1px solid}
.a-bad{background:var(--badbg);border-color:#f2b5c5;color:#6e0c27}
.a-warn{background:var(--warnbg);border-color:#f0d3a2;color:#7a3a05}
.todo{display:flex;gap:12px;padding:9px 0;font-size:.93rem}
.todo i{font-style:normal;flex:0 0 24px;height:24px;border-radius:50%;background:var(--teal);color:#fff;
font-size:.78rem;font-weight:700;display:flex;align-items:center;justify-content:center}
.disclaimer{font-size:.8rem;color:var(--mute);margin-top:6px}
.opt{font-size:.72rem;background:#eceff0;color:#5b6b68;border-radius:99px;padding:1px 8px;margin-left:6px}
.stButton>button[kind="primary"]{border-radius:10px;font-weight:600}
</style>
""", unsafe_allow_html=True)

ss = st.session_state
for k, v in {"history": [], "step": 1, "photos": {}, "upn": {"front": 0, "back": 0, "close": 0},
             "answers": {}, "report": None, "role": "Consumer"}.items():
    ss.setdefault(k, v)

LEVELS = {
    "low": ("Low suspicion",
            "Nothing in the photos points to a fake. That is reassuring, but it is not proof the pack is genuine."),
    "moderate": ("Moderate suspicion",
                 "A few things look off. Verify this pack before you use it."),
    "high": ("High suspicion",
             "Several signs suggest this pack may be counterfeit. Do not use it until it has been verified."),
}
ICON = {"pass": "✓", "review": "!", "concern": "✕", "unread": "–"}


def next_steps(level, role, expired):
    if role == "Pharmacist":
        steps = {
            "low": ["Record the batch number and match it with the supplier invoice.",
                    "Store and dispense as normal, and keep this check with your stock records.",
                    "Re-check any pack from the same batch that looks different."],
            "moderate": ["Set this stock aside until it is verified.",
                         "Confirm the batch with the manufacturer or your distributor, using the batch number on the pack.",
                         "Retake the photos in better light and run the check again."],
            "high": ["Quarantine the stock and mark it 'do not dispense'.",
                     "Keep the packs, invoice and these photos as evidence.",
                     "Notify your distributor and the state drug control authority or CDSCO.",
                     "Check other packs from the same batch and supplier."],
        }[level]
    else:
        steps = {
            "low": ["Keep the pack, bill and batch number until the course is finished.",
                    "If the medicine looks, tastes or works differently from usual, stop and ask a pharmacist.",
                    "Buy from licensed pharmacies and ask for a bill."],
            "moderate": ["Do not start or continue this medicine until it is verified.",
                         "Show the pack to a pharmacist, or call the manufacturer's customer care number printed on it.",
                         "Retake the photos in better light and check again."],
            "high": ["Do not use this medicine.",
                     "Keep the pack, bill and packaging. Do not throw them away.",
                     "Tell the pharmacy you bought it from, and report it to your state drug control authority or CDSCO.",
                     "If you have already taken it and feel unwell, get medical help promptly."],
        }[level]
    if expired:
        steps = ["The printed expiry date has passed. Do not use this medicine, even if it is genuine."] + steps
    return steps


def photos_ok():
    return "front" in ss.photos and "back" in ss.photos


def stepper():
    labels = ["Photos", "Quick checks", "Result"]
    out = []
    for i, lab in enumerate(labels, 1):
        cls = "on" if ss.step == i else ("done" if ss.step > i else "")
        out.append(f'<div class="stp {cls}"><i>{"✓" if ss.step > i else i}</i>{lab}</div>')
        if i < 3:
            out.append('<div class="stp sep">—</div>')
    st.markdown(f'<div class="stepper">{"".join(out)}</div>', unsafe_allow_html=True)


def photo_slot(col, side, label, hint, optional=False):
    with col:
        st.markdown(f"**{label}**" + ('<span class="opt">optional</span>' if optional else ""),
                    unsafe_allow_html=True)
        st.caption(hint)
        p = ss.photos.get(side)
        if p:
            st.image(p["bytes"], use_container_width=True)
            if st.button("Remove", key=f"rm_{side}"):
                del ss.photos[side]
                ss.upn[side] += 1
                st.rerun()
        else:
            f = st.file_uploader(label, type=["jpg", "jpeg", "png", "webp"],
                                 key=f"up_{side}_{ss.upn[side]}", label_visibility="collapsed")
            if f:
                data = f.getvalue()
                try:
                    Image.open(io.BytesIO(data)).verify()
                except Exception:
                    st.error("That file couldn't be read as an image. Try a JPG or PNG.")
                    return
                ss.photos[side] = {"name": f.name, "bytes": data}
                st.rerun()


def go(step):
    ss.step = step


def save_answers():
    ss.answers = {k: ss.get(f"q_{k}") for k, _, _ in engine.QUESTIONS if ss.get(f"q_{k}")}


def run_check():
    save_answers()
    with st.status("Checking your pack…", expanded=True) as status:
        for msg in ("Preparing the photos", "Comparing the packaging design",
                    "Reading the printed text and dates", "Checking seals and security marks",
                    "Putting the findings together"):
            st.write(msg)
            time.sleep(0.45)
        status.update(label="Check complete", state="complete", expanded=False)
    rep = engine.analyze_pack(ss.photos["front"]["bytes"], ss.photos["back"]["bytes"],
                              ss.photos["close"]["bytes"] if "close" in ss.photos else None,
                              ss.answers, ss.role)
    stamp = datetime.now().strftime("%d %b %Y, %H:%M")
    ss.report = rep
    ss.history.insert(0, {"id": len(ss.history) + 1, "time": stamp, "report": rep})
    ss.step = 3


def build_report_html(rep, stamp):
    e = html.escape
    rows = "".join(f"<tr><td>{e(c.label)}</td><td>{e(engine.STATUS_LABEL[c.status])}</td>"
                   f"<td>{e(c.detail)}</td></tr>" for c in rep.checks)
    i = rep.info
    info = "".join(f"<tr><td>{e(k)}</td><td>{e(v or 'Not read')}</td></tr>" for k, v in [
        ("Product", i.product), ("Strength", i.strength), ("Form", i.form),
        ("Manufacturer", i.manufacturer), ("Batch", i.batch), ("Manufactured", i.mfg),
        ("Expiry", i.expiry)])
    steps = "".join(f"<li>{e(s)}</li>" for s in next_steps(rep.level, rep.role,
                                                           i.expiry_status == "expired"))
    return f"""<!doctype html><meta charset="utf-8"><title>{APP_NAME} report</title>
<style>body{{font-family:system-ui,sans-serif;max-width:760px;margin:30px auto;color:#12201e;padding:0 16px}}
table{{border-collapse:collapse;width:100%;margin:8px 0 18px}}td{{border:1px solid #dfe6e4;padding:8px;
vertical-align:top;font-size:14px}}h1{{margin-bottom:0}}small{{color:#5b6b68}}</style>
<h1>{APP_NAME} report</h1><small>{e(stamp)} · checked as {e(rep.role)}</small>
<h2>{e(LEVELS[rep.level][0])}</h2><p>{e(LEVELS[rep.level][1])}</p>
<h3>What was checked</h3><table>{rows}</table>
<h3>Pack details as read</h3><table>{info}</table>
<h3>What to do next</h3><ol>{steps}</ol>
<p><small>Screening aid only. It cannot confirm that a medicine is genuine. Verify with the
manufacturer or a licensed pharmacist. Preview build: results are illustrative until the detection
models are connected.</small></p>"""


def render_report(rep, stamp, key):
    t, sub = LEVELS[rep.level]
    st.markdown(
        f'<div class="lvl-card lvl-{rep.level}"><p class="t">{t}</p><p class="s">{sub}</p>'
        '<div class="bar"><span></span><span></span><span></span></div>'
        '<div class="barlab"><span>Low</span><span>Moderate</span><span>High</span></div></div>',
        unsafe_allow_html=True)
    i = rep.info
    if i.expiry_status == "expired":
        st.markdown('<div class="alert a-bad"><b>Expired.</b> The printed expiry date has passed. '
                    "Do not use this medicine, even if it is genuine.</div>", unsafe_allow_html=True)
    elif i.expiry_status == "expiring_soon":
        st.markdown('<div class="alert a-warn"><b>Expiring soon.</b> Check the date on the pack '
                    "before you use it.</div>", unsafe_allow_html=True)

    left, right = st.columns([6, 5], gap="large")
    with left:
        rows = "".join(
            f'<div class="chk"><div class="ico s-{c.status}">{ICON[c.status]}</div>'
            f'<div><b>{html.escape(c.label)}</b><span class="d">{html.escape(c.detail)}</span></div>'
            f'<div class="st s-{c.status}">{engine.STATUS_LABEL[c.status]}</div></div>' for c in rep.checks)
        st.markdown(f'<div class="card"><h4>What we checked</h4>{rows}'
                    '<div class="disclaimer">"Couldn\'t check" means we could not read or assess it. '
                    "It does not count against the pack.</div></div>", unsafe_allow_html=True)
        if rep.answers:
            ar = "".join(
                f'<div class="chk"><div class="ico s-{"concern" if a["concern"] else "pass"}">'
                f'{"✕" if a["concern"] else "✓"}</div><div><span class="d">{html.escape(a["q"])}</span>'
                f'</div><div class="st">{a["a"]}</div></div>' for a in rep.answers)
            st.markdown(f'<div class="card"><h4>Your answers</h4>{ar}</div>', unsafe_allow_html=True)
    with right:
        exp_pill = ""
        if i.expiry_status:
            k, lab = {"in_date": ("ok", "In date"), "expiring_soon": ("warn", "Expiring soon"),
                      "expired": ("bad", "Expired")}[i.expiry_status]
            colors = {"ok": "background:#e6f4f1;color:#0f766e", "warn": "background:#fdf2e0;color:#b45309",
                      "bad": "background:#fde8ee;color:#9f1239"}[k]
            exp_pill = f' <span class="pill" style="{colors}">{lab}</span>'
        nr = "Not read"
        det = [("Product", i.product), ("Strength", i.strength), ("Form", i.form),
               ("Manufacturer", i.manufacturer), ("Batch", i.batch), ("Manufactured", i.mfg)]
        kv = "".join(f'<div class="kv"><span>{k}</span><b>{html.escape(v) if v else nr}</b></div>'
                     for k, v in det)
        kv += f'<div class="kv"><span>Expiry</span><b>{html.escape(i.expiry) if i.expiry else nr}{exp_pill}</b></div>'
        st.markdown(f'<div class="card"><h4>Pack details as read</h4>{kv}</div>', unsafe_allow_html=True)
        todo = "".join(f'<div class="todo"><i>{n}</i><span>{html.escape(s)}</span></div>'
                       for n, s in enumerate(next_steps(rep.level, rep.role, i.expiry_status == "expired"), 1))
        st.markdown(f'<div class="card"><h4>What to do next</h4>{todo}</div>', unsafe_allow_html=True)

    st.download_button("⬇️ Download report", build_report_html(rep, stamp),
                       file_name="pharmalens_report.html", mime="text/html", key=f"dl_{key}")
    with st.expander("How to report a suspected fake"):
        st.markdown(
            "- Keep the pack, the bill and any leftover tablets in a sealed bag.\n"
            "- Tell the pharmacy or seller where you got it.\n"
            "- Report it to your **state drug control department** or to **CDSCO**.\n"
            "- Report any side effects to your doctor or the national pharmacovigilance programme.")
    st.markdown('<div class="disclaimer">Screening aid only. It cannot confirm that a medicine is genuine. '
                "Verify with the manufacturer or a licensed pharmacist. Preview build: results are "
                "illustrative until the detection models are connected.</div>", unsafe_allow_html=True)


# ---------- header ----------
st.markdown(f'<div class="hero"><h1>💊 {APP_NAME}</h1>'
            "<p>Spot a suspicious medicine pack before you use it. Add photos of the front and back, "
            "answer a few quick questions and get a clear, plain-language result.</p></div>",
            unsafe_allow_html=True)
st.radio("I'm checking as", ["Consumer", "Pharmacist"], horizontal=True, key="role")

tab_check, tab_hist, tab_guide, tab_about = st.tabs(
    ["🔍 Check a pack", "🕘 My scans", "📖 Spot a fake", "ℹ️ About"])

# ---------- check ----------
with tab_check:
    stepper()
    if ss.step == 1:
        st.markdown("#### Add photos of the pack")
        c1, c2, c3 = st.columns(3, gap="medium")
        photo_slot(c1, "front", "Front", "Brand name and artwork side.")
        photo_slot(c2, "back", "Back", "Batch number and dates are usually here.")
        photo_slot(c3, "close", "Close-up", "Seal, hologram or blister foil.", optional=True)
        st.markdown('<div class="card" style="margin-top:8px"><h4>Tips for good photos</h4>'
                    "Lay the pack flat in daylight, avoid glare and shadows, and keep the text sharp. "
                    "On a phone, the upload button also opens the camera.</div>", unsafe_allow_html=True)
        if not photos_ok():
            st.caption("Add the front and back photos to continue.")
        st.button("Next: quick checks →", type="primary", disabled=not photos_ok(),
                  on_click=go, args=(2,))

    elif ss.step == 2:
        st.markdown("#### A few quick questions")
        st.caption("All optional. What you can see in person helps the result.")
        for k, q, roles in engine.QUESTIONS:
            if ss.role in roles:
                st.markdown(f"<div style='margin-top:10px'>{html.escape(q)}</div>", unsafe_allow_html=True)
                st.segmented_control(q, ["Yes", "No", "Not sure"], key=f"q_{k}",
                                     default=ss.answers.get(k), label_visibility="collapsed")
        st.write("")
        b1, b2, _ = st.columns([1, 2, 3])
        b1.button("← Back", on_click=lambda: (save_answers(), go(1)))
        if b2.button("🔍 Check pack", type="primary", use_container_width=True):
            run_check()
            st.rerun()

    else:
        if ss.report is None:
            ss.step = 1
            st.rerun()
        render_report(ss.report, ss.history[0]["time"], "cur")

        def reset():
            ss.photos, ss.answers, ss.report, ss.step = {}, {}, None, 1
            for s in ss.upn:
                ss.upn[s] += 1
        st.button("Start a new check", on_click=reset)

# ---------- history ----------
with tab_hist:
    if not ss.history:
        st.info("Nothing checked in this session yet. Your scans will appear here.")
    else:
        names = {"low": "Low", "moderate": "Moderate", "high": "High"}
        rows = [{"#": h["id"], "Time": h["time"],
                 "Product": h["report"].info.product or "Not read",
                 "Batch": h["report"].info.batch or "—",
                 "Suspicion": names[h["report"].level], "Checked as": h["report"].role}
                for h in ss.history]
        flt = st.multiselect("Filter by suspicion", list(names.values()), default=list(names.values()))
        shown = [r for r in rows if r["Suspicion"] in flt]
        st.dataframe(shown, use_container_width=True, hide_index=True)
        if shown:
            pick = st.selectbox("Open a past result", [f'#{r["#"]} · {r["Time"]} · {r["Product"]}' for r in shown])
            h = next(x for x in ss.history if x["id"] == int(pick.split("·")[0].strip("# ")))
            render_report(h["report"], h["time"], f"h{h['id']}")
        if st.button("Clear my scans"):
            ss.history, ss.report = [], None
            st.rerun()

# ---------- guide ----------
with tab_guide:
    st.markdown("### How to spot a suspicious pack yourself")
    st.caption("These checks take a minute and need nothing but your eyes. No single sign proves a fake, "
               "but several together are a reason to stop.")
    tips = [
        ("🖨️ Print quality", "Text should be sharp and evenly spaced, with consistent fonts and correct spelling. "
                            "Smudged, blurry or misaligned print is a warning sign."),
        ("🎨 Colours and artwork", "Compare with a pack you know is genuine. Look for faded colours, a different "
                                  "shade, or a logo that sits in a slightly different place."),
        ("🔒 Seals and tamper marks", "A factory seal should be clean and intact. Re-glued flaps, torn tape or "
                                     "stickers over the original print need a closer look."),
        ("🌈 Holograms and security marks", "If the brand uses one, it should look detailed and change as you tilt "
                                           "it. A flat, dull or easily peeled sticker is suspicious."),
        ("🔢 Batch and dates", "A batch number, manufacture date and expiry date should be clearly printed, not "
                              "stuck on, and match between carton and strip."),
        ("💊 Tablets and capsules", "They should be uniform in colour, size and shape, with a clean imprint. "
                                   "Crumbling, spots or an unusual smell are red flags."),
        ("📦 Strips and blisters", "Foil printing should be even and the pockets uniformly shaped. Loose, "
                                  "re-sealed or mismatched strips are a concern."),
        ("🛒 Where and how you bought it", "Use licensed pharmacies and keep the bill. A price far below normal, "
                                           "or sellers who do not ask for a prescription, are common warning signs."),
    ]
    g1, g2 = st.columns(2, gap="large")
    for n, (t, d) in enumerate(tips):
        with (g1 if n % 2 == 0 else g2):
            with st.expander(t):
                st.write(d)
    st.info("If something feels wrong, do not use the medicine. Ask a pharmacist or contact the "
            "manufacturer using the customer care number on the pack.", icon="💬")

# ---------- about ----------
with tab_about:
    st.markdown("### How PharmaLens works")
    steps = [
        ("Add photos", "Photograph the front and back of the pack. A close-up of the seal or hologram is optional."),
        ("We look closely", "The packaging design is compared with reference packs, and the printed text, batch "
                            "number and dates are read."),
        ("Answer a few questions", "What you can see in person, such as the seal and the tablets, is combined "
                                   "with what the photos show."),
        ("Get a clear result", "You see a suspicion level, what was checked, and what to do next."),
    ]
    cols = st.columns(4, gap="medium")
    for n, (c, (t, d)) in enumerate(zip(cols, steps), 1):
        c.markdown(f'<div class="card" style="height:100%"><div class="ico s-pass" style="margin-bottom:8px">{n}</div>'
                   f"<b>{t}</b><div class='d' style='color:var(--mute);font-size:.9rem;margin-top:4px'>{d}</div></div>",
                   unsafe_allow_html=True)
    a, b = st.columns(2, gap="large")
    a.markdown('<div class="card"><h4>What it can do</h4>'
               "• Flag packs whose design or print looks off<br>• Read the batch number and dates when they are visible"
               "<br>• Warn you about expired medicine<br>• Tell you what to do next, in plain language</div>",
               unsafe_allow_html=True)
    b.markdown('<div class="card"><h4>What it cannot do</h4>'
               "• Prove that a medicine is genuine<br>• Replace laboratory testing<br>• Judge medicines or brands "
               "it has not seen<br>• Replace advice from a pharmacist or doctor</div>", unsafe_allow_html=True)
    st.markdown('<div class="card"><h4>Privacy</h4>In this preview, your photos are used only for the check '
                "in your current session and are not stored permanently.</div>", unsafe_allow_html=True)
    st.caption("Preview build: results are illustrative until the detection models are connected.")

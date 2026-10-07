import json
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import streamlit as st


# ============================================================
# CHRONOVISION
# ============================================================

ROOT = Path(__file__).resolve().parent

DEMO_VIDEO = ROOT / "demo_input.mp4"
TRACK_SUMMARY = ROOT / "runtime" / "tracks" / "track_summary.json"
EVENT_SUMMARY = ROOT / "runtime" / "events" / "event_summary.json"
ALL_EVENTS = ROOT / "runtime" / "events" / "all_events.jsonl"
EVIDENCE_DIR = ROOT / "runtime" / "evidence"


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="ChronoVision",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# GLOBAL CSS
# ============================================================

st.markdown(
    """
    <style>

    :root {
        --bg: #080c11;
        --panel: #0d131b;
        --panel-2: #101821;
        --border: #202c38;
        --border-soft: #18222c;
        --text: #edf3f8;
        --muted: #81909f;
        --muted-2: #60707f;
        --accent: #72b7ff;
        --accent-2: #5de0c2;
        --warning: #d8b568;
        --danger: #e87878;
    }

    .stApp {
        background:
            radial-gradient(
                900px 500px at 72% -10%,
                rgba(75, 137, 196, 0.07),
                transparent 65%
            ),
            var(--bg);
        color: var(--text);
    }

    [data-testid="stHeader"] {
        background: rgba(8, 12, 17, 0.55);
    }

    [data-testid="stToolbar"] {
        display: none;
    }

    #MainMenu {
        visibility: hidden;
    }

    footer {
        visibility: hidden;
    }

    .block-container {
        max-width: 1480px;
        padding-top: 1.4rem;
        padding-bottom: 2.5rem;
    }

    /* --------------------------------------------------------
       SIDEBAR
    -------------------------------------------------------- */

    section[data-testid="stSidebar"] {
        background:
            linear-gradient(
                180deg,
                #0a1017 0%,
                #091017 100%
            );
        border-right: 1px solid #18222d;
    }

    section[data-testid="stSidebar"] > div {
        padding-top: 1.2rem;
    }

    .brand-row {
        display: flex;
        align-items: center;
        gap: 0.65rem;
    }

    .brand-mark {
        width: 30px;
        height: 30px;
        border: 1px solid #355169;
        border-radius: 9px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #72b7ff;
        font-size: 15px;
        background: #0d1721;
    }

    .brand-name {
        font-size: 1.2rem;
        font-weight: 760;
        letter-spacing: -0.03em;
        color: #edf4fb;
    }

    .brand-sub {
        color: #738292;
        font-size: 0.74rem;
        margin-top: 0.22rem;
    }

    .engine-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.42rem;
        margin-top: 1rem;
        padding: 0.38rem 0.58rem;
        border: 1px solid rgba(93,224,194,.20);
        border-radius: 999px;
        color: #7ce7cf;
        background: rgba(93,224,194,.06);
        font-size: 0.72rem;
        font-weight: 680;
    }

    .engine-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #63d9bb;
        box-shadow: 0 0 10px rgba(99,217,187,.55);
    }

    div[role="radiogroup"] {
        gap: 0.3rem !important;
    }

    div[role="radiogroup"] label {
        background: transparent !important;
        border: 1px solid transparent !important;
        border-radius: 10px !important;
        padding: 0.50rem 0.65rem !important;
        min-height: auto !important;
    }

    div[role="radiogroup"] label:hover {
        background: #0d151e !important;
        border-color: #1b2834 !important;
    }

    div[role="radiogroup"] label p {
        color: #9cabb9 !important;
        font-size: 0.84rem !important;
        font-weight: 540 !important;
    }

    div[role="radiogroup"] label:has(input:checked) {
        background: #101b26 !important;
        border-color: #263a4d !important;
    }

    div[role="radiogroup"] label:has(input:checked) p {
        color: #e4eef7 !important;
        font-weight: 670 !important;
    }

    /* --------------------------------------------------------
       PAGE
    -------------------------------------------------------- */

    .page-kicker {
        color: #6f8da6;
        font-size: 0.70rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.13em;
        margin-bottom: 0.35rem;
    }

    .page-title {
        color: #f1f6fa;
        font-size: 2rem;
        line-height: 1.1;
        font-weight: 760;
        letter-spacing: -0.045em;
        margin: 0;
    }

    .page-subtitle {
        color: #7f8e9d;
        font-size: 0.86rem;
        margin-top: 0.45rem;
    }

    .section-title {
        color: #e9eff5;
        font-size: 0.94rem;
        font-weight: 680;
        margin-bottom: 0.55rem;
    }

    /* --------------------------------------------------------
       PANELS
    -------------------------------------------------------- */

    .panel {
        background:
            linear-gradient(
                145deg,
                rgba(17, 25, 34, 0.98),
                rgba(11, 17, 24, 0.98)
            );
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1rem;
        box-shadow:
            0 14px 36px rgba(0,0,0,.12),
            inset 0 1px 0 rgba(255,255,255,.015);
    }

    .panel-tight {
        padding: 0.78rem;
    }

    /* --------------------------------------------------------
       STATUS
    -------------------------------------------------------- */

    .top-status {
        display: flex;
        justify-content: flex-end;
        padding-top: 0.2rem;
    }

    .status-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.40rem;
        padding: 0.40rem 0.62rem;
        border-radius: 999px;
        border: 1px solid #253747;
        background: #0d151e;
        color: #a6b6c5;
        font-size: 0.72rem;
        font-weight: 650;
    }

    .status-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #61d8bb;
        box-shadow: 0 0 10px rgba(99,217,187,.55);
    }

    /* --------------------------------------------------------
       KPI
    -------------------------------------------------------- */

    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0.65rem;
    }

    .kpi {
        border: 1px solid var(--border);
        background: #0d141c;
        border-radius: 13px;
        padding: 0.72rem 0.8rem;
    }

    .kpi-label {
        color: #687887;
        text-transform: uppercase;
        letter-spacing: 0.09em;
        font-size: 0.62rem;
        font-weight: 700;
    }

    .kpi-value {
        color: #eaf1f7;
        font-size: 1.24rem;
        font-weight: 720;
        margin-top: 0.25rem;
    }

    /* --------------------------------------------------------
       ANSWER
    -------------------------------------------------------- */

    .answer-panel {
        border: 1px solid #294158;
        background:
            linear-gradient(
                150deg,
                rgba(18, 32, 45, 0.94),
                rgba(12, 20, 28, 0.98)
            );
        border-radius: 16px;
        padding: 1.05rem;
    }

    .answer-kicker {
        color: #6d94b7;
        text-transform: uppercase;
        letter-spacing: 0.11em;
        font-weight: 700;
        font-size: 0.64rem;
    }

    .answer-main {
        color: #eef5fb;
        font-size: 1.18rem;
        line-height: 1.45;
        font-weight: 650;
        margin-top: 0.35rem;
    }

    .answer-meta-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-top: 0.8rem;
    }

    .answer-meta {
        padding: 0.37rem 0.55rem;
        border-radius: 8px;
        border: 1px solid #2a4257;
        background: #0d1823;
        color: #91b9d8;
        font-size: 0.70rem;
        font-weight: 650;
    }

    /* --------------------------------------------------------
       EVENT ROWS
    -------------------------------------------------------- */

    .event-row {
        display: flex;
        align-items: center;
        gap: 0.8rem;
        padding: 0.72rem 0.78rem;
        border-top: 1px solid #17222d;
    }

    .event-row:first-child {
        border-top: none;
    }

    .event-time {
        width: 64px;
        color: #7eb7e6;
        font-size: 0.73rem;
        font-weight: 690;
        flex: 0 0 auto;
    }

    .event-marker {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #72b7ff;
        box-shadow: 0 0 10px rgba(114,183,255,.24);
        flex: 0 0 auto;
    }

    .event-content {
        min-width: 0;
        flex: 1;
    }

    .event-name {
        color: #e5edf4;
        font-size: 0.80rem;
        font-weight: 640;
    }

    .event-detail {
        color: #6f7f8d;
        font-size: 0.69rem;
        margin-top: 0.15rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    .event-badge {
        color: #7e8f9e;
        border: 1px solid #25323e;
        background: #0e151d;
        border-radius: 7px;
        padding: 0.25rem 0.4rem;
        font-size: 0.62rem;
        flex: 0 0 auto;
    }

    /* --------------------------------------------------------
       TIMELINE
    -------------------------------------------------------- */

    .timeline-shell {
        position: relative;
        padding: 1.15rem 0.4rem 0.35rem;
    }

    .timeline-line {
        position: absolute;
        left: 1%;
        right: 1%;
        top: 29px;
        height: 1px;
        background: #263541;
    }

    .timeline-events {
        position: relative;
        display: flex;
        justify-content: space-between;
        gap: 0.4rem;
    }

    .timeline-item {
        min-width: 0;
        flex: 1;
        text-align: center;
    }

    .timeline-dot {
        width: 9px;
        height: 9px;
        border-radius: 50%;
        margin: 0 auto;
        background: #72b7ff;
        box-shadow: 0 0 0 4px rgba(114,183,255,.07);
    }

    .timeline-time {
        color: #7d96ab;
        font-size: 0.63rem;
        margin-top: 0.45rem;
    }

    .timeline-label {
        color: #d2dce4;
        font-size: 0.62rem;
        margin-top: 0.18rem;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }

    /* --------------------------------------------------------
       PIPELINE
    -------------------------------------------------------- */

    .pipeline-step {
        display: flex;
        align-items: center;
        gap: 0.55rem;
        padding: 0.47rem 0;
        border-bottom: 1px solid #17212b;
    }

    .pipeline-step:last-child {
        border-bottom: none;
    }

    .pipeline-icon {
        width: 24px;
        height: 24px;
        border-radius: 7px;
        background: #0e1821;
        border: 1px solid #253746;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #78b7e8;
        font-size: 0.67rem;
        flex: 0 0 auto;
    }

    .pipeline-text {
        color: #a9b7c3;
        font-size: 0.72rem;
        flex: 1;
    }

    .pipeline-state {
        color: #6ad6bc;
        font-size: 0.63rem;
        font-weight: 700;
    }

    /* --------------------------------------------------------
       BUTTONS
    -------------------------------------------------------- */

    .stButton > button {
        border-radius: 9px !important;
        border: 1px solid #273541 !important;
        background: #0f171f !important;
        color: #c4d0db !important;
        font-weight: 620 !important;
        min-height: 2.55rem !important;
        white-space: normal !important;
        line-height: 1.2 !important;
        text-align: left !important;
        padding: 0.55rem 0.7rem !important;
    }

    .stButton > button:hover {
        border-color: #41617a !important;
        color: #e7f0f7 !important;
        background: #121e29 !important;
    }

    .stButton > button[kind="primary"] {
        background: #5f9fd3 !important;
        border-color: #70addf !important;
        color: #071018 !important;
        font-weight: 760 !important;
        text-align: center !important;
    }

    .stButton > button[kind="primary"]:hover {
        background: #74afe0 !important;
    }

    /* --------------------------------------------------------
       INPUT
    -------------------------------------------------------- */

    div[data-testid="stTextArea"] textarea {
        background: #0a1118 !important;
        border: 1px solid #243341 !important;
        color: #e9f0f5 !important;
        border-radius: 11px !important;
        font-size: 0.84rem !important;
    }

    div[data-testid="stTextArea"] textarea:focus {
        border-color: #47708e !important;
        box-shadow: 0 0 0 1px #47708e !important;
    }

    /* --------------------------------------------------------
       VIDEO
    -------------------------------------------------------- */

    .stVideo {
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid #24313c;
    }

    /* --------------------------------------------------------
       MISC
    -------------------------------------------------------- */

    .muted {
        color: #71808f;
        font-size: 0.72rem;
    }

    .mono {
        font-family:
            ui-monospace,
            SFMono-Regular,
            Menlo,
            Consolas,
            monospace;
    }

    hr {
        border-color: #18232d !important;
    }

    @media (max-width: 1000px) {
        .kpi-grid {
            grid-template-columns: repeat(2, 1fr);
        }

        .page-title {
            font-size: 1.65rem;
        }
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HELPERS
# ============================================================

def load_json(path, default=None):
    if not path.exists():
        return default

    try:
        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return default


def load_events(path):
    if not path.exists():
        return []

    events = []

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        for line in f:
            line = line.strip()

            if line:
                try:
                    events.append(
                        json.loads(line)
                    )
                except json.JSONDecodeError:
                    pass

    return sorted(
        events,
        key=lambda x: x.get(
            "time_sec",
            0.0
        ),
    )


def run_command(command):
    result = subprocess.run(
        command,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    return (
        result.returncode,
        result.stdout,
    )


def extract_json(output):
    start = output.find("{")
    end = output.rfind("}")

    if start == -1 or end == -1:
        return None

    try:
        return json.loads(
            output[
                start:end + 1
            ]
        )
    except Exception:
        return None


def run_query(query):
    """
    Send every natural-language question through the
    ChronoVision PS02 Question Router.

    The router handles:
    - temporal ordering
    - before / after questions
    - counting
    - duration
    - restricted-area questions
    - machine-stop questions
    - safety-alarm questions
    - untouched-object questions
    - timestamped answers
    """

    command = [
        sys.executable,
        "src/question_router.py",
        "--question",
        query.strip(),
    ]

    code, output = run_command(command)

    parsed = extract_json(output)

    if parsed is None:
        return {
            "status": "error",
            "answer": (
                "The ChronoVision question router "
                "did not return structured output."
            ),
            "raw_output": output,
            "return_code": code,
        }

    router_status = parsed.get("status")

    if router_status == "answer":
        parsed["status"] = "success"

    elif router_status in {
        "no_match",
        "insufficient_evidence",
        "no_machine_stop_detected",
    }:
        parsed["status"] = "no_match"

    if parsed.get("timestamp") is not None:
        parsed["timestamp_sec"] = parsed["timestamp"]

    if parsed.get("reference_timestamp") is not None:
        parsed["reference_timestamp_sec"] = (
            parsed["reference_timestamp"]
        )

    if "confidence" not in parsed:
        parsed["confidence"] = None

    return parsed



def event_label(event):
    labels = {
        "movement_started":
            "Movement started",
        "movement_stopped":
            "Movement stopped",
        "stationary_interval":
            "Stationary interval",
        "zone_entered":
            "Zone entered",
        "zone_exited":
            "Zone exited",
        "zone_present_at_start":
            "Zone occupied at start",
        "interaction_candidate":
            "Interaction candidate",
        "interaction_ended":
            "Interaction ended",
        "untouched_candidate":
            "Untouched candidate",
        "track_started":
            "Track detected",
        "track_last_seen":
            "Track last seen",
    }

    return labels.get(
        event.get("event_type"),
        event.get(
            "event_type",
            "event"
        ).replace(
            "_",
            " "
        ).title(),
    )


def event_detail(event):
    if event.get("track_id") is not None:
        actor = (
            f"Track {event['track_id']}"
        )
    elif event.get("track_a") is not None:
        actor = (
            f"Tracks {event['track_a']} "
            f"↔ {event['track_b']}"
        )
    else:
        actor = ""

    detail = event.get(
        "details",
        "",
    )

    if actor and detail:
        return (
            f"{actor} · {detail}"
        )

    return (
        actor
        or detail
        or "Event detected"
    )


def format_seconds(seconds):
    seconds = max(
        0.0,
        float(seconds)
    )

    mins = int(
        seconds // 60
    )
    secs = seconds % 60

    return f"{mins:02d}:{secs:05.2f}"


def find_timestamp(result):
    if result.get(
        "timestamp_sec"
    ) is not None:
        return float(
            result["timestamp_sec"]
        )

    for answer in result.get(
        "answers",
        []
    ):

        related = answer.get(
            "related_events",
            []
        )

        if related:
            return float(
                related[0].get(
                    "timestamp_sec",
                    0.0
                )
            )

        target = answer.get(
            "target_event"
        )

        if target:
            return float(
                target.get(
                    "timestamp_sec",
                    0.0
                )
            )

    for match in result.get(
        "matches",
        []
    ):

        target = match.get(
            "target_event",
            {}
        )

        if target:
            return float(
                target.get(
                    "timestamp_sec",
                    0.0
                )
            )

    events = result.get(
        "events",
        []
    )

    if events:
        return float(
            events[0].get(
                "timestamp_sec",
                0.0
            )
        )

    return None


def result_headline(result):
    if result.get(
        "answer"
    ):
        return result["answer"]

    matches = result.get(
        "matches",
        []
    )

    if matches:

        target = matches[0].get(
            "target_event",
            {}
        )

        return target.get(
            "description",
            "Matching event found."
        )

    answers = result.get(
        "answers",
        []
    )

    if answers:

        related = answers[0].get(
            "related_events",
            []
        )

        if related:
            return related[0].get(
                "description",
                "Relevant event found."
            )

    return "Relevant event found."


def confidence_from_result(result):
    matches = result.get(
        "matches",
        []
    )

    if matches:

        target = matches[0].get(
            "target_event",
            {}
        )

        return target.get(
            "confidence"
        )

    answers = result.get(
        "answers",
        []
    )

    if answers:

        related = answers[0].get(
            "related_events",
            []
        )

        if related:
            return related[0].get(
                "confidence"
            )

    evidence = result.get(
        "evidence",
        {}
    )

    return evidence.get(
        "confidence"
    )


def latest_evidence_frame():
    if not EVIDENCE_DIR.exists():
        return None

    frames = sorted(
        EVIDENCE_DIR.glob(
            "frame_*.jpg"
        )
    )

    return (
        frames[-1]
        if frames
        else None
    )


def latest_evidence_clip():
    if not EVIDENCE_DIR.exists():
        return None

    clips = sorted(
        EVIDENCE_DIR.glob(
            "*.mp4"
        )
    )

    return (
        clips[-1]
        if clips
        else None
    )


def render_html(content):
    st.html(
        dedent(
            content
        )
    )


# ============================================================
# LOAD DATA
# ============================================================

tracks = load_json(
    TRACK_SUMMARY,
    {},
)

event_summary = load_json(
    EVENT_SUMMARY,
    {},
)

events = load_events(
    ALL_EVENTS
)


# ============================================================
# SESSION STATE
# ============================================================

if "last_result" not in st.session_state:
    st.session_state.last_result = None


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    render_html(
        """
        <div class="brand-row">
            <div class="brand-mark">◈</div>
            <div class="brand-name">ChronoVision</div>
        </div>

        <div class="brand-sub">
            Video intelligence · temporal reasoning
        </div>

        <div class="engine-pill">
            <span class="engine-dot"></span>
            LOCAL ENGINE READY
        </div>
        """
    )

    st.markdown(
        "<div style='height:1.0rem'></div>",
        unsafe_allow_html=True
    )

    page = st.radio(
        "Workspace",
        [
            "Analysis",
            "Timeline",
            "Evidence",
            "System",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    render_html(
        """
        <div class="section-title">
            Engine stack
        </div>

        <div class="pipeline-step">
            <div class="pipeline-icon">01</div>
            <div class="pipeline-text">Video ingest</div>
            <div class="pipeline-state">READY</div>
        </div>

        <div class="pipeline-step">
            <div class="pipeline-icon">02</div>
            <div class="pipeline-text">Detection</div>
            <div class="pipeline-state">READY</div>
        </div>

        <div class="pipeline-step">
            <div class="pipeline-icon">03</div>
            <div class="pipeline-text">BoT-SORT tracking</div>
            <div class="pipeline-state">READY</div>
        </div>

        <div class="pipeline-step">
            <div class="pipeline-icon">04</div>
            <div class="pipeline-text">Temporal engine</div>
            <div class="pipeline-state">READY</div>
        </div>

        <div class="pipeline-step">
            <div class="pipeline-icon">05</div>
            <div class="pipeline-text">VLM verifier</div>
            <div class="pipeline-state">STANDBY</div>
        </div>
        """
    )

    st.divider()

    duration = tracks.get(
        "duration_sec",
        0.0,
    )

    device = (
        "CUDA"
        if tracks.get(
            "cuda_available",
            False
        )
        else "CPU"
    )

    render_html(
        f"""
        <div class="muted">SESSION</div>

        <div style="height:.35rem"></div>

        <div class="muted">SOURCE</div>

        <div style="
            color:#c9d4de;
            font-size:.73rem;
            margin-top:.2rem;
            margin-bottom:.55rem;
        ">
            {DEMO_VIDEO.name}
        </div>

        <div class="muted">DURATION</div>

        <div class="mono"
             style="
                 color:#c9d4de;
                 font-size:.73rem;
                 margin-top:.2rem;
                 margin-bottom:.55rem;
             ">
            {format_seconds(duration)}
        </div>

        <div class="muted">COMPUTE</div>

        <div style="
            color:#73d9bd;
            font-size:.73rem;
            margin-top:.2rem;
        ">
            {device}
        </div>
        """
    )


# ============================================================
# PAGE HEADER
# ============================================================

header_left, header_right = st.columns(
    [4.5, 1.5]
)

with header_left:

    render_html(
        """
        <div class="page-kicker">
            HNX26 · PS02
        </div>

        <div class="page-title">
            See the sequence. Verify the moment.
        </div>

        <div class="page-subtitle">
            ChronoVision turns video into a searchable temporal evidence timeline.
        </div>
        """
    )

with header_right:

    render_html(
        """
        <div class="top-status">
            <div class="status-chip">
                <span class="status-dot"></span>
                ANALYSIS READY
            </div>
        </div>
        """
    )


st.markdown(
    "<div style='height:.8rem'></div>",
    unsafe_allow_html=True
)


# ============================================================
# ANALYSIS
# ============================================================

if page == "Analysis":

    left, right = st.columns(
        [1.55, 1],
        gap="large"
    )

    # ---------------- LEFT ----------------

    with left:

        render_html(
            """
            <div class="section-title">
                Evidence viewer
            </div>

            <div class="panel">
            """
        )

        if DEMO_VIDEO.exists():
            st.video(
                str(DEMO_VIDEO)
            )
        else:
            st.error(
                "demo_input.mp4 was not found."
            )

        render_html(
            f"""
                <div style="
                    display:flex;
                    justify-content:space-between;
                    gap:1rem;
                    margin-top:.62rem;
                    padding-top:.60rem;
                    border-top:1px solid #17232d;
                ">
                    <div class="muted">
                        SOURCE ·
                        <span style="color:#b9c6d2">
                            {DEMO_VIDEO.name}
                        </span>
                    </div>

                    <div class="muted">
                        {tracks.get('width', 0)}
                        ×
                        {tracks.get('height', 0)}
                        ·
                        {tracks.get('fps', 0):.0f} FPS
                    </div>
                </div>
            </div>
            """
        )

        st.markdown(
            "<div style='height:.65rem'></div>",
            unsafe_allow_html=True
        )

        # KPI strip
        render_html(
            """
            <div class="kpi-grid">
            """
            + "".join(
                [
                    f"""
                    <div class="kpi">
                        <div class="kpi-label">
                            {label}
                        </div>

                        <div class="kpi-value">
                            {value}
                        </div>
                    </div>
                    """
                    for label, value in [
                        (
                            "Tracked IDs",
                            tracks.get(
                                "unique_track_count",
                                0
                            ),
                        ),
                        (
                            "Events",
                            event_summary.get(
                                "event_count",
                                len(events)
                            ),
                        ),
                        (
                            "Duration",
                            f"{tracks.get('duration_sec', 0):.1f}s",
                        ),
                        (
                            "Compute",
                            device,
                        ),
                    ]
                ]
            )
            + """
            </div>
            """
        )

    # ---------------- RIGHT ----------------

    with right:

        render_html(
            """
            <div class="section-title">
                Ask ChronoVision
            </div>

            <div class="panel">
            """
        )

        query = st.text_area(
            "Temporal question",
            placeholder=(
                "Ask what happened, when it happened, "
                "or what came immediately before or after..."
            ),
            height=115,
            label_visibility="collapsed",
            key="query_box",
        )

        render_html(
            """
                <div class="query-hint">
                    Use natural language. The temporal engine resolves
                    order, counting, duration and event relationships.
                </div>
            """
        )

        st.markdown(
            "<div style='height:.6rem'></div>",
            unsafe_allow_html=True
        )

        analyze_col, clear_col = st.columns(
            [1.4, 1]
        )

        with analyze_col:
            analyze = st.button(
                "Analyze timeline",
                type="primary",
                use_container_width=True,
            )

        with clear_col:
            clear = st.button(
                "Reset",
                use_container_width=True,
            )

        if clear:
            st.session_state.last_result = None
            st.rerun()

        render_html(
            """
                <div style="height:.7rem"></div>

                <div class="muted"
                     style="
                         text-transform:uppercase;
                         letter-spacing:.09em;
                         font-weight:700;
                         font-size:.63rem;
                     ">
                    Suggested investigations
                </div>
            """
        )

        quick_queries = [
            "How many times did movement stop?",
            "What happened immediately before movement stopped?",
            "What happened immediately after movement started?",
            "How long was the person stationary?",
            "Which person entered the restricted area after the delivery truck arrived?",
            "How many times did the machine stop unexpectedly?",
            "What happened right before the safety alarm?",
            "Find every object that sat there untouched for more than 2 minutes.",
        ]

        selected_quick = None

        for i in range(
            0,
            len(quick_queries),
            2
        ):

            c1, c2 = st.columns(2)

            with c1:

                if st.button(
                    quick_queries[i],
                    key=f"quick_{i}",
                    use_container_width=True,
                ):
                    selected_quick = quick_queries[i]

            with c2:

                if (
                    i + 1
                    < len(quick_queries)
                ):

                    if st.button(
                        quick_queries[i + 1],
                        key=f"quick_{i+1}",
                        use_container_width=True,
                    ):
                        selected_quick = (
                            quick_queries[i + 1]
                        )

        render_html(
            """
            </div>
            """
        )

        if selected_quick:
            query = selected_quick
            analyze = True

    # ---------------- RESULT ----------------

    if analyze:

        if not query or not query.strip():

            st.warning(
                "Enter a question first."
            )

        else:

            with st.spinner(
                "Resolving temporal event graph..."
            ):
                result = run_query(
                    query.strip()
                )

            st.session_state.last_result = result

    result = st.session_state.last_result

    if result:

        st.markdown(
            "<div style='height:.75rem'></div>",
            unsafe_allow_html=True
        )

        if result.get("status") == "success":

            headline = result_headline(
                result
            )

            timestamp = find_timestamp(
                result
            )

            confidence = confidence_from_result(
                result
            )

            relation = result.get(
                "relation"
            )

            relation_label = (
                relation.replace(
                    "_",
                    " "
                ).title()
                if relation
                else "Temporal result"
            )

            meta = []

            if timestamp is not None:
                meta.append(
                    f"⏱ {timestamp:.3f}s"
                )

            meta.append(
                relation_label
            )

            if confidence is not None:
                meta.append(
                    f"Confidence · {confidence:.0%}"
                )

            render_html(
                f"""
                <div class="answer-panel">

                    <div class="answer-kicker">
                        VERIFIED TIMELINE RESULT
                    </div>

                    <div class="answer-main">
                        {headline}
                    </div>

                    <div class="answer-meta-row">
                        {
                            "".join(
                                f'<div class="answer-meta">{item}</div>'
                                for item in meta
                            )
                        }
                    </div>

                </div>
                """
            )

            frame = latest_evidence_frame()
            clip = latest_evidence_clip()

            if frame or clip:

                st.markdown(
                    "<div style='height:.55rem'></div>",
                    unsafe_allow_html=True
                )

                ec1, ec2 = st.columns(2)

                with ec1:

                    if frame:
                        render_html(
                            """
                            <div class="section-title">
                                Evidence frame
                            </div>
                            """
                        )

                        st.image(
                            str(frame),
                            use_container_width=True
                        )

                with ec2:

                    if clip:
                        render_html(
                            """
                            <div class="section-title">
                                Evidence clip
                            </div>
                            """
                        )

                        st.video(
                            str(clip)
                        )

            with st.expander(
                "Inspect structured reasoning"
            ):
                st.json(
                    result
                )

        elif result.get(
            "status"
        ) == "no_match":

            render_html(
                f"""
                <div class="answer-panel">

                    <div class="answer-kicker">
                        NO MATCH
                    </div>

                    <div class="answer-main">
                        {
                            result.get(
                                "answer",
                                "No matching event found."
                            )
                        }
                    </div>

                </div>
                """
            )

        else:

            st.error(
                result.get(
                    "answer",
                    "Reasoning engine error."
                )
            )

    # ---------------- TIMELINE PREVIEW ----------------

    st.markdown(
        "<div style='height:1rem'></div>",
        unsafe_allow_html=True
    )

    render_html(
        """
        <div class="section-title">
            Temporal signal
        </div>

        <div class="panel panel-tight">
        """
    )

    visible_events = [
        e
        for e in events
        if e.get("event_type")
        not in {
            "track_started",
            "track_last_seen",
        }
    ]

    preview = visible_events[:7]

    if preview:

        items = []

        for event in preview:

            timestamp = float(
                event.get(
                    "time_sec",
                    0
                )
            )

            items.append(
                f"""
                <div class="timeline-item">

                    <div class="timeline-dot"></div>

                    <div class="timeline-time">
                        {timestamp:.2f}s
                    </div>

                    <div class="timeline-label">
                        {event_label(event)}
                    </div>

                </div>
                """
            )

        render_html(
            """
            <div class="timeline-shell">
                <div class="timeline-line"></div>

                <div class="timeline-events">
            """
            + "".join(items)
            + """
                </div>
            </div>
            """
        )

    else:

        render_html(
            """
            <div class="muted">
                No temporal events available.
            </div>
            """
        )

    render_html(
        """
        </div>
        """
    )


# ============================================================
# TIMELINE PAGE
# ============================================================

elif page == "Timeline":

    render_html(
        """
        <div class="page-kicker">
            EVENT GRAPH
        </div>

        <div class="page-title">
            Temporal timeline
        </div>

        <div class="page-subtitle">
            Every meaningful event is anchored to a timestamp
            and traceable to evidence.
        </div>
        """
    )

    st.markdown(
        "<div style='height:.9rem'></div>",
        unsafe_allow_html=True
    )

    render_html(
        """
        <div class="panel">
        """
    )

    meaningful = [
        e
        for e in events
        if e.get("event_type")
        not in {
            "track_started",
            "track_last_seen",
        }
    ]

    if not meaningful:

        st.info(
            "No meaningful events are available."
        )

    else:

        rows = []

        for event in meaningful:

            timestamp = float(
                event.get(
                    "time_sec",
                    0
                )
            )

            rows.append(
                f"""
                <div class="event-row">

                    <div class="event-time">
                        {timestamp:.3f}s
                    </div>

                    <div class="event-marker"></div>

                    <div class="event-content">

                        <div class="event-name">
                            {event_label(event)}
                        </div>

                        <div class="event-detail">
                            {event_detail(event)}
                        </div>

                    </div>

                    <div class="event-badge">
                        {event.get('class_name', 'event')}
                    </div>

                </div>
                """
            )

        render_html(
            "".join(rows)
        )

    render_html(
        """
        </div>
        """
    )


# ============================================================
# EVIDENCE PAGE
# ============================================================

elif page == "Evidence":

    render_html(
        """
        <div class="page-kicker">
            PROOF LAYER
        </div>

        <div class="page-title">
            Evidence center
        </div>

        <div class="page-subtitle">
            Visual proof attached to model decisions.
        </div>
        """
    )

    st.markdown(
        "<div style='height:.9rem'></div>",
        unsafe_allow_html=True
    )

    frames = (
        sorted(
            EVIDENCE_DIR.glob(
                "frame_*.jpg"
            )
        )
        if EVIDENCE_DIR.exists()
        else []
    )

    clips = (
        sorted(
            EVIDENCE_DIR.glob(
                "*.mp4"
            )
        )
        if EVIDENCE_DIR.exists()
        else []
    )

    left, right = st.columns(
        [1, 1],
        gap="large",
    )

    with left:

        render_html(
            """
            <div class="section-title">
                Frames
            </div>
            """
        )

        if frames:

            for frame in frames:

                render_html(
                    """
                    <div class="panel">
                    """
                )

                st.image(
                    str(frame),
                    caption=frame.name,
                    use_container_width=True,
                )

                render_html(
                    """
                    </div>
                    """
                )

        else:

            st.info(
                "No evidence frames generated yet."
            )

    with right:

        render_html(
            """
            <div class="section-title">
                Clips
            </div>
            """
        )

        if clips:

            for clip in clips:

                render_html(
                    """
                    <div class="panel">
                    """
                )

                st.video(
                    str(clip)
                )

                render_html(
                    f"""
                    <div class="muted"
                         style="margin-top:.45rem">
                        {clip.name}
                    </div>

                    </div>
                    """
                )

        else:

            st.info(
                "No evidence clips generated yet."
            )


# ============================================================
# SYSTEM PAGE
# ============================================================

else:

    render_html(
        """
        <div class="page-kicker">
            RUNTIME
        </div>

        <div class="page-title">
            System status
        </div>

        <div class="page-subtitle">
            ChronoVision runtime, model and processing state.
        </div>
        """
    )

    st.markdown(
        "<div style='height:.9rem'></div>",
        unsafe_allow_html=True
    )

    left, right = st.columns(
        [1.15, 1],
        gap="large",
    )

    with left:

        render_html(
            """
            <div class="panel">

                <div class="section-title">
                    Runtime
                </div>
            """
        )

        rows = [
            (
                "Compute device",
                device,
            ),
            (
                "CUDA available",
                (
                    "Yes"
                    if tracks.get(
                        "cuda_available",
                        False
                    )
                    else "No"
                ),
            ),
            (
                "Detector",
                tracks.get(
                    "model",
                    "Unknown"
                ),
            ),
            (
                "Tracker",
                tracks.get(
                    "tracker",
                    "Unknown"
                ),
            ),
            (
                "FPS",
                f"{tracks.get('fps', 0):.2f}",
            ),
            (
                "Resolution",
                (
                    f"{tracks.get('width', 0)} × "
                    f"{tracks.get('height', 0)}"
                ),
            ),
        ]

        row_html = []

        for label, value in rows:

            row_html.append(
                f"""
                <div style="
                    display:flex;
                    justify-content:space-between;
                    gap:1rem;
                    padding:.62rem 0;
                    border-bottom:1px solid #17212b;
                ">

                    <div class="muted">
                        {label}
                    </div>

                    <div style="
                        color:#ccd7e0;
                        font-size:.73rem;
                        font-weight:650;
                    ">
                        {value}
                    </div>

                </div>
                """
            )

        render_html(
            "".join(row_html)
            + "</div>"
        )

    with right:

        render_html(
            """
            <div class="panel">

                <div class="section-title">
                    Architecture
                </div>
            """
        )

        architecture = [
            ("01", "Video normalization", "LIVE"),
            ("02", "YOLO object detection", "LIVE"),
            ("03", "BoT-SORT identity tracking", "LIVE"),
            ("04", "Event extraction", "LIVE"),
            ("05", "Temporal query engine", "LIVE"),
            ("06", "Evidence generation", "LIVE"),
            ("07", "Gemini semantic verification", "OPTIONAL"),
        ]

        items = []

        for number, name, state in architecture:

            items.append(
                f"""
                <div class="pipeline-step">

                    <div class="pipeline-icon">
                        {number}
                    </div>

                    <div class="pipeline-text">
                        {name}
                    </div>

                    <div class="pipeline-state">
                        {state}
                    </div>

                </div>
                """
            )

        render_html(
            "".join(items)
            + "</div>"
        )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    "<div style='height:1.25rem'></div>",
    unsafe_allow_html=True
)

render_html(
    """
    <div style="
        border-top:1px solid #17212b;
        padding-top:.75rem;
        display:flex;
        justify-content:space-between;
        color:#556474;
        font-size:.64rem;
    ">
        <div>
            CHRONOVISION · VIDEO INTELLIGENCE
        </div>

        <div>
            HNX26 · PS02 · LOCAL-FIRST
        </div>
    </div>
    """
) 
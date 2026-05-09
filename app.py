import os, time, sqlite3, cv2, pygame, numpy as np, streamlit as st
import pandas as pd
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Import your fixed modules
from utils import get_head_pose
from database import DB_NAME, init_db, log_event, get_event_frequency, reset_yawn_history

# --- SYSTEM CONFIG ---
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
st.set_page_config(page_title="GuardianDrive OS", layout="wide", initial_sidebar_state="expanded")

THEMES = {
    "Dark": {"bg": "#000000", "sidebar": "#050505", "accent": "#00D1FF", "card": "rgba(255,255,255,0.02)", "border": "#333333"},
    "Light": {"bg": "#FFFFFF", "sidebar": "#F8FAFC", "accent": "#0369A1", "card": "#FFFFFF", "border": "#E5E7EB"},
    "Blue": {"bg": "#071A2F", "sidebar": "#04101F", "accent": "#38BDF8", "card": "rgba(255,255,255,0.04)", "border": "#164E63"},
    "Green": {"bg": "#061A12", "sidebar": "#03100B", "accent": "#22C55E", "card": "rgba(255,255,255,0.04)", "border": "#166534"},
}


def readable_text_color(hex_color):
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return "#111827" if ((r * 299 + g * 587 + b * 114) / 1000) > 150 else "#FFFFFF"


def apply_theme(theme):
    text_color = readable_text_color(theme["bg"])
    muted_color = "#4B5563" if text_color == "#111827" else "#555555"
    heading_color = "#374151" if text_color == "#111827" else "#222222"
    button_hover_text = readable_text_color(theme["accent"])

    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=JetBrains+Mono:wght@700&display=swap');

        .stApp {{ background-color: {theme["bg"]}; color: {text_color}; font-family: 'Orbitron', sans-serif; }}
        .stMarkdown, .stText, label, p, h1, h2, h3, h4, h5, h6 {{ color: {text_color}; }}

        .status-card {{
            background: {theme["card"]};
            border-radius: 30px;
            border: 4px solid {theme["border"]};
            padding: 24px;
            text-align: center;
            aspect-ratio: 4 / 3;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            justify-content: center;
            transition: all 0.4s ease-in-out;
            margin-bottom: 20px;
        }}

        .alert-text {{
            font-size: 56px !important;
            font-weight: 900;
            letter-spacing: 6px;
            margin: 0;
            text-transform: uppercase;
            overflow-wrap: anywhere;
        }}

        .mega-metric {{ font-family: 'JetBrains Mono'; font-size: 70px; margin: 0; }}
        .label {{ color: {muted_color}; font-size: 14px; text-transform: uppercase; letter-spacing: 4px; margin-bottom: 5px; }}
        .theme-heading {{ text-align: center; color: {heading_color}; letter-spacing: 8px; }}

        section[data-testid="stSidebar"] {{ background-color: {theme["sidebar"]}; border-right: 1px solid {theme["border"]}; }}
        .stButton>button {{
            background-color: {theme["bg"]};
            color: {theme["accent"]};
            border: 1px solid {theme["accent"]};
            border-radius: 5px;
            height: 3.5em;
            font-weight: bold;
            width: 100%;
        }}
        .stButton>button:hover {{
            background-color: {theme["accent"]};
            color: {button_hover_text};
            box-shadow: 0 0 20px {theme["accent"]};
        }}
        .st-key-start_engine button {{
            color: #22C55E;
            border-color: #22C55E;
        }}
        .st-key-start_engine button:hover {{
            background-color: #22C55E;
            color: #000000;
            box-shadow: 0 0 20px #22C55E;
        }}
        .st-key-stop_engine button {{
            color: #EF4444;
            border-color: #EF4444;
        }}
        .st-key-stop_engine button:hover {{
            background-color: #EF4444;
            color: #FFFFFF;
            box-shadow: 0 0 20px #EF4444;
        }}
    </style>
    """, unsafe_allow_html=True)


# --- MATH HELPER ---
def calculate_EAR(face_lms, indices):
    pts = np.array([(face_lms[i].x, face_lms[i].y) for i in indices])
    v1 = np.linalg.norm(pts[1] - pts[5])
    v2 = np.linalg.norm(pts[2] - pts[4])
    h = np.linalg.norm(pts[0] - pts[3])
    return (v1 + v2) / (2.0 * h) if h != 0 else 0.0


def main():
    # Session State Setup
    if 'page' not in st.session_state: st.session_state.page = "Dashboard"
    if 'running' not in st.session_state: st.session_state.running = False
    if 'calibrated' not in st.session_state: st.session_state.calibrated = False

    with st.sidebar:
        theme_name = st.selectbox(
            "Theme",
            ["Dark", "Light", "Blue", "Green", "Custom"],
            index=["Dark", "Light", "Blue", "Green", "Custom"].index(st.session_state.get("theme_name", "Light")),
            key="theme_name",
        )
        if theme_name == "Custom":
            custom_bg = st.color_picker("Background", st.session_state.get("custom_bg", "#000000"), key="custom_bg")
            custom_accent = st.color_picker("Accent", st.session_state.get("custom_accent", "#00D1FF"), key="custom_accent")
            theme = {
                "bg": custom_bg,
                "sidebar": custom_bg,
                "accent": custom_accent,
                "card": "rgba(255,255,255,0.04)" if readable_text_color(custom_bg) == "#FFFFFF" else "#FFFFFF",
                "border": custom_accent,
            }
        else:
            theme = THEMES[theme_name]

    apply_theme(theme)

    # Init Hardware/DB
    init_db()
    pygame.mixer.init()
    alarm = None
    if os.path.exists("assets/sound.wav"):
        alarm = pygame.mixer.Sound("assets/sound.wav")

    # --- SIDEBAR NAVIGATION ---
    with st.sidebar:
        st.markdown("<h1 style='color:#00D1FF; font-size:22px;'>🛡️ GUARDIAN OS</h1>", unsafe_allow_html=True)
        st.markdown("---")
        if st.button("📊 DASHBOARD"): st.session_state.page = "Dashboard"
        if st.button("📑 VIEW LOGS"): st.session_state.page = "Logs"
        st.markdown("<br><br>", unsafe_allow_html=True)
        if st.button("START ENGINE", key="start_engine"): st.session_state.running = True
        if st.button("STOP ENGINE", key="stop_engine"):
            st.session_state.running = False
            if alarm: alarm.stop()
            st.rerun()
        

    # --- LOGS PAGE ---
    if st.session_state.page == "Logs":
        st.header("📑 SYSTEM EVENT LOGS")
        conn = sqlite3.connect(DB_NAME)
        df = pd.read_sql_query("SELECT type, timestamp FROM logs ORDER BY id DESC", conn)
        conn.close()
        if df.empty:
            st.info("No events logged yet. Start the engine and trigger a drowsy, nodding, or yawn event.")
        else:
            st.dataframe(df, use_container_width=True)
        return

    # --- DASHBOARD PAGE ---
    st.markdown("<h3 class='theme-heading'>NEURAL SENSOR ARRAY v3.0</h3>",
                unsafe_allow_html=True)

    col_status, col_video = st.columns([1, 1])

    with col_status:
        status_ui = st.empty()
        st.markdown("<br>", unsafe_allow_html=True)
        m1, m2 = st.columns(2)
        yawn_ui = m1.empty()
        ear_ui = m2.empty()

    with col_video:
        st.markdown("<p class='label'>EYE-TRACKING FIELD</p>", unsafe_allow_html=True)
        video_ui = st.empty()

    # --- AI PROCESSING ENGINE ---
    if st.session_state.running:
        cap = cv2.VideoCapture(0)
        detector = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path='face_landmarker.task'),
            running_mode=vision.RunningMode.VIDEO, num_faces=1))

        # Counters & Throttles
        d_count, n_count, y_count, r_count = 0, 0, 0, 0
        base_p = 0
        alarm_on = False

        while st.session_state.running:
            ret, frame = cap.read()
            if not ret: break
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
            result = detector.detect_for_video(mp_image, int(time.time() * 1000))

            # Default UI State (GREEN)
            state, color, should_alarm = "NORMAL", "#00FF7F", False

            if result.face_landmarks:
                landmarks = result.face_landmarks[0]

                # 1. EAR (Eyes)
                ear = (calculate_EAR(landmarks, [33, 160, 158, 133, 153, 144]) +
                       calculate_EAR(landmarks, [362, 385, 387, 263, 373, 380])) / 2.0

                # 2. Pose (Head)
                lms_tuple = [(lm.x, lm.y) for lm in landmarks]
                curr_p, curr_y = get_head_pose(lms_tuple, w, h)

                if not st.session_state.calibrated:
                    base_p = curr_p
                    st.session_state.calibrated = True

                # --- DROWSY LOGIC (RED) ---
                if ear < 0.21:
                    d_count += 1
                    state, color = "CAUTION", "#FFD700"  # YELLOW
                    if d_count > 25:
                        state, color, should_alarm = "DROWSY", "#FF3131", True
                        if d_count == 26: log_event("DROWSY")
                else:
                    d_count = 0

                # --- NODDING LOGIC (RED) ---
                if abs(curr_p - base_p) > 28:
                    n_count += 1
                    if n_count > 20:
                        state, color, should_alarm = "NODDING", "#FF3131", True
                        if n_count == 21: log_event("NODDING")
                else:
                    n_count = 0

                # --- YAWNING LOGIC ---
                m_h = np.linalg.norm(
                    np.array([landmarks[13].x, landmarks[13].y]) - np.array([landmarks[14].x, landmarks[14].y]))
                m_w = np.linalg.norm(
                    np.array([landmarks[61].x, landmarks[61].y]) - np.array([landmarks[291].x, landmarks[291].y]))
                if (m_h / m_w) > 0.62:
                    y_count += 1
                    if y_count == 22: log_event("YAWN")
                else:
                    y_count = 0

                # --- CRITICAL ESCALATION ---
                recent_y = get_event_frequency("YAWN", 300)
                if recent_y >= 3:
                    state, color = "CRITICAL", "#8B0000"
                    if ear < 0.24: should_alarm = True
                    # Recovery
                    if ear > 0.25 and abs(curr_p - base_p) < 15:
                        r_count += 1
                        if r_count > 60: reset_yawn_history(); r_count = 0

                # --- UI REFRESH ---
                status_ui.markdown(f"""
                    <div class='status-card' style='border-color: {color}; box-shadow: 0 0 60px {color}33;'>
                        <p class='label'>OPERATOR STATUS</p>
                        <p class='alert-text' style='color: {color}; text-shadow: 0 0 30px {color}66;'>{state}</p>
                    </div>
                """, unsafe_allow_html=True)

                yawn_ui.markdown(
                    f"<div style='text-align:center'><p class='label'>YAWN INDEX</p><p class='mega-metric' style='color:{color}'>{recent_y}</p></div>",
                    unsafe_allow_html=True)
                ear_ui.markdown(
                    f"<div style='text-align:center'><p class='label'>EYE RATIO</p><p class='mega-metric' style='color:{color}'>{ear:.2f}</p></div>",
                    unsafe_allow_html=True)

            # Audio Engine
            if should_alarm and alarm:
                if not alarm_on: alarm.play(-1); alarm_on = True
            elif alarm_on:
                alarm.stop(); alarm_on = False

            # Live Feed
            video_ui.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), use_container_width=True)

        cap.release()
        detector.close()


if __name__ == "__main__":
    main()

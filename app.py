import os, time, sqlite3, cv2, pygame, numpy as np, streamlit as st
import pandas as pd
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Import your fixed modules
from utils import get_head_pose
from database import init_db, log_event, get_event_frequency, reset_yawn_history

# --- SYSTEM CONFIG ---
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
st.set_page_config(page_title="GuardianDrive OS", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS (Black & Electric Blue + Dynamic Colors) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;900&family=JetBrains+Mono:wght@700&display=swap');

    .stApp { background-color: #000000; color: #FFFFFF; font-family: 'Orbitron', sans-serif; }

    /* Neon Status Card */
    .status-card {
        background: rgba(255, 255, 255, 0.02);
        border-radius: 30px;
        border: 4px solid #333;
        padding: 60px;
        text-align: center;
        transition: all 0.4s ease-in-out;
        margin-bottom: 20px;
    }

    .alert-text { 
        font-size: 110px !important; 
        font-weight: 900; 
        letter-spacing: 12px; 
        margin: 0; 
        text-transform: uppercase;
    }

    .mega-metric { font-family: 'JetBrains Mono'; font-size: 70px; margin: 0; }
    .label { color: #555; font-size: 14px; text-transform: uppercase; letter-spacing: 4px; margin-bottom: 5px; }

    /* Sidebar styling */
    section[data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #222; }
    .stButton>button { 
        background-color: #000; 
        color: #00D1FF; 
        border: 1px solid #00D1FF; 
        border-radius: 5px; 
        height: 3.5em; 
        font-weight: bold; 
        width: 100%;
    }
    .stButton>button:hover { background-color: #00D1FF; color: black; box-shadow: 0 0 20px #00D1FF; }
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
        if st.button("🚀 START ENGINE", type="primary"): st.session_state.running = True
        if st.button("🛑 STOP ENGINE"):
            st.session_state.running = False
            if alarm: alarm.stop()
            st.rerun()
        if st.button("🎯 CALIBRATE"): st.session_state.calibrated = False

    # --- LOGS PAGE ---
    if st.session_state.page == "Logs":
        st.header("📑 SYSTEM EVENT LOGS")
        conn = sqlite3.connect('guardian_drive.db')
        df = pd.read_sql_query("SELECT type, timestamp FROM logs ORDER BY id DESC", conn)
        conn.close()
        st.dataframe(df, use_container_width=True)
        return

    # --- DASHBOARD PAGE ---
    st.markdown("<h3 style='text-align: center; color:#222; letter-spacing:8px;'>NEURAL SENSOR ARRAY v3.0</h3>",
                unsafe_allow_html=True)

    col_status, col_video = st.columns([1.3, 1])

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
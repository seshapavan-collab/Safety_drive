import os, time, sqlite3, cv2, pygame, numpy as np, streamlit as st
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from utils import get_head_pose
from database import init_db, log_event, get_event_frequency, reset_yawn_history

# --- CONFIG & THEME ---
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
st.set_page_config(page_title="GuardianDrive | OS", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS (Cyber-Grid & Neon Accents) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&family=JetBrains+Mono&display=swap');
    .stApp { background-color: #0A0C10; color: #E6edf3; font-family: 'Inter', sans-serif; }
    section[data-testid="stSidebar"] { background-color: #0D1117; border-right: 1px solid #30363d; }
    .metric-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 20px; }
    .status-alert { padding: 30px; border-radius: 12px; text-align: center; transition: 0.5s; border: 1px solid; }
    .alert-text { font-weight: bold; font-size: 42px; letter-spacing: 2px; margin: 0; }
    .metric-val { color: #f0f6fc; font-size: 32px; font-family: 'JetBrains Mono'; margin: 0; }
    .metric-label { color: #8b949e; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)


# --- REFINED MATH ---
def calculate_EAR(face_lms, indices):
    """Calculates EAR using 'face_lms' to avoid shadowing warnings."""
    pts = np.array([(face_lms[i].x, face_lms[i].y) for i in indices])
    A = np.linalg.norm(pts[1] - pts[5])
    B = np.linalg.norm(pts[2] - pts[4])
    C = np.linalg.norm(pts[0] - pts[3])
    return (A + B) / (2.0 * C) if C != 0 else 0.0


# --- MAIN ENGINE ---
def main():
    # 1. Session State Initialization
    if 'running' not in st.session_state: st.session_state.running = False
    if 'calibrated' not in st.session_state: st.session_state.calibrated = False
    if 'ear_hist' not in st.session_state: st.session_state.ear_hist = []

    # 2. Hardware/DB Initialization
    init_db()
    pygame.mixer.init()
    alarm = None
    if os.path.exists("assets/sound.wav"):
        alarm = pygame.mixer.Sound("assets/sound.wav")

    # 3. SIDEBAR CONTROLS
    with st.sidebar:
        st.markdown("<h2 style='color:#00FFA3;'>🛡️ GUARDIANDRIVE</h2>", unsafe_allow_html=True)
        st.caption("SYSTEM CORE: ACTIVE")
        st.markdown("---")
        start_btn = st.button("🚀 START ENGINE", type="primary", use_container_width=True)
        stop_btn = st.button("🛑 STOP ENGINE", use_container_width=True)
        cal_btn = st.button("🎯 CALIBRATE", use_container_width=True)

        if start_btn: st.session_state.running = True
        if stop_btn:
            st.session_state.running = False
            if alarm: alarm.stop()
            st.rerun()
        if cal_btn: st.session_state.calibrated = False

    # 4. DASHBOARD LAYOUT
    st.title("SYSTEM MONITOR")

    top_left, top_right = st.columns([2, 1])
    with top_left:
        status_placeholder = st.empty()

    with top_right:
        # Mini metrics cards
        m_col1, m_col2 = st.columns(2)
        yawns_display = m_col1.empty()
        events_display = m_col2.empty()

    st.markdown("---")
    feed_col, chart_col = st.columns([2, 1])
    video_placeholder = feed_col.empty()
    chart_placeholder = chart_col.empty()

    # 5. LIVE PROCESSING LOOP
    if st.session_state.running:
        cap = cv2.VideoCapture(0)

        # Init MediaPipe
        detector = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path='face_landmarker.task'),
            running_mode=vision.RunningMode.VIDEO, num_faces=1))

        # Internal Counters
        DROWSY_COUNTER = 0
        YAWN_COUNTER = 0
        RECOVERY_COUNTER = 0
        ALARM_ON = False
        base_p, base_y = 0, 0

        while st.session_state.running:
            ret, frame = cap.read()
            if not ret: break
            frame = cv2.flip(frame, 1)
            h, w, _ = frame.shape

            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)
            result = detector.detect_for_video(mp_image, int(time.time() * 1000))

            # Default UI state
            current_state = "ALERT"
            state_color = "#3fb950"
            state_desc = "DRIVER ATTENTIVE. MONITORING NOMINAL."
            should_alarm = False

            if result.face_landmarks:
                landmarks = result.face_landmarks[0]

                # EAR/MAR
                EAR = (calculate_EAR(landmarks, [33, 160, 158, 133, 153, 144]) +
                       calculate_EAR(landmarks, [362, 385, 387, 263, 373, 380])) / 2.0

                m_h = np.linalg.norm(
                    np.array([landmarks[13].x, landmarks[13].y]) - np.array([landmarks[14].x, landmarks[14].y]))
                m_w = np.linalg.norm(
                    np.array([landmarks[61].x, landmarks[61].y]) - np.array([landmarks[291].x, landmarks[291].y]))
                MAR = m_h / m_w if m_w > 0 else 0

                # Head Pose
                lms_tuple = [(lm.x, lm.y) for lm in landmarks]
                curr_p, curr_y = get_head_pose(lms_tuple, w, h)

                if not st.session_state.calibrated:
                    base_p, base_y = curr_p, curr_y
                    st.session_state.calibrated = True

                # --- LOGIC: DROWSY ---
                if EAR < 0.20:
                    DROWSY_COUNTER += 1
                    if DROWSY_COUNTER > 40:
                        current_state, state_color = "DROWSY", "#f85149"
                        state_desc = "DROWSINESS DETECTED: WAKE UP!"
                        should_alarm = True
                else:
                    DROWSY_COUNTER = 0

                # --- LOGIC: YAWN ---
                if MAR > 0.65 and m_h > 0.06:
                    YAWN_COUNTER += 1
                    if YAWN_COUNTER == 25: log_event("YAWN")
                else:
                    YAWN_COUNTER = 0

                # --- LOGIC: RECOVERY ---
                recent_yawns = get_event_frequency("YAWN", 300)
                if recent_yawns >= 3:
                    current_state, state_color = "CRITICAL", "#f85149"
                    if EAR < 0.23: should_alarm = True

                    if EAR > 0.25 and (abs(curr_p - base_p) < 15):
                        RECOVERY_COUNTER += 1
                        if RECOVERY_COUNTER > 50:
                            reset_yawn_history()
                            RECOVERY_COUNTER = 0
                    else:
                        RECOVERY_COUNTER = 0

                # --- UPDATE UI ---
                st.session_state.ear_hist.append(EAR)
                if len(st.session_state.ear_hist) > 50: st.session_state.ear_hist.pop(0)

                yawns_display.markdown(
                    f"<div class='metric-card'><p class='metric-label'>YAWNS (5M)</p><p class='metric-val'>{recent_yawns}</p></div>",
                    unsafe_allow_html=True)
                events_display.markdown(
                    f"<div class='metric-card'><p class='metric-label'>EAR</p><p class='metric-val'>{EAR:.2f}</p></div>",
                    unsafe_allow_html=True)

            # --- ALARM & FEED ---
            status_placeholder.markdown(f"""
                <div class='status-alert' style='border-color: {state_color}; background: linear-gradient(90deg, {state_color}1A 0%, {state_color}00 100%);'>
                    <p class='metric-label'>CURRENT STATE</p>
                    <p class='alert-text' style='color: {state_color};'>{current_state}</p>
                    <p class='metric-label'>{state_desc}</p>
                </div>
            """, unsafe_allow_html=True)

            if should_alarm and alarm:
                if not ALARM_ON:
                    alarm.play(-1)
                    ALARM_ON = True
            else:
                if ALARM_ON and alarm:
                    alarm.stop()
                    ALARM_ON = False

            video_placeholder.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), use_container_width=True)
            chart_placeholder.line_chart(st.session_state.ear_hist, height=200)

        cap.release()
        detector.close()


if __name__ == "__main__":
    main()
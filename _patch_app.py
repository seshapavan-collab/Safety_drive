"""One-off patch script for app.py — delete after use."""
from pathlib import Path

p = Path(__file__).resolve().parent / "app.py"
t = p.read_text(encoding="utf-8")

old_init = """    init_db()
    pygame.mixer.pre_init(44100, -16, 2, 512);
    pygame.mixer.init()
    alarm, HAS_AUDIO = None, False
    try:
        if os.path.exists("assets/alarm.wav"): alarm = pygame.mixer.Sound("assets/alarm.wav"); HAS_AUDIO = True
    except:
        pass

    try:
        detector = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path='face_landmarker.task'),
            running_mode=vision.RunningMode.VIDEO, num_faces=1))
        MP_OK = True
    except:
        st.error("��️ Place 'face_landmarker.task' in folder"); MP_OK = False"""

new_init = """    init_db()
    pygame.mixer.pre_init(44100, -16, 2, 512)
    pygame.mixer.init()
    alarm, HAS_AUDIO = None, False
    try:
        if os.path.exists("assets/alarm.wav"):
            alarm = pygame.mixer.Sound("assets/alarm.wav")
            HAS_AUDIO = True
    except Exception:
        pass

    detector = None
    try:
        detector = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path='face_landmarker.task'),
            running_mode=vision.RunningMode.VIDEO, num_faces=1))
        MP_OK = True
    except Exception:
       �️ Place 'face_landmarker.task' in folder")
        MP_OK = False"""

if old_init not in t:
    raise SystemExit("init block not found — app.py may have changed")
t = t.replace(old_init, new_init)

repls = [
    ('ear_m = m1.metric("��️ EAR", "0.00");', 'ear_m = m1.metric("��️ EAR", "0.00")'),
    ('pitch_m = m� Pitch", "0°");', 'pitch_m = m2.metric("�� Pitch", "0°")'),
    (
        'st.markdown("### �� Driver Feed"); vid = st.empty(); alert = st.empty()',
        'st.markdown("### �� Driver Feed")\n        vid = st.empty()\n        alert = st.empty()',
    ),
    (
        'st.markdown("### �� Fatigue Trend"); chart = st.empty()',
        'st.markdown("### �� Fatigue Trend")\n        chart = st.empty()',
    ),
    ('status, alert_msg = "��� DROWSY!", "WAKE UP!";', 'status, alert_msg = "��� DROWSY!", "WAKE UP!"'),
    ('status, alert_msg = "��� NODDING!", "WAKE UP!";', 'status, alert_msg = "��� NODDING!", "WAKE UP!"'),
    ('ear_m.metric("��️ EAR", f"{EAR:.2f}");', 'ear_m.metric("��️ EAR", f"{EAR:.2f}")'),
    ('pitch_m.metric("�� Pitch", f"{curr_p:.1f}°");', 'pitch_m.metric("�� Pitch", f"{curr_p:.1f}°")'),
]
for a, b in repls:
    if a not in t:
        raise SystemExit(f"pattern not found: {a[:50]}...")
    t = t.replace(a, b)

p.write_text(t, encoding="utf-8")
print("patched app.py")

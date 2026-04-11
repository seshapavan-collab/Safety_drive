# 🛡️ GuardianDrive | Edge-AI Driver Monitoring System

**GuardianDrive** is an intelligent safety layer designed for the next generation of smart vehicles. It utilizes Computer Vision and Deep Learning to monitor driver alertness, detecting signs of fatigue and distraction in real-time.

---

## 📺 Dashboard Preview
![GuardianDrive Dashboard](https://kommodo.ai/i/mFMKNlxk6Hg5EKarSgpS) 
*Custom Cyber-UI featuring real-time EAR telemetry and triple-state alert logic.*

---

## 🧠 Core Intelligence
The system processes a 478-landmark face mesh at the edge to calculate:
* **Eye Aspect Ratio (EAR):** Detects micro-sleeps and prolonged blinks.
* **Mouth Aspect Ratio (MAR):** Analyzes yawning frequency to predict fatigue onset.
* **Head Pose Estimation:** Extracts Pitch/Yaw angles to detect "nodding off" or distraction.



## 🛠️ Tech Stack
- **Python** (Core Logic)
- **MediaPipe** (Face Mesh & Landmark Detection)
- **Streamlit** (Custom Cyberpunk Dashboard)
- **OpenCV** (Frame Processing)
- **SQLite3** (Incident Telemetry)

## 🚦 Alert States
| State | Condition | Visual Indicator |
| :--- | :--- | :--- |
| **NORMAL** | Driver is alert | **Green Glow** |
| **CAUTION** | Initial signs of fatigue | **Yellow Pulse** |
| **DROWSY** | Sustained eye closure | **Red Neon** |
| **CRITICAL** | Repeated yawning/nodding | **Deep Blood Red** |

## ⚙️ Quick Start

1. **Clone the Repo:**
   ```bash
   git clone [https://github.com/Laksh9126/Guardian-Drive-.git](https://github.com/Laksh9126/Guardian-Drive-.git)
   cd Guardian-Drive-
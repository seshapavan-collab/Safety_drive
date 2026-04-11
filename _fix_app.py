from pathlib import Path
import re

p = Path(__file__).resolve().parent / "app.py"
t = p.read_text(encoding="utf-8")

t2, n = re.subn(
    r"    except:\n        st\.error\((\"[^\"]+\"\)); MP_OK = False",
    r"    except Exception:\n        st.error(\1)\n        MP_OK = False",
    t,
    count=1,
)
if n != 1:
    raise SystemExit(f"except block replace count={n}")
t = t2

t = re.sub(r"(ear_m = m1\.metric\([^)]+\));", r"\1", t, count=1)
t = re.sub(r"(pitch_m = m2\.metric\([^)]+\));", r"\1", t, count=1)

t2, n = re.subn(
    r"(        st\.markdown\(\"### .*? Driver Feed\"\)); vid = st\.empty\(\); alert = st\.empty\(\)",
    r"\1\n        vid = st.empty()\n        alert = st.empty()",
    t,
    count=1,
)
if n != 1:
    raise SystemExit(f"driver feed replace count={n}")
t = t2

t2, n = re.subn(
    r"(        st\.markdown\(\"### .*? Fatigue Trend\"\)); chart = st\.empty\(\)",
    r"\1\n        chart = st.empty()",
    t,
    count=1,
)
if n != 1:
    raise SystemExit(f"fatigue replace count={n}")
t = t2

t = re.sub(r"(\"WAKE UP!\");", r"\1", t)

t = re.sub(r"(ear_m\.metric\([^)]+\));", r"\1", t, count=1)
t = re.sub(r"(pitch_m\.metric\([^)]+\));", r"\1", t, count=1)

p.write_text(t, encoding="utf-8")
print("done")

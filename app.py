import os
import re
import streamlit as st

# Optional OpenAI import (app still runs without it in Demo Mode)
try:
    from openai import OpenAI
except Exception:
    OpenAI = None


# ----------------------------
# Page setup
# ----------------------------
st.set_page_config(page_title="Care Companion Demo", layout="wide")
st.title("Care Companion Demo 🫶")
st.caption("AI-assisted coding demo: 5 differentiated caregiver tools (non-diagnostic).")

# ----------------------------
# Sidebar controls
# ----------------------------
with st.sidebar:
    st.header("Settings")
    output_lang = st.selectbox("Output language", ["English", "Spanish", "Hindi", "Urdu"], index=0)

    st.markdown("---")
    st.subheader("Run mode")
    mode = st.radio(
        "Choose:",
        ["Auto (OpenAI if available, else Demo Mode)", "Force Demo Mode (no API)"],
        index=0
    )

    model = st.selectbox("OpenAI model (if enabled)", ["gpt-4o-mini", "gpt-4.1-mini"], index=0)
    temperature = st.slider("Creativity", 0.0, 1.0, 0.2, 0.1)

    st.markdown("---")
    st.subheader("Safety")
    st.write("- No diagnosis. No dosing changes.")
    st.write("- Uses only what’s in the note/context.")
    st.write("- Use sample notes in class (avoid real PHI).")


# ----------------------------
# Input
# ----------------------------
default_note = """Dad seemed more tired than usual this morning and skipped breakfast.
Blood pressure at 11 AM was 92/58.
He felt dizzy when standing up and needed help walking to the bathroom.
Took his blood pressure medication but missed his afternoon vitamin D.
Drank very little water today and did not go for his usual evening walk.
Mood seemed quiet and withdrawn."""

note = st.text_area("Paste today's caregiver note", value=default_note, height=170)

context = st.text_input(
    "Optional context (age, conditions, meds list) — improves quality",
    value="Older adult; diabetes; usually walks daily; takes metformin + vitamin D; on blood pressure medication."
)

st.markdown("")

# ----------------------------
# Helpers: Demo-mode extraction (smart fallback)
# ----------------------------
def _find_bp(text: str):
    m = re.search(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b", text)
    if not m:
        return None
    sys, dia = int(m.group(1)), int(m.group(2))
    return sys, dia, m.group(0)

def _find_temp(text: str):
    m = re.search(r"\b(\d{2,3}\.?\d?)\s*°?\s*f\b", text.lower())
    if not m:
        return None
    return m.group(0)

def _contains_any(text: str, phrases):
    t = text.lower()
    return [p for p in phrases if p in t]

def demo_risk_radar(note_text: str):
    t = note_text.lower()
    risks = []

    bp = _find_bp(note_text)
    if bp:
        sys, dia, raw = bp
        if sys <= 90 or dia <= 60:
            risks.append(("Low blood pressure reading", f"Evidence: '{raw}'", "monitor_closely"))

    if "dizzy" in t or "dizziness" in t or "lightheaded" in t:
        risks.append(("Dizziness on standing", "Evidence: 'dizzy / standing' mentioned", "monitor_closely"))

    if "short of breath" in t or "difficulty breathing" in t:
        risks.append(("Breathing difficulty", "Evidence: 'short of breath' mentioned", "consider_urgent"))

    if "chest pain" in t or "fainted" in t or "passed out" in t:
        risks.append(("Potential emergency symptom", "Evidence: chest pain/fainting mentioned", "consider_urgent"))

    if "fell" in t or "trip" in t or "walker" in t:
        risks.append(("Fall risk", "Evidence: fall/trip/walker mentioned", "monitor_closely"))

    if "very little water" in t or "drank less" in t or "dehydr" in t:
        risks.append(("Low hydration risk", "Evidence: low water intake mentioned", "monitor"))

    if not risks:
        urgency = "low"
    else:
        urgency = "moderate" if any(r[2] == "monitor_closely" for r in risks) else "low"
        if any(r[2] == "consider_urgent" for r in risks):
            urgency = "high"

    lines = []
    lines.append("## 🚦 Risk Radar (Demo Mode)")
    lines.append(f"**Urgency level:** **{urgency.upper()}**")
    lines.append("")
    if risks:
        lines.append("### Signals detected (non-diagnostic)")
        for title, ev, level in risks:
            tag = {"monitor": "Monitor", "monitor_closely": "Monitor closely", "consider_urgent": "Consider urgent care"}[level]
            lines.append(f"- **{title}** — *{tag}*  \n  {ev}")
    else:
        lines.append("- No clear risk signals detected from the note.")

    lines.append("")
    lines.append("### What to do next (general)")
    if urgency == "high":
        lines.append("- Consider urgent medical care / call clinician, especially if symptoms worsen.")
    else:
        lines.append("- Monitor symptoms and repeat key measurements if available (e.g., BP).")
        lines.append("- Encourage hydration/food if appropriate and safe for the person.")
    return "\n".join(lines)

def demo_action_planner(note_text: str):
    t = note_text.lower()
    actions_now = []
    monitor = []
    confirm = []
    schedule = []

    if "dizzy" in t or "lightheaded" in t:
        actions_now.append("Help them stand slowly; ensure a safe path to prevent falls.")
        monitor.append("Track when dizziness happens (standing, after meds, after meals).")

    bp = _find_bp(note_text)
    if bp:
        actions_now.append("Recheck blood pressure later if you have a monitor.")
        monitor.append("Log BP with time and symptoms nearby.")

    if "missed" in t:
        confirm.append("Confirm which medication(s) were missed and when (write it down).")

    if "very little water" in t or "drank less" in t:
        actions_now.append("Offer fluids in small amounts (if appropriate), and note intake.")
        monitor.append("Urine frequency/color (if comfortable) as a hydration clue.")

    if "skipped breakfast" in t or "ate only" in t:
        actions_now.append("Offer a small, easy-to-eat meal/snack if appropriate.")
        monitor.append("Food intake today (rough estimate).")

    schedule.append("Prepare a short update to share with family/other caregivers.")
    schedule.append("If symptoms persist/worsen, contact clinician for guidance.")

    lines = []
    lines.append("## ✅ Action Planner (Demo Mode)")
    lines.append("### Do now")
    lines += [f"- {a}" for a in (actions_now or ["Ensure comfort and safety; address immediate needs."])]
    lines.append("")
    lines.append("### Monitor")
    lines += [f"- {m}" for m in (monitor or ["Track symptoms + timing through the day."])]
    lines.append("")
    lines.append("### Confirm")
    lines += [f"- {c}" for c in (confirm or ["Confirm meds taken/missed and any measurements taken."])]
    lines.append("")
    lines.append("### Schedule / delegate")
    lines += [f"- {s}" for s in schedule]
    return "\n".join(lines)

def demo_doctor_brief(note_text: str):
    bp = _find_bp(note_text)
    bp_line = f"BP: {bp[2]} (reported)" if bp else "BP: not provided"
    dizzy = "Dizziness: yes (reported)" if "dizzy" in note_text.lower() else "Dizziness: not reported"
    missed = "Missed medication dose: yes (reported)" if "missed" in note_text.lower() else "Missed medication dose: not reported"

    lines = []
    lines.append("## 🩺 Doctor Brief (Demo Mode)")
    lines.append("### Summary (4–6 sentences)")
    lines.append(
        "Caregiver reports increased fatigue today with reduced intake/activity. "
        f"{bp_line}. {dizzy}. {missed}. "
        "Hydration appears reduced. Mood described as lower/withdrawn."
    )
    lines.append("")
    lines.append("### Pertinent positives")
    if bp:
        lines.append(f"- Low BP reading reported: {bp[2]}")
    if "dizzy" in note_text.lower():
        lines.append("- Dizziness when standing reported")
    if "missed" in note_text.lower():
        lines.append("- Missed a medication dose reported")
    if "very little water" in note_text.lower() or "drank less" in note_text.lower():
        lines.append("- Reduced hydration reported")

    lines.append("")
    lines.append("### Questions for clinician")
    lines.append("- Could symptoms relate to hydration, medication timing, or blood pressure variability?")
    lines.append("- What parameters should trigger urgent evaluation (e.g., BP thresholds, worsening dizziness)?")
    lines.append("- Any recommended monitoring cadence for BP/symptoms over the next few days?")

    lines.append("")
    lines.append("### What to track before visit")
    lines.append("- BP readings with timestamps (if available)")
    lines.append("- Episodes of dizziness (timing, triggers, duration)")
    lines.append("- Food/fluid intake estimate")
    lines.append("- Meds taken/missed with approximate times")
    return "\n".join(lines)

def demo_care_circle_msg(note_text: str, audience: str, tone: str):
    lines = []
    lines.append(f"## 👥 Care Circle Message (Demo Mode)")
    lines.append(f"**Audience:** {audience} | **Tone:** {tone}")
    lines.append("")
    msg = []
    msg.append("Quick update:")
    if "dizzy" in note_text.lower():
        msg.append("- Had dizziness when standing today.")
    bp = _find_bp(note_text)
    if bp:
        msg.append(f"- BP reading reported: {bp[2]}.")
    if "missed" in note_text.lower():
        msg.append("- Missed at least one medication dose (noted).")
    msg.append("- Next steps: encourage fluids/food if appropriate, recheck BP later, and monitor symptoms.")
    if tone.lower().startswith("urgent"):
        msg.append("If symptoms worsen, we should contact clinician / consider urgent care.")
    lines.append("\n".join(msg[:7]))
    return "\n".join(lines)

def demo_caregiver_wellbeing(note_text: str):
    t = note_text.lower()
    burnout_phrases = _contains_any(t, ["exhaust", "overwhelm", "can't", "tired", "stress", "burnout", "cry", "anxious"])
    lines = []
    lines.append("## 🧘 Caregiver Wellbeing (Demo Mode)")
    lines.append("### Signals (only if present)")
    if burnout_phrases:
        lines.append(f"- Possible strain cues: {', '.join(sorted(set(burnout_phrases)))}")
    else:
        lines.append("- No explicit caregiver strain language detected in the note.")
    lines.append("")
    lines.append("### 10-minute reset plan (practical)")
    lines.append("- Drink water + quick snack.")
    lines.append("- Send a 2-line status update to someone in the care circle.")
    lines.append("- Pick ONE task to do next; park the rest.")
    lines.append("")
    lines.append("### Delegate / share load")
    lines.append("- Ask someone to cover: a meal, a 30-minute visit, a pharmacy run, or a check-in call.")
    lines.append("- If nights are tough, rotate shifts (even 2–3 hour blocks).")
    lines.append("")
    lines.append("### Boundary reminder")
    lines.append("- You don’t have to do everything perfectly. You’re aiming for safety + consistency.")
    return "\n".join(lines)


# ----------------------------
# LLM call helper (with graceful fallback)
# ----------------------------
SYSTEM = f"""You are a careful caregiving assistant.
Rules:
- Do NOT diagnose or claim medical certainty.
- Only use information explicitly present in the caregiver note/context.
- If something isn't mentioned, do not invent it.
- Be concrete and actionable.
- If urgent risk is strongly suggested, say: "Consider urgent medical care" without diagnosing.
- Write output in {output_lang}.
"""

def llm_available() -> bool:
    if mode.startswith("Force Demo"):
        return False
    if OpenAI is None:
        return False
    return bool(os.getenv("OPENAI_API_KEY", ""))

def call_llm_or_demo(prompt: str, demo_fn, *demo_args):
    if not llm_available():
        return demo_fn(*demo_args)

    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        # Quota/billing/rate-limit errors -> demo fallback (no stage-crash)
        msg = str(e).lower()
        if "insufficient_quota" in msg or "exceeded your current quota" in msg or "429" in msg:
            return demo_fn(*demo_args)
        raise


# ----------------------------
# Tabs (Differentiated features)
# ----------------------------
tabs = st.tabs([
    "🚦 Risk Radar",
    "✅ Action Planner",
    "🩺 Doctor Brief",
    "👥 Care Circle",
    "🧘 Wellbeing",
])

# 1) Risk Radar
with tabs[0]:
    st.subheader("🚦 Risk Radar")
    st.write("Answers: **Is anything potentially urgent or unsafe?** (non-diagnostic, evidence-based)")

    if st.button("Run Risk Radar", type="primary"):
        prompt = f"""
Create a Risk Radar from the caregiver note.

Context:
{context}

Caregiver note:
{note}

Output format (use headings):
1) Urgency level: LOW / MODERATE / HIGH (non-diagnostic)
2) Signals detected (bullets). For each signal:
   - Why it was flagged (include exact quote from note)
   - Suggested action: monitor / monitor closely / consider urgent medical care
3) What to monitor next (bullets)
Rules: Do NOT diagnose. Do NOT invent details.
"""
        with st.spinner("Analyzing risk..."):
            out = call_llm_or_demo(prompt, demo_risk_radar, note)
        st.markdown(out)

# 2) Action Planner
with tabs[1]:
    st.subheader("✅ Action Planner")
    st.write("Answers: **What should I do next — in priority order?**")

    if st.button("Generate Action Plan", type="primary"):
        prompt = f"""
Generate a prioritized caregiver Action Plan from the note.

Context:
{context}

Caregiver note:
{note}

Output format (use headings):
- Do NOW (3–6 bullets)
- Monitor (3–6 bullets)
- Confirm (missing info to clarify) (2–6 bullets)
- Schedule / delegate (2–5 bullets)
Rules: Do NOT diagnose. Use only note/context.
"""
        with st.spinner("Planning actions..."):
            out = call_llm_or_demo(prompt, demo_action_planner, note)
        st.markdown(out)

# 3) Doctor Brief
with tabs[2]:
    st.subheader("🩺 Doctor Brief")
    st.write("Answers: **How do I communicate clearly to a clinician?**")

    if st.button("Generate Doctor Brief", type="primary"):
        prompt = f"""
Create a clinician-friendly brief based strictly on the note.

Context:
{context}

Caregiver note:
{note}

Output format (use headings):
1) 4–6 sentence summary (no diagnosis)
2) Pertinent positives (bullets)
3) Medication adherence (bullets; only what is stated)
4) Key questions for clinician (2–6)
5) What to track before visit (3–8)
Rules: Use only note/context. No invented negatives.
"""
        with st.spinner("Creating brief..."):
            out = call_llm_or_demo(prompt, demo_doctor_brief, note)
        st.markdown(out)

# 4) Care Circle
with tabs[3]:
    st.subheader("👥 Care Circle Message")
    st.write("Answers: **How do I update others quickly without confusion?**")

    audience = st.selectbox("Audience", ["Family group chat", "Paid caregiver", "Nurse/care team", "Neighbor helping out"], index=0)
    tone = st.selectbox("Tone", ["Warm + reassuring", "Neutral + factual", "Urgent (only if needed)"], index=1)

    if st.button("Generate Message", type="primary"):
        prompt = f"""
Write a short message for {audience}.
Tone: {tone}

Context:
{context}

Caregiver note:
{note}

Constraints:
- 3–7 short lines max
- Include: 1) key update, 2) what help is needed, 3) next step
- If urgent risk is strongly suggested by the note, recommend contacting clinician/urgent care (non-diagnostic).
No diagnosis. Use only note/context.
"""
        with st.spinner("Drafting message..."):
            out = call_llm_or_demo(prompt, demo_care_circle_msg, note, audience, tone)
        st.markdown(out)

# 5) Wellbeing
with tabs[4]:
    st.subheader("🧘 Caregiver Wellbeing")
    st.write("Answers: **How is the caregiver coping and what support helps right now?**")

    caregiver_note = st.text_area(
        "Optional: caregiver’s own note (1–3 lines). Leave empty if not available.",
        value="I feel exhausted this week and I'm overwhelmed managing nights.",
        height=90
    )

    if st.button("Generate Wellbeing Support", type="primary"):
        combined = note + "\n\nCaregiver note: " + caregiver_note
        prompt = f"""
Assess caregiver wellbeing and suggest non-medical support steps.

Context:
{context}

Caregiver note:
{note}

Caregiver's self-note:
{caregiver_note}

Output format:
1) Burnout/strain signals (ONLY if present; include quote if you cite a signal)
2) 10-minute reset plan (practical)
3) Delegate/share-load ideas (concrete examples)
4) Boundary reminder (1–2 lines)
Rules: Non-medical. No diagnosis. Use only provided text.
"""
        with st.spinner("Supporting caregiver..."):
            out = call_llm_or_demo(prompt, demo_caregiver_wellbeing, combined)
        st.markdown(out)

st.markdown("---")
st.caption("Tip: This demo stands out because each tab solves a different caregiver pain: risk → actions → clinician comms → team coordination → caregiver wellbeing.")

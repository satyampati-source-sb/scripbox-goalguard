import streamlit as st
import numpy as np
import plotly.graph_objects as go
from google import genai
import os
from google.genai.errors import ClientError

# ====================== PASSWORD GATE ======================
st.set_page_config(page_title="Scripbox GoalGuard", page_icon="🛡️", layout="centered")

st.title("🛡️ Scripbox GoalGuard")

# Change this password to anything you like
PASSWORD = "hackathon2026"   # ←←← CHANGE THIS TO YOUR OWN PASSWORD

if "password_correct" not in st.session_state:
    st.session_state.password_correct = False

if not st.session_state.password_correct:
    st.markdown("### 🔐 Enter password to access the tool")
    entered_password = st.text_input("Password", type="password")
    if st.button("Unlock"):
        if entered_password == PASSWORD:
            st.session_state.password_correct = True
            st.rerun()
        else:
            st.error("❌ Wrong password")
    st.stop()   # stops the rest of the app from loading
# ===========================================================

# Only people who know the password will see everything below
os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
client = genai.Client()

st.markdown("**See how your behaviour affects your goal achievement** — 100% private, no portfolio upload needed.")

# ================== GOAL INPUT SECTION ==================
st.header("1️⃣ Your Goal")
goal_desc = st.text_input("Describe your goal in plain English", value="Rs 3 Crore for my retirement in 10 years")

col_unit, col_val = st.columns([1, 3])
with col_unit:
    unit = st.selectbox("Target unit", options=["Crores", "Lakhs"], index=0)
with col_val:
    if unit == "Crores":
        target_value = st.number_input("Target amount", value=3.0, min_value=0.1, step=0.1, format="%.1f")
        target_amount = int(target_value * 10_000_000)
    else:
        target_value = st.number_input("Target amount", value=300.0, min_value=1.0, step=1.0, format="%.0f")
        target_amount = int(target_value * 100_000)

st.success(f"**Target: ₹{target_amount:,.0f}**")

years = st.number_input("Time horizon (years)", value=10, min_value=1, max_value=30)
monthly_sip = st.number_input("Planned monthly SIP (₹)", value=122000, min_value=1000, step=1000)

# Current savings
st.subheader("💰 Amount already saved for this goal")
col_unit2, col_val2 = st.columns([1, 3])
with col_unit2:
    unit2 = st.selectbox("Current savings unit", options=["Crores", "Lakhs"], index=1)
with col_val2:
    if unit2 == "Crores":
        saved_value = st.number_input("Current savings", value=0.0, min_value=0.0, step=0.1, format="%.1f")
        current_savings = int(saved_value * 10_000_000)
    else:
        saved_value = st.number_input("Current savings", value=0.0, min_value=0.0, step=1.0, format="%.0f")
        current_savings = int(saved_value * 100_000)

st.success(f"**Already saved: ₹{current_savings:,.0f}**")
# ========================================================

# Behaviour quiz (unchanged)
st.header("2️⃣ Your Behaviour Profile (8 quick questions)")
st.caption("Be honest — this is what makes the magic happen!")

q1 = st.slider("During market crashes (like 2020), how often did you pause or reduce your SIP?", 1, 5, 3)
q2 = st.slider("If markets fall 15% tomorrow, how likely are you to stop your SIP?", 1, 5, 3)
q3 = st.slider("Do you ever buy a fund just because everyone on social media is talking about it?", 1, 5, 2)
q4 = st.slider("Would you rather lock in a small gain than risk it for a bigger upside?", 1, 5, 3)
q5 = st.slider("How much do recent market news affect your investment decisions?", 1, 5, 3)
q6 = st.slider("How often do you skip SIPs when cash feels tight?", 1, 5, 2)
q7 = st.slider("Have you ever sold a fund early because of fear of further loss?", 1, 5, 2)
q8 = st.slider("Do you check your portfolio daily/weekly during volatile times?", 1, 5, 4)

answers = np.array([q1, q2, q3, q4, q5, q6, q7, q8])
discipline_score = int(100 - (answers.mean() - 1) * 12.5)
discipline_score = max(0, min(100, discipline_score))

if st.button("🚀 Analyse My Goal", type="primary"):
    with st.spinner("Running AI + Monte Carlo simulation..."):
        n_sim = 5000
        base_return = 0.12
        vol = 0.18
        behavioural_drag = (100 - discipline_score) / 100 * 0.035
        
        base_corpus = np.zeros(n_sim)
        behaviour_corpus = np.zeros(n_sim)
        for i in range(n_sim):
            r_base = np.random.normal(base_return, vol, years)
            r_behave = r_base - behavioural_drag
            corpus_base = float(current_savings)
            corpus_behave = float(current_savings)
            for yr in range(years):
                corpus_base = (corpus_base + monthly_sip * 12) * (1 + r_base[yr])
                corpus_behave = (corpus_behave + monthly_sip * 12) * (1 + r_behave[yr])
            base_corpus[i] = corpus_base
            behaviour_corpus[i] = corpus_behave
        
        base_prob = np.mean(base_corpus >= target_amount) * 100
        behaviour_prob = np.mean(behaviour_corpus >= target_amount) * 100
        
        crisis_harm = int((100 - discipline_score) * 0.65)
        crisis_impact_pct = round((100 - discipline_score) / 100 * 22, 1)
    try: 
        prompt = f"""
        You are a friendly and encouraging behavioural finance coach.

        User's goal: {goal_desc}
        Already saved: ₹{current_savings:,.0f}
        Discipline score: {discipline_score}/100
        Base probability: {base_prob:.0f}%
        Behaviour-adjusted probability: {behaviour_prob:.0f}%
        Crisis harm chance: {crisis_harm}%

        Give a warm, but detailed response based on the metrics shared by the User.
        Focus on general investment behaviour, emotions, habits and mindset and suggest corrective actions.
                
        IMPORTANT RULES:
        - NEVER mention or suggest any specific features, tools, buttons, or actions inside any app.
        - NEVER invent any product features.
        - Keep advice very general and high-level.
        - Stay positive and encouraging.

        Use simple, friendly language.
        """

        ai_response = client.models.generate_content(model="gemini-2.5-flash-lite", contents=prompt).text
        except ClientError as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "quota" in str(e).lower():
                ai_response = "⚠️ Gemini API quota limit reached for today (free tier). Please try again tomorrow or create a new API key from a new Google Cloud project."
            else:
                ai_response = f"⚠️ AI coach temporarily unavailable: {str(e)[:100]}..."
        except Exception as e:
            ai_response = "⚠️ The AI coach is temporarily unavailable. However, your probabilities and chart are still shown above."
        # =====================================
        
        st.success("✅ Your GoalGuard Report")
        st.metric("Your Discipline Score", f"{discipline_score}/100")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Ideal (Disciplined) Probability", f"{base_prob:.0f}%")
        with col2:
            delta = f"{behaviour_prob - base_prob:+.0f}%"
            st.metric("Your Behaviour-Adjusted Probability", f"{behaviour_prob:.0f}%", delta)
        
        st.metric("Crisis Harm Likelihood", f"{crisis_harm}% chance", f"Could reduce your goal by ~{crisis_impact_pct}%")
        
        st.info(f"""
        **What do these percentages mean?**  
        We ran **5,000 possible market scenarios** (12% avg return, 18% volatility).  
        The simulation now starts with the ₹{current_savings:,.0f} you have already saved.
        """)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["Ideal Path", "Your Path"], y=[base_prob, behaviour_prob], text=[f"{base_prob:.0f}%", f"{behaviour_prob:.0f}%"], textposition="auto"))
        fig.update_layout(title="Goal Achievement Probability", yaxis_title="Probability (%)", yaxis_range=[0,100])
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("🧠 Your Personalised Coach Advice")
        st.write(ai_response)
        
        total_contrib = monthly_sip * 12 * years
        st.caption(f"Total future contributions planned: ₹{total_contrib:,.0f} | This is a prototype for the Scripbox hackathon. Not financial advice. Built with ❤️ using Gemini AI + Monte Carlo.")

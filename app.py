import streamlit as st
import numpy as np
import plotly.graph_objects as go
from google import genai
import os

# ====================== GEMINI KEY ======================
os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
client = genai.Client()

st.set_page_config(page_title="Scripbox GoalGuard", page_icon="🛡️", layout="centered")

st.title("🛡️ Scripbox GoalGuard")
st.markdown("**See how your behaviour affects your goal achievement** — 100% private, no portfolio upload needed.")

# ================== USER-FRIENDLY GOAL INPUT ==================
st.header("1️⃣ Your Goal")
goal_desc = st.text_input("Describe your goal in plain English", value="Rs 3 Crore for my retirement in 10 years")

col_unit, col_val = st.columns([1, 3])
with col_unit:
    unit = st.selectbox("Unit", options=["Crores", "Lakhs"], index=0)
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
# =============================================================

# Behaviour quiz
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
            corpus_base = 0.0
            corpus_behave = 0.0
            for yr in range(years):
                corpus_base = (corpus_base + monthly_sip * 12) * (1 + r_base[yr])
                corpus_behave = (corpus_behave + monthly_sip * 12) * (1 + r_behave[yr])
            base_corpus[i] = corpus_base
            behaviour_corpus[i] = corpus_behave
        
        base_prob = np.mean(base_corpus >= target_amount) * 100
        behaviour_prob = np.mean(behaviour_corpus >= target_amount) * 100
        
        crisis_harm = int((100 - discipline_score) * 0.65)
        crisis_impact_pct = round((100 - discipline_score) / 100 * 22, 1)
        
                # STRICTER PROMPT - no more hallucinated Scripbox features
        prompt = f"""
        You are a friendly and encouraging behavioural finance coach.

        User's goal: {goal_desc}
        Discipline score: {discipline_score}/100
        Base probability: {base_prob:.0f}%
        Behaviour-adjusted probability: {behaviour_prob:.0f}%
        Crisis harm chance: {crisis_harm}%

        Give a warm, short (maximum 3-4 sentences) response.
        Focus ONLY on general investment behaviour, emotions, habits and mindset.
        
        IMPORTANT RULES:
        - NEVER mention or suggest any specific features, tools, buttons, or actions inside the Scripbox app.
        - NEVER invent any product features.
        - Keep advice very general and high-level (examples: "stick to your monthly plan", "avoid checking too often", "focus on the long term", "celebrate small wins", etc.).
        - Stay positive and encouraging.

        Use simple, friendly language.
        """

        ai_response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt).text
        st.success("✅ Your GoalGuard Report")
        st.metric("Your Discipline Score", f"{discipline_score}/100")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Ideal (Disciplined) Probability", f"{base_prob:.0f}%")
        with col2:
            delta = f"{behaviour_prob - base_prob:+.0f}%"
            st.metric("Your Behaviour-Adjusted Probability", f"{behaviour_prob:.0f}%", delta)
        
        st.metric("Crisis Harm Likelihood", f"{crisis_harm}% chance", f"Could reduce your goal by ~{crisis_impact_pct}%")
        
        st.info("""
        **What do these percentages mean?**  
        We ran **5,000 possible market scenarios** (12% avg return, 18% volatility).  
        Ideal = % of scenarios you hit your goal if you stay perfectly disciplined.  
        Your version = same simulation but with the small drag from your quiz answers.
        """)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(x=["Ideal Path", "Your Path"], y=[base_prob, behaviour_prob], text=[f"{base_prob:.0f}%", f"{behaviour_prob:.0f}%"], textposition="auto"))
        fig.update_layout(title="Goal Achievement Probability", yaxis_title="Probability (%)", yaxis_range=[0,100])
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("🧠 Your Personalised Coach Advice")
        st.write(ai_response)
        
        total_contrib = monthly_sip * 12 * years
        st.caption(f"Total contributions planned: ₹{total_contrib:,.0f} | This is a prototype for the Scripbox hackathon. Not financial advice. Built with ❤️ using Gemini AI + Monte Carlo.")

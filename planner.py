import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. CLEAN LIGHT UI STYLING ---
st.set_page_config(page_title="Wealth Studio", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; color: #1e293b; }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border: 1px solid #e2e8f0;
    }
    .stButton>button {
        background-color: #d32f2f;
        color: white;
        border-radius: 8px;
        font-weight: 600;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #b71c1c;
        box-shadow: 0 4px 12px rgba(211, 47, 47, 0.2);
    }
    .insight-card {
        background-color: #fff1f2;
        padding: 24px;
        border-radius: 12px;
        border-left: 5px solid #d32f2f;
        margin-bottom: 20px;
        color: #9f1239;
    }
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CORE ENGINES ---
def run_simulation(data, monthly_override=None):
    m_save = monthly_override if monthly_override is not None else data['monthly']
    curr_bal = data['savings']
    
    # Monthly Inflation Calculation
    inf_m = (1 + data['inflation']/100)**(1/12) - 1
    years_to_ret = max(0, data['ret_age'] - data['age'])
    
    # Cost of lifestyle at the moment of retirement
    fut_spend = data['spend'] * ((1 + data['inflation']/100) ** years_to_ret)
    gross_draw = fut_spend / (1 - (data['tax']/100))
    
    ages, balances = [], []
    exhaust_age = None
    
    for m in range(int((data['death_age'] - data['age'] + 1) * 12)):
        age = data['age'] + (m/12)
        ages.append(age)
        balances.append(curr_bal)
        
        if age < data['ret_age']:
            # Accumulation Phase
            curr_bal = (curr_bal + m_save) * (1 + (data['roi']/100)/12)
        else:
            # Decumulation Phase
            pension = data['cpp_oas'] * ((1 + data['inflation']/100) ** (age - data['age']))
            curr_bal = (curr_bal - (gross_draw - pension)) * (1 + (4.0/100)/12)
            gross_draw *= (1 + inf_m)
            
            if curr_bal <= 0 and exhaust_age is None:
                exhaust_age = int(age)
                curr_bal = 0
            
    return ages, balances, exhaust_age, fut_spend

def solve_for_legacy(data):
    low, high = 0, 100000
    for _ in range(18):
        mid = (low + high) / 2
        _, balances, _, _ = run_simulation(data, mid)
        if balances[-1] < data['legacy']: low = mid
        else: high = mid
    return high

# --- 3. SESSION STATE ---
if 'step' not in st.session_state:
    st.session_state.step = 1
    st.session_state.data = {
        "name": "Investor", "age": 35, "ret_age": 65, "death_age": 95,
        "savings": 250000, "monthly": 2000, "roi": 5.5, "cpp_oas": 1900,
        "spend": 6000, "inflation": 2.1, "tax": 22, "legacy": 100000
    }
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- 4. SIDEBAR: BURN RATE ADVISOR ---
with st.sidebar:
    st.header("🔥 Burn Rate Advisor")
    d = st.session_state.data
    _, balances, exhaust_age, fut_spend = run_simulation(d)
    
    st.markdown(f"**Assumed Inflation:** {d['inflation']}%")
    if exhaust_age:
        st.error(f"⚠️ Exhaustion: Age {exhaust_age}")
    else:
        st.success("✅ Plan Sustainable")
    
    st.write(f"**Retirement Spend:** ${fut_spend:,.0f}/mo")
    st.divider()
    
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): st.write(msg["content"])

    if prompt := st.chat_input("Ask about inflation or burn..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        if "inflation" in prompt.lower():
            resp = f"A {d['inflation']}% inflation rate means your ${d['spend']:,} lifestyle today will cost ${fut_spend:,.0f} when you retire."
        else:
            resp = "Adjust the inflation slider in Step 2 to see how rising costs affect your legacy."
        st.session_state.chat_history.append({"role": "assistant", "content": resp})
        st.rerun()

# --- 5. MAIN UI ---
st.title("🇨🇦 Wealth Studio")

if st.session_state.step == 1:
    st.subheader("Step 1: Let's Get to Know You ")
    name = st.text_input("Name", st.session_state.data['name'])
    c1, c2 = st.columns(2)
    age = c1.number_input("Current Age", 18, 75, st.session_state.data['age'])
    ret_age = c2.number_input("Retirement Age", age+1, 85, st.session_state.data['ret_age'])
    if st.button("Next: Assets & ROI →"):
        st.session_state.data.update({"name": name, "age": age, "ret_age": ret_age})
        st.session_state.step = 2; st.rerun()

elif st.session_state.step == 2:
    st.subheader("Step 2: Assets, ROI & Inflation")
    profiles = {"Conservative": 4.0, "Balanced": 5.5, "Growth": 6.5, "Aggressive": 7.5}
    c1, c2 = st.columns(2)
    savings = c1.number_input("Current Assets ($)", 0, value=st.session_state.data['savings'])
    monthly = c2.number_input("Monthly Contribution ($)", 0, value=st.session_state.data['monthly'])
    
    profile = st.selectbox("Risk Profile", options=list(profiles.keys()), index=1)
    roi = st.slider("Fine-tune ROI (%)", 1.0, 10.0, profiles[profile], step=0.1)
    
    # NEW INFLATION ADJUSTMENT FIELD
    inflation = st.slider("Expected Inflation Rate (%)", 0.0, 6.0, st.session_state.data['inflation'], 
                          help="FP Canada 2025 standard is 2.1%. Higher inflation increases future costs.")
    
    if st.button("Next: Lifestyle & Legacy →"):
        st.session_state.data.update({"savings": savings, "monthly": monthly, "roi": roi, "inflation": inflation})
        st.session_state.step = 3; st.rerun()

elif st.session_state.step == 3:
    st.subheader("Step 3: Legacy & Spending")
    c1, c2 = st.columns(2)
    spend = c1.number_input("Monthly Spend (Today's $)", 1000, value=st.session_state.data['spend'])
    legacy = c2.number_input("Legacy Goal (Estate Target $)", 0, value=st.session_state.data['legacy'])
    death_age = st.number_input("Plan Duration (Death Age)", 80, 115, st.session_state.data['death_age'])
    if st.button("Finalize Simulations 🚀"):
        st.session_state.data.update({"spend": spend, "legacy": legacy, "death_age": death_age})
        st.session_state.step = 4; st.rerun()

elif st.session_state.step == 4:
    ages, balances, exhaust_age, fut_spend = run_simulation(st.session_state.data)
    req_save = solve_for_legacy(st.session_state.data)
    gap = req_save - st.session_state.data['monthly']

    st.markdown('<div class="insight-card">', unsafe_allow_html=True)
    if exhaust_age or balances[-1] < st.session_state.data['legacy']:
        st.markdown(f"### ⚠️ Inflation/Legacy Gap")
        st.write(f"At {st.session_state.data['inflation']}% inflation, you need to save **${req_save:,.0f}/mo** to hit your legacy goal.")
    else:
        st.markdown(f"### ✅ Sustainability Confirmed")
        st.write(f"Your plan outpaces inflation, leaving an estate of **${balances[-1]:,.0f}**.")
    st.markdown('</div>', unsafe_allow_html=True)

    m1, m2, m3 = st.columns(3)
    m1.metric("Peak Wealth", f"${max(balances):,.0f}")
    m2.metric("Savings Gap", f"${max(0, gap):,.0f}")
    m3.metric("Cost at Ret.", f"${fut_spend:,.0f}/mo")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ages, y=balances, fill='tozeroy', line_color="#d32f2f", fillcolor="rgba(211, 47, 47, 0.1)"))
    fig.update_layout(plot_bgcolor='white', paper_bgcolor='white', xaxis_title="Age", yaxis_title="Net Worth ($)")
    st.plotly_chart(fig, use_container_width=True)

    if st.button("⬅ Adjust Entries"):
        st.session_state.step = 1; st.rerun()

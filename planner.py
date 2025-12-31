import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. CONFIG & PREMIUM DARK UI ---
st.set_page_config(page_title="Canada Wealth Studio", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0f172a; color: #f1f5f9; }
    .stMetric { background-color: #1e293b; padding: 20px; border-radius: 15px; border: 1px solid #334155; }
    div[data-testid="stMetricValue"] { color: #ef4444; font-weight: 800; }
    
    .stButton>button { 
        border-radius: 12px; height: 3.5em; width: 100%;
        background: linear-gradient(135deg, #ef4444 0%, #b91c1c 100%); 
        color: white; border: none; font-weight: 700;
    }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4); }
    
    .insight-card { 
        background-color: #1e293b; padding: 24px; border-radius: 16px; 
        border-left: 6px solid #ef4444; margin-bottom: 25px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    section[data-testid="stSidebar"] { background-color: #1e293b !important; border-right: 1px solid #334155; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE ENGINE: LEGACY & BURN CALCULATOR ---
def run_simulation(data, monthly_override=None):
    m_save = monthly_override if monthly_override is not None else data['monthly']
    curr_bal = data['savings']
    
    # Retirement Lifestyle Math (Adjusted for 2025 Inflation)
    inf_m = (1 + data['inflation']/100)**(1/12) - 1
    years_to_ret = max(0, data['ret_age'] - data['age'])
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
            # Decumulation Phase (Burn Rate)
            # CPP/OAS indexed to inflation
            pension = data['cpp_oas'] * ((1 + data['inflation']/100) ** (age - data['age']))
            curr_bal = (curr_bal - (gross_draw - pension)) * (1 + (4.0/100)/12)
            gross_draw *= (1 + inf_m)
            
            if curr_bal <= 0 and exhaust_age is None:
                exhaust_age = int(age)
                curr_bal = 0
            
    return ages, balances, exhaust_age, fut_spend

def solve_for_legacy(data):
    # Binary Search to find savings needed to hit the exact Legacy Goal
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

# --- 4. SIDEBAR: BURN RATE CHAT ---
with st.sidebar:
    st.title("🔥 Burn Rate Analyst")
    d = st.session_state.data
    _, balances, exhaust_age, fut_spend = run_simulation(d)
    
    st.markdown("### 📊 Live Stats")
    status = "⚠️ DEEP BURN" if exhaust_age else "✅ STABLE"
    st.write(f"**Portfolio Status:** {status}")
    st.write(f"**Monthly Ret. Burn:** ${fut_spend:,.0f}")
    st.write(f"**Target Estate:** ${d['legacy']:,}")
    
    st.divider()
    
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): st.write(msg["content"])

    if prompt := st.chat_input("Ask about your burn rate..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        
        # Burn Rate Logic
        if "burn" in prompt.lower() or "spend" in prompt.lower():
            resp = f"Your projected retirement burn rate is ${fut_spend:,.0f}/mo. At your current ROI, this burn will deplete your capital by age {exhaust_age if exhaust_age else '95+' }."
        elif "legacy" in prompt.lower() or "leave" in prompt.lower():
            resp = f"To leave ${d['legacy']:,} at age {d['death_age']}, your portfolio cannot drop below that floor. Currently, you are projected to end with ${balances[-1]:,.0f}."
        else:
            resp = "I can analyze how your burn rate affects your legacy. Try asking: 'Is my burn rate too high for my legacy goal?'"
        
        st.session_state.chat_history.append({"role": "assistant", "content": resp})
        st.rerun()

# --- 5. WIZARD STEPS ---
if st.session_state.step == 1:
    st.title("👤 Step 1: Profile")
    name = st.text_input("Investor Name", st.session_state.data['name'])
    c1, c2 = st.columns(2)
    age = c1.number_input("Current Age", 18, 75, st.session_state.data['age'])
    ret_age = c2.number_input("Target Retirement Age", age+1, 85, st.session_state.data['ret_age'])
    if st.button("Next: Assets →"):
        st.session_state.data.update({"name": name, "age": age, "ret_age": ret_age})
        st.session_state.step = 2; st.rerun()

elif st.session_state.step == 2:
    st.title("📈 Step 2: Asset Allocation")
    profiles = {"Conservative (4%)": 4.0, "Balanced (5.5%)": 5.5, "Growth (6.5%)": 6.5, "Aggressive (7.5%)": 7.5}
    c1, c2 = st.columns(2)
    savings = c1.number_input("Current Liquid Assets ($)", 0, value=st.session_state.data['savings'])
    monthly = c2.number_input("Current Monthly Savings ($)", 0, value=st.session_state.data['monthly'])
    
    profile = st.selectbox("Select Risk Profile", options=list(profiles.keys()), index=1)
    roi = st.slider("Fine-tune ROI %", 1.0, 10.0, profiles[profile])
    if st.button("Next: Legacy & Spending →"):
        st.session_state.data.update({"savings": savings, "monthly": monthly, "roi": roi})
        st.session_state.step = 3; st.rerun()

elif st.session_state.step == 3:
    st.title("🎁 Step 3: Desired Legacy & Spending")
    c1, c2 = st.columns(2)
    spend = c1.number_input("Monthly Desired Spend (Today's $)", 1000, value=st.session_state.data['spend'])
    legacy = c2.number_input("Desired Amount to Leave Behind ($)", 0, value=st.session_state.data['legacy'])
    death_age = st.number_input("Plan for Life Expectancy (Age)", 80, 115, st.session_state.data['death_age'])
    if st.button("Analyze My Future 🚀"):
        st.session_state.data.update({"spend": spend, "legacy": legacy, "death_age": death_age})
        st.session_state.step = 4; st.rerun()

elif st.session_state.step == 4:
    d = st.session_state.data
    ages, balances, exhaust_age, fut_spend = run_simulation(d)
    req_save = solve_for_legacy(d)
    gap = req_save - d['monthly']

    st.title(f"🏆 Financial Vision: {d['name']}")
    
    st.markdown('<div class="insight-card">', unsafe_allow_html=True)
    if exhaust_age or balances[-1] < d['legacy']:
        st.subheader("⚠️ Legacy Gap Identified")
        st.write(f"To spend ${d['spend']:,}/mo and leave **${d['legacy']:,}** at age {d['death_age']}:")
        st.write(f"👉 You need to save **${req_save:,.0f}/mo** (Increase of ${max(0, gap):,.0f}).")
    else:
        st.subheader("✅ Surplus Plan")
        st.write(f"Your plan is sustainable. You are projected to leave **${balances[-1]:,.0f}**, exceeding your goal.")
    st.markdown('</div>', unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Peak Wealth", f"${max(balances):,.0f}")
    c2.metric("Monthly Gap", f"${max(0, gap):,.0f}")
    c3.metric("Final Estate", f"${balances[-1]:,.0f}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=ages, y=balances, fill='tozeroy', name="Portfolio", line_color="#ef4444", fillcolor="rgba(239, 68, 68, 0.1)"))
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#f1f5f9", height=450,
                      margin=dict(l=0, r=0, t=20, b=0), xaxis_title="Age", yaxis_title="Balance ($)")
    st.plotly_chart(fig, use_container_width=True)

    if st.button("⬅ Adjust Scenario"):
        st.session_state.step = 1; st.rerun()

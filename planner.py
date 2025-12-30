import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Ultimate Retirement Simulator", layout="wide")
st.title("🏦 Lifetime Wealth & Drawdown Simulator")

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("📋 Phase 1: Accumulation")
    curr_age = st.number_input("Current Age", 18, 100, 30)
    ret_age = st.number_input("Retirement Age", curr_age, 100, 65)
    curr_savings = st.number_input("Current Savings ($)", 0, value=50000)
    monthly_contrib = st.number_input("Monthly Contribution ($)", 0, value=1500)
    return_rate = st.slider("Pre-Retirement Return (%)", 0.0, 12.0, 7.0)
    
    st.header("📋 Phase 2: Retirement")
    death_age = st.number_input("Plan Until Age", ret_age, 110, 95)
    monthly_spend = st.number_input("Desired Monthly Spend ($)", 0, value=5000)
    ret_return_rate = st.slider("Post-Retirement Return (%)", 0.0, 12.0, 4.0)
    inflation = st.slider("Annual Inflation (%)", 0.0, 10.0, 2.5)

# --- Calculations ---
years_to_ret = ret_age - curr_age
years_in_ret = death_age - ret_age

# Tracking variables
ages = []
balances = []
current_balance = curr_savings
monthly_inflation = (1 + inflation/100)**(1/12) - 1

# 1. Accumulation Loop
for year in range(curr_age, ret_age):
    for month in range(12):
        ages.append(year + month/12)
        balances.append(current_balance)
        # Monthly growth + monthly savings
        current_balance = (current_balance + monthly_contrib) * (1 + (return_rate/100)/12)

# 2. Drawdown Loop
adjusted_spend = monthly_spend
for year in range(ret_age, death_age + 1):
    for month in range(12):
        ages.append(year + month/12)
        balances.append(current_balance)
        # Monthly growth - inflation-adjusted spending
        current_balance = (current_balance - adjusted_spend) * (1 + (ret_return_rate/100)/12)
        adjusted_spend *= (1 + monthly_inflation)
        if current_balance < 0: current_balance = 0

# --- Results Dashboard ---
df = pd.DataFrame({"Age": ages, "Balance": balances})
peak_wealth = max(balances)
end_balance = balances[-1]

c1, c2, c3 = st.columns(3)
c1.metric("Peak Net Worth", f"${peak_wealth:,.0f}")
c2.metric("Balance at Age {death_age}", f"${end_balance:,.0f}")
c3.metric("Monthly Spend (Start of Ret.)", f"${monthly_spend:,.0f}")

# --- Visuals ---
fig = go.Figure()
# Area chart for wealth
fig.add_trace(go.Scatter(x=df["Age"], y=df["Balance"], fill='tozeroy', 
                         line_color='rgb(46, 204, 113)', name="Portfolio Value"))

# Vertical line for Retirement Age
fig.add_vline(x=ret_age, line_dash="dash", line_color="orange", annotation_text="Retirement Starts")

fig.update_layout(title="Your Lifetime Wealth Trajectory", xaxis_title="Age", yaxis_title="Balance ($)")
st.plotly_chart(fig, use_container_width=True)

# Status Message
if end_balance > 0:
    st.success(f"✅ Your money is projected to last until age {death_age}!")
else:
    # Find the age where balance hits zero
    zero_age = df[df["Balance"] == 0]["Age"].min()
    st.error(f"⚠️ Warning: Your savings may run out at age {int(zero_age)}.")

# --- Data Table ---
st.subheader("📊 Detailed Annual Snapshot")
annual_df = df[::12].copy() # Take one snapshot per year
annual_df["Balance"] = annual_df["Balance"].map("${:,.2f}".format)
st.dataframe(annual_df, use_container_width=True)
"""Live dashboard for Py5cheSim using Streamlit."""
import json
import os
import time
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

STATE_FILE = "Statistics/live_state.json"

st.set_page_config(
    page_title="Py5cheSim Live Dashboard",
    page_icon="📡",
    layout="wide",
)

# ---- Sidebar controls ----
st.sidebar.title("Controls")
auto_refresh = st.sidebar.checkbox("Auto-refresh", value=True)
refresh_interval = st.sidebar.slider("Refresh interval (s)", 0.2, 2.0, 0.5, 0.1)
if st.sidebar.button("Force refresh"):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(
    "The dashboard reads `Statistics/live_state.json`, "
    "which the simulation overwrites every 30 ms."
)

# ---- Header ----
st.title("📡 Live Network Slice Allocation")
st.caption(f"Last page refresh: {datetime.now().strftime('%H:%M:%S')}")

# ---- Load state ----
if not os.path.exists(STATE_FILE):
    st.warning("Waiting for simulation to start... "
               "Run `python simulation.py` in another terminal.")
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()
    st.stop()

try:
    with open(STATE_FILE) as f:
        state = json.load(f)
except (json.JSONDecodeError, FileNotFoundError):
    st.warning("Reading state file... retrying.")
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()
    st.stop()

slices = state["slices"]
time_ms = state["time_ms"]
wall_delay = time.time() - state.get("wall_time", time.time())

# ---- Top metrics row ----
cols = st.columns(len(slices) + 2)
cols[0].metric("Sim time (ms)", f"{time_ms}")
cols[1].metric("Staleness", f"{wall_delay*1000:.0f} ms")

for i, (label, data) in enumerate(slices.items()):
    with cols[i + 2]:
        st.metric(
            f"{label} PRBs",
            f"{data['prbs']}",
            delta=f"{data['plr']:.1f}% PLR",
            delta_color="inverse",
        )

# ---- Charts in a grid ----
st.markdown("---")

col1, col2 = st.columns(2)

# PRB allocation - bar chart
with col1:
    st.subheader("PRB Allocation")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(slices.keys()),
        y=[d["prbs"] for d in slices.values()],
        marker_color=["#1f77b4", "#ff7f0e", "#2ca02c"][:len(slices)],
        text=[d["prbs"] for d in slices.values()],
        textposition="outside",
    ))
    fig.update_layout(
        height=300, margin=dict(l=10, r=10, t=30, b=10),
        yaxis_title="PRBs",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

# Buffer occupancy
with col2:
    st.subheader("Buffer Occupancy (packets)")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(slices.keys()),
        y=[d["buffer"] for d in slices.values()],
        marker_color=["#1f77b4", "#ff7f0e", "#2ca02c"][:len(slices)],
        text=[d["buffer"] for d in slices.values()],
        textposition="outside",
    ))
    fig.update_layout(
        height=300, margin=dict(l=10, r=10, t=30, b=10),
        yaxis_title="Packets",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

col3, col4 = st.columns(2)

# Throughput
with col3:
    st.subheader("Throughput (Mbps)")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(slices.keys()),
        y=[d["throughput"] for d in slices.values()],
        marker_color=["#1f77b4", "#ff7f0e", "#2ca02c"][:len(slices)],
        text=[f"{d['throughput']:.2f}" for d in slices.values()],
        textposition="outside",
    ))
    fig.update_layout(
        height=300, margin=dict(l=10, r=10, t=30, b=10),
        yaxis_title="Mbps",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

# PLR
with col4:
    st.subheader("Packet Loss Rate (%)")
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=list(slices.keys()),
        y=[d["plr"] for d in slices.values()],
        marker_color=["#1f77b4", "#ff7f0e", "#2ca02c"][:len(slices)],
        text=[f"{d['plr']:.2f}%" for d in slices.values()],
        textposition="outside",
    ))
    fig.update_layout(
        height=300, margin=dict(l=10, r=10, t=30, b=10),
        yaxis_title="PLR %",
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

# ---- Detailed table ----
st.markdown("---")
st.subheader("Detailed Slice State")
df = pd.DataFrame(slices).T
df.index.name = "Slice"
st.dataframe(df, use_container_width=True)

# ---- Auto refresh ----
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
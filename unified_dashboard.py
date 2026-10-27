"""Unified dashboard: live classifier + allocator state. Run in either env."""
import time
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from shared_bus import read_state


STATE_FILE = "shared/live_bus.json"

st.set_page_config(page_title="Slice Classifier + Allocator", layout="wide")

# Sidebar
st.sidebar.title("Controls")
auto = st.sidebar.checkbox("Auto-refresh", value=True)
interval = st.sidebar.slider("Refresh (s)", 0.5, 3.0, 1.0, 0.5)
if st.sidebar.button("Force refresh"):
    st.rerun()



def load():
     return read_state()

state = load()

st.title("📡 Live Slice Classifier + Resource Allocator")

col1, col2 = st.columns(2)

# --- Classifier panel ---
with col1:
    st.header("ML Classifier (ml_env)")
    cls = state.get("classifier", {})
    if cls:
        st.caption(f"Last update: {time.strftime('%H:%M:%S', time.localtime(cls.get('timestamp', 0)))}")
        st.metric("Active flows classified", cls.get("num_flows", 0))
        preds = cls.get("predictions", [])
        if preds:
            df = pd.DataFrame(preds)
            # Slice distribution
            counts = df["predicted_slice"].value_counts()
            fig = go.Figure(go.Bar(x=counts.index, y=counts.values,
                                   text=counts.values, textposition="outside"))
            fig.update_layout(height=250, title="Predicted Slice Distribution",
                              showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df.head(20), use_container_width=True)
        else:
            st.info("No flows classified in the last window.")
    else:
        st.info("Waiting for ML classifier to write data...")

# --- Allocator panel ---
with col2:
    st.header("Resource Allocator (py5chesim)")
    alloc = state.get("allocator", {})
    if alloc:
        st.caption(f"Sim time: {alloc.get('time_ms', '?')} ms")
        slices = alloc.get("slices", {})
        if slices:
            rows = []
            for name, d in slices.items():
                rows.append({
                    "Slice": name,
                    "PRBs": d.get("prbs", 0),
                    "PLR %": round(d.get("plr", 0), 2),
                    "Throughput (Mbps)": round(d.get("throughput", 0), 3),
                    "Buffer": d.get("buffer", 0),
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True)

            fig = go.Figure(go.Bar(
                x=df["Slice"], y=df["PRBs"],
                text=df["PRBs"], textposition="outside",
            ))
            fig.update_layout(height=250, title="PRB Allocation per Slice",
                              showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No slices in allocator state yet.")
    else:
        st.info("Waiting for allocator to write data...")

# Auto refresh
if auto:
    time.sleep(interval)
    st.rerun()
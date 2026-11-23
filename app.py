"""MIRQAB Ground Control — browser-based *demo* simulator and MATLAB CSV viewer.

This app simulates a mission in Python. It does NOT command MATLAB Online,
Simulink, or physical UAVs. Session state belongs to the current browser session.
"""
import io
import zipfile
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="MIRQAB Ground Control", page_icon="🛩️", layout="wide")

STATES = {0: "WAIT", 1: "PREPARE", 2: "TAKEOFF", 3: "EXECUTE", 4: "RETURN", 5: "LAND"}
STEPS = [0, 1, 2, 3, 3, 3, 4, 5]

# Illustrative local coordinates in kilometers, NOT real GPS positions.
# Both routes are fixed DEMO examples and show only progress already simulated.
DEMO_ROUTES_KM = {
    "Stork VTOL": [(0, 0), (0, 0), (0.7, 0.6), (1.5, 1.2), (2.6, 1.7),
                   (3.0, 1.1), (1.3, 0.5), (0, 0)],
    "Small UAV": [(0, 0), (0, 0), (-0.3, 0.6), (-1.0, 1.2), (-1.9, 1.7),
                  (-2.5, 1.0), (-0.8, 0.4), (0, 0)],
}


def show_demo_routes(index):
    fig = go.Figure()
    for name, route in DEMO_ROUTES_KM.items():
        traveled = route[:index + 1]
        fig.add_trace(go.Scatter(
            x=[pt[0] for pt in route], y=[pt[1] for pt in route],
            mode="lines", name=f"{name} planned route", line=dict(dash="dot"),
            hovertemplate="East: %{x:.1f} km<br>North: %{y:.1f} km<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=[pt[0] for pt in traveled], y=[pt[1] for pt in traveled],
            mode="lines+markers", name=f"{name} simulated progress",
            hovertemplate="East: %{x:.1f} km<br>North: %{y:.1f} km<extra></extra>",
        ))
        latest = traveled[-1]
        fig.add_annotation(x=latest[0], y=latest[1], text=name,
                           showarrow=True, arrowhead=2, ax=0,
                           ay=-35 if name == "Stork VTOL" else 35)
    fig.add_trace(go.Scatter(x=[0], y=[0], mode="markers", name="Demo ground station",
                             marker=dict(symbol="diamond", size=15)))
    fig.update_layout(
        title="Illustrative UAV positions and routes (DEMO)",
        xaxis_title="East / West (km from demo station)",
        yaxis_title="North / South (km from demo station)",
        legend=dict(orientation="h", y=-0.3),
        height=480, margin=dict(l=15, r=15, t=60, b=55),
    )
    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Illustrative local XY route only — NOT GPS, actual aircraft tracking, or MATLAB telemetry. "
               "NEXT STEP advances both demo routes; RESET returns them to the station.")


def reset():
    st.session_state.demo = {
        "index": 0, "time": 0, "running": False, "decision": None,
        "status": "READY", "history": [],
    }
    record()


def snapshot():
    d = st.session_state.demo
    state = STEPS[d["index"]]
    # All values below are illustrative DEMO data, not hardware telemetry.
    stork_battery = max(0, 100 - d["index"] * 2)
    small_battery = max(0, 90 - d["index"] * 3)
    return {
        "Time_s": d["time"], "MissionState": state,
        "OperatorApproval": 1 if d["decision"] == "APPROVE" else 0,
        "DockReady": 1 if state in (0, 5) else 0,
        "SoC_percent": stork_battery,
        "StorkBattery_percent": stork_battery,
        "StorkConnection": 1, "StorkUAVStatus": int(state in (2, 3, 4)),
        "SmallBattery_percent": small_battery,
        "SmallConnection": 1, "SmallUAVStatus": int(state in (2, 3, 4)),
    }


def record():
    st.session_state.demo["history"].append(snapshot())


def start(decision):
    d = st.session_state.demo
    if decision == "REJECT":
        d.update(running=False, decision="REJECT", status="REJECTED")
        record()
        return
    if d["index"] >= len(STEPS) - 1:
        d.update(running=False, status="FINISHED")
        return
    d.update(running=True, decision="APPROVE", status="RUNNING")
    record()


def advance():
    d = st.session_state.demo
    if not d["running"] or d["decision"] != "APPROVE":
        return
    if d["index"] < len(STEPS) - 1:
        d["index"] += 1
        d["time"] += 30
        record()
    if d["index"] >= len(STEPS) - 1:
        d.update(running=False, status="FINISHED")


def run_demo():
    while st.session_state.demo["running"]:
        advance()


def load_csv_bundle(file):
    raw = file.getvalue()
    if file.name.lower().endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            csv_names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
            if not csv_names:
                raise ValueError("ZIP file contains no CSV files.")
            parts = []
            for name in csv_names:
                with archive.open(name) as stream:
                    part = pd.read_csv(stream)
                    part["SourceFile"] = Path(name).name
                    parts.append(part)
            return pd.concat(parts, ignore_index=True)
    return pd.read_csv(io.BytesIO(raw))


def last_value(df, names):
    for name in names:
        if name in df.columns:
            s = pd.to_numeric(df[name], errors="coerce").dropna()
            if not s.empty:
                return float(s.iloc[-1])
    return None


def metric_value(val, suffix=""):
    return "—" if val is None else f"{val:.1f}{suffix}" if suffix else str(int(round(val)))


if "demo" not in st.session_state:
    reset()

st.title("MIRQAB | GROUND CONTROL")
st.caption("Ground Layer • Stork VTOL + Small UAV")
st.warning("DEMO CONTROL: Buttons operate a Python mission simulation only. They do NOT control Simulink or real aircraft.")

with st.sidebar:
    st.header("Control Center")
    mode = st.radio("Mode", ["Interactive demo", "MATLAB CSV viewer"], index=0)

if mode == "Interactive demo":
    d = st.session_state.demo
    with st.sidebar:
        decision = st.radio("Operator decision", ["APPROVE", "REJECT"], horizontal=True,
                            help="Choose before START. REJECT aborts the demo mission.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("▶ START", use_container_width=True, disabled=d["running"] or d["status"] == "FINISHED"):
                start(decision)
        with c2:
            if st.button("■ STOP", use_container_width=True, disabled=not d["running"]):
                d["running"] = False
                d["status"] = "STOPPED"
        c3, c4 = st.columns(2)
        with c3:
            if st.button("NEXT STEP", use_container_width=True, disabled=not d["running"]):
                advance()
        with c4:
            if st.button("RUN DEMO", use_container_width=True, disabled=not d["running"]):
                run_demo()
        if st.button("↺ RESET MISSION", use_container_width=True):
            reset()
        st.caption("NEXT STEP advances 30 seconds. RUN DEMO completes the simulated mission instantly.")

    d = st.session_state.demo
    current = snapshot()
    st.subheader("Mission overview — simulated data")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Mission state", f"{current['MissionState']} · {STATES[current['MissionState']]}")
    k2.metric("Control status", d["status"])
    k3.metric("Dock readiness", current["DockReady"])
    k4.metric("Elapsed time", f"{d['time']} s")
    if d["status"] == "REJECTED":
        st.error("Operator REJECT: demo mission was not started.")
    elif d["status"] == "FINISHED":
        st.success("Demo mission completed: LAND (state 5).")
    elif d["status"] == "RUNNING":
        st.info("Mission is running. Select NEXT STEP or RUN DEMO to progress.")

    st.subheader("Ground stations — simulated data")
    a, b = st.columns(2)
    with a:
        st.markdown("#### Stork VTOL")
        x, y, z = st.columns(3)
        x.metric("Battery", f"{current['StorkBattery_percent']}%")
        y.metric("Connection", "Connected")
        z.metric("UAV status", "In flight" if current["StorkUAVStatus"] else "On ground")
    with b:
        st.markdown("#### Small UAV")
        x, y, z = st.columns(3)
        x.metric("Battery", f"{current['SmallBattery_percent']}%")
        y.metric("Connection", "Connected")
        z.metric("UAV status", "In flight" if current["SmallUAVStatus"] else "On ground")
    st.subheader("Aircraft locations & routes — DEMO")
    show_demo_routes(d["index"])
    df = pd.DataFrame(d["history"])
    st.subheader("Mission telemetry — DEMO")
    selected = st.selectbox("Signal", [c for c in df.select_dtypes(include="number").columns if c != "Time_s"])
    fig = px.line(df, x="Time_s", y=selected, markers=True, title=f"{selected} (simulated)")
    if selected in ("MissionState", "DockReady", "OperatorApproval"):
        fig.update_traces(line_shape="hv")
    st.plotly_chart(fig, use_container_width=True)
    st.download_button("Download DEMO CSV", df.to_csv(index=False).encode("utf-8"),
                       "MIRQAB_Demo_Results.csv", "text/csv")
    st.caption("Simulation values are illustrative, not validated MATLAB telemetry. Demo state is session-local and resets on server/session restart.")
else:
    with st.sidebar:
        uploaded = st.file_uploader("Upload MIRQAB_Telemetry.csv / .zip", type=["csv", "zip"])
        st.caption("Data exported from MATLAB Online. Read-only viewer; no remote control.")
    if uploaded is None:
        st.info("Upload the CSV exported from MATLAB to see recorded simulation results.")
    else:
        try:
            df = load_csv_bundle(uploaded)
            st.success(f"Loaded MATLAB telemetry: {len(df):,} rows")
            st.subheader("Mission overview — imported MATLAB data")
            mission = last_value(df, ["MissionState", "mirqabMissionForMetrics"])
            dock = last_value(df, ["DockReady", "mirqabDockReady"])
            soc = last_value(df, ["SoC_percent", "SoC", "out_SoC"])
            approval = last_value(df, ["OperatorApproval", "mirqabOperatorApproval"])
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Mission state", metric_value(mission))
            k2.metric("Dock readiness", metric_value(dock))
            k3.metric("Battery SoC", metric_value(soc, "%"))
            k4.metric("Operator approval", metric_value(approval))
            st.subheader("Ground stations — imported MATLAB data")
            a, b = st.columns(2)
            with a:
                st.markdown("#### Stork VTOL")
                st.metric("Battery", metric_value(last_value(df, ["StorkBattery_percent"]), "%"))
                st.metric("Connection", metric_value(last_value(df, ["StorkConnection"])))
                st.metric("UAV status", metric_value(last_value(df, ["StorkUAVStatus"])))
            with b:
                st.markdown("#### Small UAV")
                st.metric("Battery", metric_value(last_value(df, ["SmallBattery_percent"]), "%"))
                st.metric("Connection", metric_value(last_value(df, ["SmallConnection"])))
                st.metric("UAV status", metric_value(last_value(df, ["SmallUAVStatus"])))
            st.subheader("Telemetry charts")
            time_col = next((c for c in ("Time_s", "Time", "time") if c in df.columns), None)
            numeric_cols = [c for c in df.select_dtypes(include="number").columns if c != time_col]
            if numeric_cols:
                signal = st.selectbox("Signal", numeric_cols)
                chart = px.line(df, x=time_col, y=signal, title=signal) if time_col else px.line(df, y=signal, title=signal)
                if signal in ("MissionState", "DockReady", "OperatorApproval"):
                    chart.update_traces(line_shape="hv")
                st.plotly_chart(chart, use_container_width=True)
            else:
                st.info("No numeric signal columns found.")
            st.subheader("Alerts")
            alerts = []
            for label, batt, conn in [
                ("Stork VTOL", "StorkBattery_percent", "StorkConnection"),
                ("Small UAV", "SmallBattery_percent", "SmallConnection"),
            ]:
                bval = last_value(df, [batt])
                cval = last_value(df, [conn])
                if bval is not None and bval < 20:
                    alerts.append(f"LOW BATTERY: {label}")
                if cval is not None and cval < 0.5:
                    alerts.append(f"CONNECTION LOST: {label}")
            if alerts:
                for msg in alerts:
                    st.error(msg)
            else:
                st.success("No alert condition detected in this uploaded telemetry.")
            with st.expander("View imported data"):
                st.dataframe(df, use_container_width=True)
            st.download_button("Download imported data", df.to_csv(index=False).encode("utf-8"),
                               "MIRQAB_Telemetry_copy.csv", "text/csv")
        except Exception as exc:
            st.error(f"Could not read uploaded data: {exc}")

st.divider()
st.caption("MIRQAB Ground Layer | Interactive Python demo + read-only MATLAB telemetry viewer")

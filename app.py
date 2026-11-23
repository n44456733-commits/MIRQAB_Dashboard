import io
import zipfile
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="MIRQAB Ground Control", page_icon="🛩️", layout="wide")

st.title("MIRQAB | GROUND CONTROL")
st.caption("Ground Layer telemetry viewer · MATLAB / Simulink results")
st.info(
    "This Python dashboard displays exported MATLAB/Simulink telemetry. "
    "It does not start Simulink or send live commands to the model from the iPad."
)

with st.sidebar:
    st.header("Data import")
    uploaded = st.file_uploader(
        "Upload MIRQAB_Telemetry.csv or MIRQAB_Telemetry.zip",
        type=["csv", "zip"],
    )
    st.caption("Generate the export using Export_MIRQAB_Telemetry.m in MATLAB Online.")


def load_csv_bundle(file):
    if file is None:
        return None
    raw = file.getvalue()
    if file.name.lower().endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            csv_names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
            if not csv_names:
                raise ValueError("ZIP file contains no CSV files.")
            frames = []
            for name in csv_names:
                with archive.open(name) as stream:
                    part = pd.read_csv(stream)
                    part["SourceFile"] = Path(name).name
                    frames.append(part)
            return pd.concat(frames, ignore_index=True, sort=False)
    return pd.read_csv(io.BytesIO(raw))


def first_value(df, candidates, default=float("nan")):
    for col in candidates:
        if col in df.columns:
            values = pd.to_numeric(df[col], errors="coerce").dropna()
            if not values.empty:
                return float(values.iloc[-1])
    return default


if uploaded is None:
    st.subheader("Ground Stations")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Stork VTOL")
        st.metric("Telemetry", "Awaiting CSV")
    with c2:
        st.markdown("#### Small UAV")
        st.metric("Telemetry", "Awaiting CSV")
    st.warning("No simulation file uploaded. The dashboard is ready; upload the CSV exported from MATLAB to display real results.")
    st.subheader("Mission states")
    st.write({0: "WAIT", 1: "PREPARE", 2: "TAKEOFF", 3: "EXECUTE", 4: "RETURN", 5: "LAND"})
else:
    try:
        df = load_csv_bundle(uploaded)
        st.success(f"Loaded telemetry: {len(df):,} rows")

        # Normalize likely signal column names from the MATLAB export.
        time_col = next((c for c in ["Time_s", "Time", "time"] if c in df.columns), None)
        if time_col:
            df[time_col] = pd.to_numeric(df[time_col], errors="coerce")

        st.subheader("Mission overview")
        mission = first_value(df, ["MissionState", "mirqabMissionForMetrics"])
        dock = first_value(df, ["DockReady", "mirqabDockReady"])
        soc = first_value(df, ["SoC_percent", "SoC", "out_SoC"])
        approval = first_value(df, ["OperatorApproval", "mirqabOperatorApproval"])
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Mission state", "—" if pd.isna(mission) else int(round(mission)))
        k2.metric("Dock readiness", "—" if pd.isna(dock) else int(round(dock)))
        k3.metric("Battery SoC", "—" if pd.isna(soc) else f"{soc:.1f}%")
        k4.metric("Operator approval", "—" if pd.isna(approval) else int(round(approval)))

        st.subheader("Ground stations")
        a, b = st.columns(2)
        station_fields = [
            ("Stork VTOL", "StorkBattery_percent", "StorkConnection", "StorkUAVStatus"),
            ("Small UAV", "SmallBattery_percent", "SmallConnection", "SmallUAVStatus"),
        ]
        for col, (title, batt, conn, status) in zip((a, b), station_fields):
            with col:
                st.markdown(f"#### {title}")
                x, y, z = st.columns(3)
                x.metric("Battery", f"{first_value(df, [batt]):.1f}%" if batt in df else "—")
                y.metric("Connection", f"{int(first_value(df, [conn]))}" if conn in df else "—")
                z.metric("UAV status", f"{int(first_value(df, [status]))}" if status in df else "—")

        st.subheader("Telemetry charts")
        numeric = df.select_dtypes(include="number")
        chart_cols = [c for c in numeric.columns if c != time_col]
        if chart_cols:
            selected = st.selectbox("Signal", chart_cols)
            if time_col:
                chart = px.line(df, x=time_col, y=selected, title=selected)
            else:
                chart = px.line(df, y=selected, title=selected)
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.info("No numeric telemetry columns found in this file.")

        st.subheader("Alerts")
        alerts = []
        for label, batt, conn in [
            ("Stork VTOL", "StorkBattery_percent", "StorkConnection"),
            ("Small UAV", "SmallBattery_percent", "SmallConnection"),
        ]:
            battery_value = first_value(df, [batt])
            connection_value = first_value(df, [conn])
            if not pd.isna(battery_value) and battery_value < 20:
                alerts.append(f"LOW BATTERY: {label}")
            if not pd.isna(connection_value) and connection_value < 0.5:
                alerts.append(f"CONNECTION LOST: {label}")
        if alerts:
            for alert in alerts:
                st.error(alert)
        else:
            st.success("No alert condition detected in the uploaded telemetry.")

        with st.expander("View imported data"):
            st.dataframe(df, use_container_width=True)

        st.download_button(
            "Download imported data as CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="MIRQAB_Telemetry_copy.csv",
            mime="text/csv",
        )
    except Exception as exc:
        st.error(f"Could not read the uploaded telemetry: {exc}")

st.divider()
st.caption("MIRQAB Ground Layer · Python dashboard for exported simulation telemetry")

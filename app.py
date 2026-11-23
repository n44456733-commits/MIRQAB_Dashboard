import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
page_title="MIRQAB Ground Control",
page_icon="🛩️",
layout="wide"
)

st.title("MIRQAB | GROUND CONTROL")
st.caption("Python Dashboard — MATLAB / Simulink")

st.sidebar.header("Mission Control")

approval = st.sidebar.selectbox(
"Operator Approval",
["REJECT (0)", "APPROVE (1)"]
)

st.sidebar.info(
"MATLAB simulation control is not connected yet."
)

st.subheader("Ground Stations")

a, b = st.columns(2)

with a:
    st.markdown("### Stork VTOL")
    st.info("Waiting for MATLAB telemetry")

with b:
    st.markdown("### Small UAV")
    st.info("Waiting for MATLAB telemetry")

st.subheader("Simulation Results")

file = st.file_uploader(
"Upload MATLAB simulation results (CSV)",
type=["csv"]
)

if file is not None:
    try:
        df = pd.read_csv(file)
        st.success("Simulation data loaded successfully")
        st.dataframe(df, use_container_width=True)

        numeric = df.select_dtypes(include="number")

        if not numeric.empty:
            selected = st.selectbox(
            "Choose a signal",
            numeric.columns.tolist()
        )
        st.plotly_chart(
            px.line(
                df,
                y=selected,
                title=selected
            ),
            use_container_width=True
        )

except Exception as e:
    st.error(f"Cannot read data: {e}")
    else:    st.warning("Upload real simulation data to view results.")

st.subheader("Mission States")

states = {
0: "WAIT",
1: "PREPARE",
2: "TAKEOFF",
3: "EXECUTE",
4: "RETURN",
5: "LAND"
}

st.write(states)

st.subheader("Alerts & Performance")
st.info("Metrics and alerts will appear after MATLAB integration.")

st.divider()
st.caption("MIRQAB Ground Layer | Python Control Dashboard")

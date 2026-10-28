import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ------------------------------------------------------------
# Solar PV Analytics Dashboard
# Research question:
# How are solar irradiation and module temperature related to
# photovoltaic power output?
# ------------------------------------------------------------

st.set_page_config(
    page_title="Solar PV Analytics Dashboard",
    page_icon="☀️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Theme colours
BG = "#101827"
CARD = "#1C2940"
GREEN = "#20C997"
BLUE = "#48A9E6"
GOLD = "#F4C95D"
TEXT = "#F4F7FB"
MUTED = "#A7B3C7"

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: {BG}; color: {TEXT}; }}
    [data-testid="stSidebar"] {{ background-color: {CARD}; }}
    h1, h2, h3, p, label {{ color: {TEXT}; }}
    div[data-testid="stMetric"] {{
        background-color: {CARD};
        border: 1px solid #33415c;
        padding: 16px 18px;
        border-radius: 12px;
    }}
    div[data-testid="stMetricLabel"] p {{ color: {MUTED} !important; }}
    div[data-testid="stMetricValue"] {{ color: {TEXT} !important; }}
    .subtitle {{ color: {MUTED}; font-size: 1rem; }}
    .note {{ color: {MUTED}; font-size: 0.85rem; }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("☀️ Solar PV Performance Dashboard")
st.markdown(
    '<div class="subtitle">Exploratory analysis of solar irradiation, module temperature, and photovoltaic power output.</div>',
    unsafe_allow_html=True,
)
st.markdown("")

# ---- Load data: use repository CSV if present, otherwise allow upload ----
@st.cache_data
def read_csv(file_or_path):
    return pd.read_csv(file_or_path)

uploaded_file = st.sidebar.file_uploader(
    "Upload SolarPV_Cleaned_Data.csv", type=["csv"]
)
default_path = Path(__file__).parent / "SolarPV_Cleaned_Data.csv"

try:
    if uploaded_file is not None:
        raw_df = read_csv(uploaded_file)
        data_source = "Uploaded CSV"
    elif default_path.exists():
        raw_df = read_csv(default_path)
        data_source = "CSV included with the app"
    else:
        st.info(
            "Upload SolarPV_Cleaned_Data.csv in the sidebar, or add the CSV file "
            "to the same GitHub repository as app.py."
        )
        st.stop()
except Exception as exc:
    st.error(f"The CSV file could not be read: {exc}")
    st.stop()

# ---- Check and prepare expected columns ----
required = ["AC_POWER", "IRRADIATION", "MODULE_TEMPERATURE"]
missing = [col for col in required if col not in raw_df.columns]
if missing:
    st.error(
        "The dataset is missing required column(s): "
        + ", ".join(missing)
        + ". Please check the CSV column names."
    )
    st.stop()

df = raw_df.copy()

if "DATE_TIME" in df.columns:
    df["DATE_TIME"] = pd.to_datetime(df["DATE_TIME"], errors="coerce")
else:
    st.warning("DATE_TIME was not found. Time-based charts and date filters will be unavailable.")

numeric_candidates = [
    "DC_POWER", "AC_POWER", "DAILY_YIELD", "TOTAL_YIELD",
    "AMBIENT_TEMPERATURE", "MODULE_TEMPERATURE", "IRRADIATION",
    "Hour", "Month", "Day", "Year"
]
for col in numeric_candidates:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

if "DATE_TIME" in df.columns:
    df = df.dropna(subset=["DATE_TIME"])
    if "Hour" not in df.columns:
        df["Hour"] = df["DATE_TIME"].dt.hour
    if "Month" not in df.columns:
        df["Month"] = df["DATE_TIME"].dt.month
    if "Day" not in df.columns:
        df["Day"] = df["DATE_TIME"].dt.day
    if "Year" not in df.columns:
        df["Year"] = df["DATE_TIME"].dt.year
    df["Date"] = df["DATE_TIME"].dt.date

# Remove rows without the main values needed for the central question.
df = df.dropna(subset=["AC_POWER", "IRRADIATION", "MODULE_TEMPERATURE"])
if df.empty:
    st.error("No usable rows remain after checking AC_POWER, IRRADIATION, and MODULE_TEMPERATURE.")
    st.stop()

# ---- Sidebar filters ----
st.sidebar.header("Dashboard filters")
filtered = df.copy()

if "PLANT_ID" in filtered.columns:
    plant_values = sorted(filtered["PLANT_ID"].dropna().unique().tolist(), key=str)
    if plant_values:
        chosen_plants = st.sidebar.multiselect(
            "Plant ID", plant_values, default=plant_values
        )
        if chosen_plants:
            filtered = filtered[filtered["PLANT_ID"].isin(chosen_plants)]
        else:
            st.warning("Select at least one plant.")
            st.stop()

if "DATE_TIME" in filtered.columns and not filtered.empty:
    min_date = filtered["DATE_TIME"].min().date()
    max_date = filtered["DATE_TIME"].max().date()
    date_range = st.sidebar.date_input(
        "Date range", value=(min_date, max_date), min_value=min_date, max_value=max_date
    )
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start_date, end_date = date_range
        filtered = filtered[
            (filtered["DATE_TIME"].dt.date >= start_date)
            & (filtered["DATE_TIME"].dt.date <= end_date)
        ]

if "DATE_TIME" in filtered.columns and not filtered.empty:
    hours = st.sidebar.slider("Hours of day", 0, 23, (0, 23))
    filtered = filtered[
        filtered["DATE_TIME"].dt.hour.between(hours[0], hours[1])
    ]

if filtered.empty:
    st.warning("No rows match the selected filters. Adjust the filters in the sidebar.")
    st.stop()

# ---- Summary / data-quality notes ----
date_text = "Date/time unavailable"
if "DATE_TIME" in filtered.columns:
    date_text = (
        f"{filtered['DATE_TIME'].min():%d %b %Y} – "
        f"{filtered['DATE_TIME'].max():%d %b %Y}"
    )

st.caption(f"Data source: {data_source}  •  Records shown: {len(filtered):,}  •  Period: {date_text}")

# KPI values are descriptive statistics, not energy totals.
c1, c2, c3, c4 = st.columns(4)
c1.metric("Records analysed", f"{len(filtered):,}")
c2.metric("Mean AC power", f"{filtered['AC_POWER'].mean():,.2f}")
c3.metric("Mean irradiation", f"{filtered['IRRADIATION'].mean():,.3f}")
c4.metric("Mean module temperature", f"{filtered['MODULE_TEMPERATURE'].mean():,.2f} °C")

st.markdown("---")

# ---- Tabs keep the dashboard organised ----
tab1, tab2, tab3, tab4 = st.tabs(
    ["Overview", "Irradiation & Power", "Temperature & Power", "Data details"]
)

def apply_dark_layout(fig, height=390):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG,
        plot_bgcolor=CARD,
        font=dict(color=TEXT),
        height=height,
        margin=dict(l=25, r=20, t=65, b=35),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    fig.update_xaxes(gridcolor="#33415c", zerolinecolor="#33415c")
    fig.update_yaxes(gridcolor="#33415c", zerolinecolor="#33415c")
    return fig

with tab1:
    left, right = st.columns(2)

    with left:
        if "DATE_TIME" in filtered.columns:
            # Use a line chart for records over time. Sampling can be large, so cap points.
            ts = filtered.sort_values("DATE_TIME")
            if len(ts) > 5000:
                step = max(1, len(ts) // 5000)
                ts = ts.iloc[::step]
            fig_time = px.line(
                ts, x="DATE_TIME", y="AC_POWER",
                title="AC power output over time",
                labels={"DATE_TIME": "Date and time", "AC_POWER": "AC power (dataset units)"},
            )
            fig_time.update_traces(line=dict(color=GREEN, width=1.5))
            st.plotly_chart(apply_dark_layout(fig_time), use_container_width=True)
        else:
            st.info("A DATE_TIME column is needed for the time-series chart.")

    with right:
        if "Hour" in filtered.columns:
            hourly = filtered.groupby("Hour", as_index=False)["AC_POWER"].mean()
            fig_hour = px.line(
                hourly, x="Hour", y="AC_POWER", markers=True,
                title="Average AC power by hour of day",
                labels={"Hour": "Hour of day", "AC_POWER": "Mean AC power (dataset units)"},
            )
            fig_hour.update_traces(line=dict(color=BLUE, width=3))
            fig_hour.update_xaxes(dtick=2)
            st.plotly_chart(apply_dark_layout(fig_hour), use_container_width=True)
        else:
            st.info("An Hour column or valid DATE_TIME values are needed for the hourly profile.")

    left, right = st.columns(2)
    with left:
        fig_irr = px.scatter(
            filtered, x="IRRADIATION", y="AC_POWER",
            title="Irradiation and AC power",
            labels={"IRRADIATION": "Solar irradiation (dataset units)", "AC_POWER": "AC power (dataset units)"},
            opacity=0.55,
            trendline="ols" if len(filtered) >= 3 else None,
        )
        fig_irr.update_traces(marker=dict(color=GOLD, size=6))
        st.plotly_chart(apply_dark_layout(fig_irr), use_container_width=True)

    with right:
        fig_temp = px.scatter(
            filtered, x="MODULE_TEMPERATURE", y="AC_POWER",
            title="Module temperature and AC power",
            labels={"MODULE_TEMPERATURE": "Module temperature (°C)", "AC_POWER": "AC power (dataset units)"},
            opacity=0.55,
            trendline="ols" if len(filtered) >= 3 else None,
        )
        fig_temp.update_traces(marker=dict(color=BLUE, size=6))
        st.plotly_chart(apply_dark_layout(fig_temp), use_container_width=True)

with tab2:
    st.subheader("How does solar irradiation relate to AC power?")
    st.markdown(
        "Use the scatter plot to inspect the relationship. The fitted line summarises the overall linear trend; "
        "it does not prove that irradiation is the only factor affecting output."
    )
    scatter_df = filtered.copy()
    if len(scatter_df) > 12000:
        scatter_df = scatter_df.sample(12000, random_state=42)
    fig = px.scatter(
        scatter_df, x="IRRADIATION", y="AC_POWER",
        title="Solar irradiation vs AC power",
        labels={"IRRADIATION": "Solar irradiation (dataset units)", "AC_POWER": "AC power (dataset units)"},
        opacity=0.5, trendline="ols" if len(scatter_df) >= 3 else None,
    )
    fig.update_traces(marker=dict(color=GOLD, size=7))
    st.plotly_chart(apply_dark_layout(fig, 480), use_container_width=True)

    # Compare mean output across irradiation groups, using quantile bins when possible.
    try:
        group_df = filtered[["IRRADIATION", "AC_POWER"]].dropna().copy()
        if group_df["IRRADIATION"].nunique() >= 4:
            group_df["Irradiation group"] = pd.qcut(
                group_df["IRRADIATION"], q=4, duplicates="drop"
            ).astype(str)
            summary = group_df.groupby("Irradiation group", observed=False)["AC_POWER"].agg(
                ["mean", "median", "count"]
            ).reset_index()
            fig_group = px.bar(
                summary, x="Irradiation group", y="mean",
                title="Mean AC power across irradiation groups",
                labels={"Irradiation group": "Irradiation group", "mean": "Mean AC power (dataset units)"},
                text_auto=".2f",
            )
            fig_group.update_traces(marker_color=GREEN)
            st.plotly_chart(apply_dark_layout(fig_group, 380), use_container_width=True)
        else:
            st.info("There are too few distinct irradiation values to create meaningful groups.")
    except Exception:
        st.info("Irradiation groups could not be created for the selected data.")

with tab3:
    st.subheader("How does module temperature relate to AC power?")
    left, right = st.columns(2)
    with left:
        temp_df = filtered.copy()
        if len(temp_df) > 12000:
            temp_df = temp_df.sample(12000, random_state=42)
        fig = px.scatter(
            temp_df, x="MODULE_TEMPERATURE", y="AC_POWER",
            title="Module temperature vs AC power",
            labels={"MODULE_TEMPERATURE": "Module temperature (°C)", "AC_POWER": "AC power (dataset units)"},
            opacity=0.5, trendline="ols" if len(temp_df) >= 3 else None,
        )
        fig.update_traces(marker=dict(color=BLUE, size=7))
        st.plotly_chart(apply_dark_layout(fig, 430), use_container_width=True)

    with right:
        if "AMBIENT_TEMPERATURE" in filtered.columns:
            fig = px.scatter(
                filtered, x="AMBIENT_TEMPERATURE", y="MODULE_TEMPERATURE",
                title="Ambient and module temperature",
                labels={"AMBIENT_TEMPERATURE": "Ambient temperature (°C)", "MODULE_TEMPERATURE": "Module temperature (°C)"},
                opacity=0.55,
            )
            fig.update_traces(marker=dict(color=GREEN, size=6))
            st.plotly_chart(apply_dark_layout(fig, 430), use_container_width=True)
        else:
            st.info("AMBIENT_TEMPERATURE is not available in this dataset.")

    # Correlation heatmap for selected numeric variables
    numeric_cols = [
        c for c in [
            "DC_POWER", "AC_POWER", "DAILY_YIELD", "TOTAL_YIELD",
            "AMBIENT_TEMPERATURE", "MODULE_TEMPERATURE", "IRRADIATION"
        ] if c in filtered.columns
    ]
    corr = filtered[numeric_cols].corr(numeric_only=True)
    fig_corr = px.imshow(
        corr, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r",
        zmin=-1, zmax=1, title="Correlation between numeric variables",
    )
    st.plotly_chart(apply_dark_layout(fig_corr, 470), use_container_width=True)

with tab4:
    st.subheader("Dataset overview")
    a, b, c = st.columns(3)
    a.metric("Rows in original dataset", f"{len(raw_df):,}")
    b.metric("Columns", f"{raw_df.shape[1]:,}")
    c.metric("Missing values in filtered data", f"{int(filtered.isna().sum().sum()):,}")

    st.markdown("**Preview of filtered data**")
    st.dataframe(filtered.head(100), use_container_width=True)

    with st.expander("Show descriptive statistics"):
        st.dataframe(filtered.describe(include="all").transpose(), use_container_width=True)

    with st.expander("Show missing values by column in original data"):
        missing_table = raw_df.isna().sum().rename("Missing values").to_frame()
        missing_table["Missing (%)"] = (missing_table["Missing values"] / max(len(raw_df), 1) * 100).round(2)
        st.dataframe(missing_table, use_container_width=True)

st.markdown("---")
st.markdown(
    '<div class="note">Interpretation note: this dashboard is exploratory. Confirm the dataset units and sampling interval before reporting energy totals. '
    'The current dataset covers only the dates present in the CSV, so findings should not be generalised to a full year unless additional data are available.</div>',
    unsafe_allow_html=True,
)

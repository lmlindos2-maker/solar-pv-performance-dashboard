from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# --------------------------------------------------
# 1. PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Solar PV Performance Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)


# --------------------------------------------------
# 2. DASHBOARD STYLING
# --------------------------------------------------

st.markdown(
    """
    <style>
        .main {
            background-color: #F7F9FC;
        }

        h1, h2, h3 {
            color: #17324D;
        }

        div[data-testid="stMetric"] {
            background-color: #F0F2F6;
            border: 1px solid #DCE3EB;
            padding: 16px;
            border-radius: 10px;
        }

        div[data-testid="stMetricValue"] {
            color: #0284C7;
            font-size: 1.6rem;   /* reduced KPI value size */
            line-height: 1.2;
        }

        .section-note {
            color: #526477;
            font-size: 14px;
        }
    </style>
    """,
    unsafe_allow_html=True
)


# --------------------------------------------------
# 3. DATA LOADING AND CLEANING
# --------------------------------------------------

REQUIRED_COLUMNS = [
    "DATE_TIME",
    "AC_POWER",
    "IRRADIATION",
    "MODULE_TEMPERATURE"
]


@st.cache_data
def load_data(file_bytes=None, local_file=None):

    if file_bytes is not None:
        from io import BytesIO
        data = pd.read_csv(BytesIO(file_bytes))

    elif local_file is not None:
        data = pd.read_csv(local_file)

    else:
        raise FileNotFoundError(
            "No CSV file was supplied."
        )

    # Remove spaces from column names
    data.columns = data.columns.str.strip()

    # Check required columns
    missing_columns = [
        col for col in REQUIRED_COLUMNS
        if col not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            "The dataset is missing these required columns: "
            + ", ".join(missing_columns)
        )

    # Convert timestamp
    data["DATE_TIME"] = pd.to_datetime(
        data["DATE_TIME"],
        errors="coerce"
    )

    # Convert measurements to numeric values
    numeric_columns = [
        "AC_POWER",
        "IRRADIATION",
        "MODULE_TEMPERATURE"
    ]

    for column in numeric_columns:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce"
        )

    # Remove rows without essential information
    data = data.dropna(
        subset=REQUIRED_COLUMNS
    ).copy()

    # Remove impossible negative measurements
    # This assumes the dataset represents non-negative
    # PV output and non-negative solar irradiation.
    data = data[
        (data["AC_POWER"] >= 0)
        & (data["IRRADIATION"] >= 0)
    ].copy()

    # Create time-based variables
    data["Date"] = data["DATE_TIME"].dt.date
    data["Hour"] = data["DATE_TIME"].dt.hour
    data["Month"] = data["DATE_TIME"].dt.strftime("%B")

    return data


# --------------------------------------------------
# 4. DASHBOARD HEADER
# --------------------------------------------------

st.title("Solar PV Performance Analysis Dashboard")

st.markdown(
    """
    This dashboard explores PV system performance
    by examining solar irradiation, module temperature and
    AC power output
    """
)

st.info(
    "**Research question:** How are solar irradiation and "
    "module temperature related to PV power output?"
)

# --------------------------------------------------
# 5. LOAD THE DATASET (NO UPLOAD OPTION)
# --------------------------------------------------

st.sidebar.header("Dashboard Filters")

@st.cache_data
def load_data(file_path):
    data = pd.read_csv(file_path)

    data.columns = data.columns.str.strip()

    missing_columns = [
        col for col in REQUIRED_COLUMNS
        if col not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(missing_columns)
        )

    data["DATE_TIME"] = pd.to_datetime(
        data["DATE_TIME"],
        errors="coerce"
    )

    for column in [
        "AC_POWER",
        "IRRADIATION",
        "MODULE_TEMPERATURE"
    ]:
        data[column] = pd.to_numeric(
            data[column],
            errors="coerce"
        )

    data = data.dropna(
        subset=REQUIRED_COLUMNS
    ).copy()

    data = data[
        (data["AC_POWER"] >= 0)
        & (data["IRRADIATION"] >= 0)
    ].copy()

    data["Date"] = data["DATE_TIME"].dt.date
    data["Hour"] = data["DATE_TIME"].dt.hour
    data["Month"] = data["DATE_TIME"].dt.strftime("%B")

    return data


# Load CSV from the same folder as app.py
csv_path = Path(__file__).parent / "SolarPV_Cleaned_Data.csv"

try:
    if not csv_path.exists():
        st.error(
            "SolarPV_Cleaned_Data.csv was not found. "
            "Please add the dataset to the same folder as app.py."
        )
        st.stop()

    df = load_data(str(csv_path))

except Exception as error:
    st.error(f"Unable to load the dataset: {error}")
    st.stop()


if df.empty:
    st.error("No valid records remain after data cleaning.")
    st.stop()


# --------------------------------------------------
# 6. INTERACTIVE FILTERS
# --------------------------------------------------

min_date = df["DATE_TIME"].min().date()
max_date = df["DATE_TIME"].max().date()

date_selection = st.sidebar.date_input(
    "Select date range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

if isinstance(date_selection, (tuple, list)):
    if len(date_selection) == 2:
        start_date, end_date = date_selection
    elif len(date_selection) == 1:
        start_date = end_date = date_selection[0]
    else:
        start_date, end_date = min_date, max_date
else:
    start_date = end_date = date_selection


available_months = (
    df.sort_values("DATE_TIME")["Month"].drop_duplicates().tolist()
)

selected_months = st.sidebar.multiselect(
    "Select month",
    options=available_months,
    default=available_months
)

hour_selection = st.sidebar.slider(
    "Select hours of the day",
    min_value=0,
    max_value=23,
    value=(0, 23)
)

filtered_df = df[
    (df["DATE_TIME"].dt.date >= start_date)
    & (df["DATE_TIME"].dt.date <= end_date)
    & (df["Month"].isin(selected_months))
    & (df["Hour"] >= hour_selection[0])
    & (df["Hour"] <= hour_selection[1])
].copy()


if filtered_df.empty:
    st.warning(
        "No records match the selected filters. "
        "Please change your selections."
    )
    st.stop()

# --------------------------------------------------
# 7. KEY PERFORMANCE INDICATORS
# --------------------------------------------------

st.subheader("Key Performance Indicators")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Average AC Power",
    f"{filtered_df['AC_POWER'].mean():,.3f} kW"
)

col2.metric(
    "Peak AC Power",
    f"{filtered_df['AC_POWER'].max():,.3f} kW"
)

col3.metric(
    "Average Irradiation",
    f"{filtered_df['IRRADIATION'].mean():,.3f} W/m²"
)

col4.metric(
    "Average Module Temperature",
    f"{filtered_df['MODULE_TEMPERATURE'].mean():,.2f} °C"
)

st.divider()


# --------------------------------------------------
# 8. DASHBOARD TABS
# --------------------------------------------------

overview_tab, irradiation_tab, temperature_tab, data_tab = st.tabs(
    [
        "Overview",
        "Irradiation and Power",
        "Temperature and Power",
        "Data Quality"
    ]
)


# --------------------------------------------------
# 9. OVERVIEW
# --------------------------------------------------

with overview_tab:

    st.subheader("AC Power Output Over Time")

    time_df = filtered_df.sort_values("DATE_TIME")

    fig_time = px.line(
        time_df,
        x="DATE_TIME",
        y="AC_POWER",
        title="Photovoltaic AC Power Output Over Time",
        labels={
            "DATE_TIME": "Date and Time",
            "AC_POWER": "AC Power (kW)"
        }
    )

    fig_time.update_layout(
        template="plotly_white",
        hovermode="x unified"
    )

    st.plotly_chart(
        fig_time,
        use_container_width=True
    )

    left, right = st.columns(2)

    with left:
        st.subheader("Average Power by Month")

        monthly_df = (
            filtered_df.groupby("Month", sort=False)["AC_POWER"]
            .mean()
            .reset_index()
        )

        fig_month = px.bar(
            monthly_df,
            x="Month",
            y="AC_POWER",
            title="Average AC Power by Month",
            labels={
                "Month": "Month",
                "AC_POWER": "Average AC Power (kW)"
            },
            text_auto=".3f"
        )

        fig_month.update_layout(
            template="plotly_white"
        )

        st.plotly_chart(
            fig_month,
            use_container_width=True
        )

    with right:
        st.subheader("Average Power by Hour")

        hourly_df = (
            filtered_df.groupby("Hour")["AC_POWER"]
            .mean()
            .reset_index()
        )

        fig_hour = px.line(
            hourly_df,
            x="Hour",
            y="AC_POWER",
            markers=True,
            title="Average Daily Power Profile",
            labels={
                "Hour": "Hour of Day",
                "AC_POWER": "Average AC Power (kW)"
            }
        )

        fig_hour.update_layout(
            template="plotly_white",
            xaxis=dict(dtick=2)
        )

        st.plotly_chart(
            fig_hour,
            use_container_width=True
        )


# --------------------------------------------------
# 10. IRRADIATION AND POWER
# --------------------------------------------------

with irradiation_tab:

    st.subheader("Relationship Between Irradiation and AC Power")

    fig_irradiation = px.scatter(
        filtered_df,
        x="IRRADIATION",
        y="AC_POWER",
        opacity=0.55,
        trendline="ols",
        title="Solar Irradiation vs AC Power Output",
        labels={
            "IRRADIATION": "Irradiation (W/m²)",
            "AC_POWER": "AC Power (kW)"
        },
        hover_data=["DATE_TIME"]
    )

    fig_irradiation.update_layout(
        template="plotly_white"
    )

    st.plotly_chart(
        fig_irradiation,
        use_container_width=True
    )

    correlation = filtered_df[
        ["IRRADIATION", "AC_POWER"]
    ].corr().iloc[0, 1]

    st.metric(
        "Irradiation–Power Correlation",
        f"{correlation:.3f}"
    )

    st.markdown(
        """
        **Interpretation:** A positive correlation indicates that
        higher irradiation is generally associated with higher
        AC power output. Correlation alone does not prove causation.
        """
    )


# --------------------------------------------------
# 11. MODULE TEMPERATURE AND POWER
# --------------------------------------------------

with temperature_tab:

    st.subheader("Relationship Between Module Temperature and AC Power")

    fig_temperature = px.scatter(
        filtered_df,
        x="MODULE_TEMPERATURE",
        y="AC_POWER",
        color="IRRADIATION",
        opacity=0.65,
        title="Module Temperature vs AC Power Output",
        labels={
            "MODULE_TEMPERATURE": "Module Temperature (°C)",
            "AC_POWER": "AC Power (kW)",
            "IRRADIATION": "Irradiation"
        },
        hover_data=["DATE_TIME"]
    )

    fig_temperature.update_layout(
        template="plotly_white"
    )

    st.plotly_chart(
        fig_temperature,
        use_container_width=True
    )

    temperature_correlation = filtered_df[
        ["MODULE_TEMPERATURE", "AC_POWER"]
    ].corr().iloc[0, 1]

    st.metric(
        "Temperature–Power Correlation",
        f"{temperature_correlation:.3f}"
    )

    st.markdown(
        """
        **Interpretation:** This chart shows how AC power varies
        with module temperature. The colour represents irradiation,
        helping distinguish temperature patterns under different
        sunlight conditions. The relationship should not be
        interpreted as a causal effect without further analysis.
        """
    )


# --------------------------------------------------
# 12. DATA QUALITY AND CORRELATION
# --------------------------------------------------

with data_tab:

    st.subheader("Dataset Summary")

    summary_col1, summary_col2, summary_col3 = st.columns(3)

    summary_col1.metric(
        "Usable Records",
        f"{len(df):,}"
    )

    summary_col2.metric(
        "Filtered Records",
        f"{len(filtered_df):,}"
    )

    summary_col3.metric(
        "Date Coverage",
        f"{df['DATE_TIME'].min():%d %b %Y} – "
        f"{df['DATE_TIME'].max():%d %b %Y}"
    )

    st.subheader("Missing Values After Cleaning")

    missing_df = (
        df[REQUIRED_COLUMNS]
        .isna()
        .sum()
        .rename("Missing Values")
        .reset_index()
        .rename(columns={"index": "Variable"})
    )

    st.dataframe(
        missing_df,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("Correlation Between Variables")

    correlation_df = filtered_df[
        [
            "AC_POWER",
            "IRRADIATION",
            "MODULE_TEMPERATURE"
        ]
    ].corr()

    fig_corr = px.imshow(
        correlation_df,
        text_auto=".2f",
        color_continuous_scale="RdBu_r",
        zmin=-1,
        zmax=1,
        aspect="auto",
        title="Correlation Heatmap"
    )

    fig_corr.update_layout(
        template="plotly_white"
    )

    st.plotly_chart(
        fig_corr,
        use_container_width=True
    )


# --------------------------------------------------
# 13. FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "Mazibuko LG 29639387 | Power System Data Analytics | Solar PV Performance Analysis"
)
st.caption(
    "Data source: Solar Power Generation Data, Kaggle, published by Anikannal (2020)."
)

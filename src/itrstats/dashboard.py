from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import altair as alt
from sqlalchemy import create_engine, text

from itrstats.db import DEFAULT_DB_PATH

st.set_page_config(page_title="ITR Stats Dashboard", layout="wide")


def load_data(db_path: Path | str = DEFAULT_DB_PATH) -> pd.DataFrame:
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    with engine.begin() as conn:
        df = pd.read_sql(
            text(
                """
                SELECT *
                FROM snapshots
                """
            ),
            conn,
        )
    return df



def get_latest_provider_date(db_path: Path | str = DEFAULT_DB_PATH) -> str:
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    with engine.begin() as conn:
        return conn.execute(
            text("SELECT MAX(provider_last_updated_raw) FROM snapshots WHERE provider_last_updated_raw IS NOT NULL")
        ).scalar()


def main() -> None:
    st.title("Income Tax e-Portal: Daily Stats")
    st.caption("Data collected daily from the public endpoint.")

    # Load data and get the latest snapshot for each provider date
    all_data = load_data()
    if all_data.empty:
        st.warning("No data yet. Run the collector to ingest a snapshot.")
        st.stop()

    sorted_data = all_data.sort_values(["provider_last_updated_raw", "collected_at"], ascending=[True, False])
    sorted_data["rank"] = sorted_data.groupby("provider_last_updated_raw")['collected_at'].rank(method="first", ascending=False)
    sorted_data["rank"] = sorted_data["rank"].astype(int)
    data = sorted_data[sorted_data["rank"] == 1].drop("rank", axis=1).copy()

    # Convert provider date to datetime and set as index
    data["provider_last_updated_raw"] = pd.to_datetime(data["provider_last_updated_raw"])
    data = data.set_index("provider_last_updated_raw")

    # Reindex to daily frequency to see gaps, and forward-fill cumulative values
    start_date = data.index.min()
    end_date = data.index.max()
    daily_index = pd.date_range(start=start_date, end=end_date, freq="D")
    df = data.reindex(daily_index)

    df["interpolated"] = df["collected_at"].isnull()

    cumulative_cols = [
        "e_verified_returns",
        "total_processed_refund",
        "indv_reg_users",
        "total_aadhar_linked_pan",
    ]
    df[cumulative_cols] = df[cumulative_cols].ffill()
    for col in cumulative_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')


    # Calculate daily changes
    daily_change_cols = {}
    for col in cumulative_cols:
        daily_col_name = f"daily_{col}"
        df[daily_col_name] = df[col].diff().fillna(0)
        daily_change_cols[col] = daily_col_name

    # Calculate pending processing percentage and its daily change
    df["pending_processing_percentage"] = ((df["e_verified_returns"] - df["total_processed_refund"]) / df["e_verified_returns"]).fillna(0)
    daily_change_cols["pending_processing_percentage"] = "daily_pending_processing_percentage"
    df["daily_pending_processing_percentage"] = df["pending_processing_percentage"].diff().fillna(0)

    # Calculate 7-day rolling average of processed refunds
    df["avg_processed_last_7_days"] = df[daily_change_cols["total_processed_refund"]].rolling(window=7, min_periods=1).mean()

    df = df.reset_index().rename(columns={"index": "provider_date"})
    df["weekday"] = df["provider_date"].dt.day_name()

    # Get latest and previous rows for KPI deltas
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else None

    def fmt(n: int | float) -> str:
        return f"{int(n):,}"

    st.subheader("Latest Key Figures")
    st.caption(f"As of provider date: {last['provider_date'].strftime('%Y-%m-%d')}. Delta is change from previous day.")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.metric("e-Verified Returns", fmt(last["e_verified_returns"]), fmt(last[daily_change_cols["e_verified_returns"]]))
    with c2:
        st.metric("Processed Refunds", fmt(last["total_processed_refund"]), fmt(last[daily_change_cols["total_processed_refund"]]))
    with c3:
        st.metric("Registered Users", fmt(last["indv_reg_users"]), fmt(last[daily_change_cols["indv_reg_users"]]))
    with c4:
        st.metric("Aadhaar-linked PAN", fmt(last["total_aadhar_linked_pan"]), fmt(last[daily_change_cols["total_aadhar_linked_pan"]]))
    with c5:
        st.metric(
            "Pending Processing",
            f"{last['pending_processing_percentage']:.2%}",
            f"{last['daily_pending_processing_percentage']:.2%}",
        )
    with c6:
        avg_processed_val = last['avg_processed_last_7_days']
        avg_processed_delta = (last['avg_processed_last_7_days'] - prev['avg_processed_last_7_days']) if prev is not None and pd.notna(prev['avg_processed_last_7_days']) else None
        st.metric(
            "Avg Processed (7d)",
            f"{avg_processed_val:.2f}" if pd.notna(avg_processed_val) else "N/A",
            f"{avg_processed_delta:.2f}" if avg_processed_delta is not None and pd.notna(avg_processed_delta) else None,
        )


    st.subheader("Daily Changes Analysis")
    st.write("Shows the day-over-day change in key metrics. Days with no change could indicate processing delays or weekends/holidays.")
    
    daily_df_melted = df.melt(
        id_vars=["provider_date"],
        value_vars=list(daily_change_cols.values()),
        var_name="metric",
        value_name="daily_change",
    )
    daily_df_melted["metric"] = daily_df_melted["metric"].str.replace("daily_", "").str.replace("_", " ").str.title()

    daily_chart = alt.Chart(daily_df_melted).mark_bar().encode(
        x=alt.X("provider_date:T", title="Date"),
        y=alt.Y("daily_change:Q", title="Daily Change"),
        tooltip=["provider_date:T", "metric:N", alt.Tooltip("daily_change:Q", format=",")],
    ).properties(
        height=150
    ).facet(
        facet=alt.Facet("metric:N", title=None, header=alt.Header(labelFontSize=12, title=None)),
        columns=2,
    ).resolve_scale(
        y='independent'
    )
    st.altair_chart(daily_chart, use_container_width=True)


    st.subheader("Metrics Over Time")
    st.write("Cumulative totals for key metrics, and the percentage of e-verified returns pending processing.")

    # Melt cumulative data for plotting
    cumulative_df_melted = df.melt(
        id_vars=["provider_date"],
        value_vars=cumulative_cols,
        var_name="metric",
        value_name="total",
    )
    cumulative_df_melted["metric"] = cumulative_df_melted["metric"].str.replace("_", " ").str.title()

    # Layer 1: Cumulative counts
    line_cumulative = alt.Chart(cumulative_df_melted).mark_line(point=True).encode(
        x=alt.X("provider_date:T", title="Date"),
        y=alt.Y("total:Q", title="Cumulative Totals"),
        color=alt.Color("metric:N", title="Metric"),
        tooltip=["provider_date:T", "metric:N", alt.Tooltip("total:Q", format=",")],
    )

    # Layer 2: Percentage line
    line_percentage = alt.Chart(df).mark_line(point=True, strokeDash=[5,5], color="firebrick").encode(
        x=alt.X("provider_date:T", title="Date"),
        y=alt.Y("pending_processing_percentage:Q", title="Pending Processing %", axis=alt.Axis(format='%')),
        tooltip=[alt.Tooltip("provider_date:T"), alt.Tooltip("pending_processing_percentage:Q", format=".2%")],
    )

    # Combine charts with independent y-axes
    combined_chart = alt.layer(line_cumulative, line_percentage).resolve_scale(
        y='independent'
    ).interactive()

    st.altair_chart(combined_chart, use_container_width=True)


    st.subheader("Weekly Processing Patterns")
    st.write("Average daily change by day of the week for key metrics.")
    weekdays = [
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
    ]
    
    # Calculate mean of daily changes for each metric by weekday
    # weekly_agg = df.groupby("weekday")[list(daily_change_cols.values())].mean().reindex(weekdays)
    weekly_agg = df.groupby("weekday")["daily_total_processed_refund"].mean().reindex(weekdays)
    weekly_agg.columns = [col.replace("daily_", "").replace("_", " ").title() for col in weekly_agg.columns]
    
    st.bar_chart(weekly_agg)

    st.subheader("Raw Data")
    st.write("The full dataset, with interpolated rows (days with no new data from provider) highlighted in a light yellow.")

    def highlight_interpolated(row):
        color = 'background-color: #fff2cc' if row.interpolated else ''
        return [color] * len(row)

    # Prepare dataframe for display
    # We select and format columns for a clean presentation in the raw data table.
    display_df = df.copy()
    
    # Ensure daily processed is int for display
    display_df[daily_change_cols["total_processed_refund"]] = display_df[daily_change_cols["total_processed_refund"]].astype(int)

    # Columns to show in the raw data table
    cols_to_show = [
        "provider_date",
        "e_verified_returns",
        "total_processed_refund",
        daily_change_cols["total_processed_refund"],
        "pending_processing_percentage",
        "indv_reg_users",
        "total_aadhar_linked_pan",
        "weekday",
        "interpolated",  # needed for styling
    ]
    # Filter display_df to only include columns that actually exist in df
    display_df = display_df[[col for col in cols_to_show if col in display_df.columns]]

    st.dataframe(
        display_df.style.apply(highlight_interpolated, axis=1)
        .format({"pending_processing_percentage": "{:.2%}"})
        .hide(subset=["interpolated"], axis="columns"),
        use_container_width=True,
    )


if __name__ == "__main__":
    main()

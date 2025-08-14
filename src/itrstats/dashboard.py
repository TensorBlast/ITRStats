from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
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

    # Top KPI boxes: latest provider date, and within it the latest collected snapshot
    all_data = load_data()
    if all_data.empty:
        st.warning("No data yet. Run the collector to ingest a snapshot.")
        st.stop()

    latest_provider_date = all_data["provider_last_updated_raw"].max()

    sorted_data = all_data.sort_values(["provider_last_updated_raw", "collected_at"], ascending=[True, False])
    sorted_data["rank"] = sorted_data.groupby("provider_last_updated_raw")['collected_at'].rank(method="first", ascending=False)
    sorted_data["rank"] = sorted_data["rank"].astype(int)
    data = sorted_data[sorted_data["rank"] == 1].drop("rank", axis=1)

    previous_provider_date = sorted_data[sorted_data["provider_last_updated_raw"] < latest_provider_date]["provider_last_updated_raw"].max()
    latest_row_df = data[data["provider_last_updated_raw"] == latest_provider_date]
    previous_row_df = data[data["provider_last_updated_raw"] == previous_provider_date]

    df = data.copy()

    df['daily_processed'] = df['total_processed_refund'] - df['total_processed_refund'].shift(1)
    df['daily_processed'] = df['daily_processed'].fillna(0)

    assert not latest_row_df.empty
    last = latest_row_df.iloc[0]
    prev = previous_row_df.iloc[0] if not previous_row_df.empty else None

    def fmt(n: int | float) -> str:
        return f"{int(n):,}"

    st.subheader("Key figures")
    st.caption(f"As of provider date: {last['provider_last_updated_raw']}")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        delta = (int(last["e_verified_returns"]) - int(prev["e_verified_returns"])) if prev is not None else None
        st.metric("e-Verified Returns", fmt(last["e_verified_returns"]), delta)
    with c2:
        delta = (int(last["total_processed_refund"]) - int(prev["total_processed_refund"])) if prev is not None else None
        st.metric("Processed Refunds", fmt(last["total_processed_refund"]), delta)
    with c3:
        delta = (int(last["indv_reg_users"]) - int(prev["indv_reg_users"])) if prev is not None else None
        st.metric("Registered Users", fmt(last["indv_reg_users"]), delta)
    with c4:
        delta = (int(last["total_aadhar_linked_pan"]) - int(prev["total_aadhar_linked_pan"])) if prev is not None else None
        st.metric("Aadhaar-linked PAN", fmt(last["total_aadhar_linked_pan"]), delta)


    #df["collected_date"] = pd.to_datetime(df["collected_date"])  # type: ignore
    df["provider_last_updated_raw"] = pd.to_datetime(df["provider_last_updated_raw"])  # type: ignore
    df["weekday"] = df["provider_last_updated_raw"].dt.day_name()

    df["provider_date"] = df["provider_last_updated_raw"].dt.strftime("%Y-%m-%d")

    st.subheader("Daily metrics (max per day)")
    st.line_chart(
        df.set_index("provider_date")[
            [
                "e_verified_returns",
                "total_processed_refund",
                "indv_reg_users",
                "total_aadhar_linked_pan",
            ]
        ]
    )

    st.subheader("Weekly patterns")
    agg = (
        df.groupby("weekday")["total_processed_refund"].mean().reindex(
            [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
        )
    )
    st.bar_chart(agg)

    st.subheader("Raw data")
    st.dataframe(df)


if __name__ == "__main__":
    main()

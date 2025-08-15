from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from .db import get_engine, init_db, session_scope
from .models import Snapshot
from .scraper import StatsPayload, fetch_stats


def collect_once(db_path: str | Path | None = None) -> Snapshot:
    engine = get_engine(db_path)
    init_db(engine)

    payload: StatsPayload = fetch_stats()

    now = datetime.utcnow()
    collected_date = now.strftime("%Y-%m-%d")

    snapshot = Snapshot(
        indv_reg_users=payload.indv_reg_users,
        e_verified_returns=payload.e_verified_returns,
        total_aadhar_linked_pan=payload.total_aadhar_linked_pan,
        total_processed_refund=payload.total_processed_refund,
        provider_last_updated_raw=payload.provider_last_updated_raw,
        collected_at=now,
        collected_date=collected_date,
    )

    with session_scope(engine) as session:  # type: Session
        session.add(snapshot)

    return snapshot


if __name__ == "__main__":
    snap = collect_once()
    print(
        f"Collected at {snap.collected_at.isoformat()} | "
        f"eVerifiedReturns={snap.e_verified_returns} | "
        f"TotalProcessedRefund={snap.total_processed_refund}"
    )

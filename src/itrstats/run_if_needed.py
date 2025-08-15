from __future__ import annotations

import random
import time
from datetime import datetime, timedelta, timezone
from typing import Tuple

import pandas as pd
from sqlalchemy import create_engine, text

from .collector import collect_once
from .db import DEFAULT_DB_PATH


FOUR_HOURS = timedelta(hours=4)


def should_collect(db_path: str = str(DEFAULT_DB_PATH)) -> Tuple[bool, str]:
    # Collect if the latest snapshot is older than 4 hours (UTC)
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    with engine.begin() as conn:
        last_ts = conn.execute(
            text("SELECT MAX(collected_at) FROM snapshots"),
        ).scalar()
        now = datetime.now(timezone.utc)
        if last_ts is None:
            return True, "no previous snapshots"
        # SQLite returns string for DateTime by default; let pandas parse if needed
        if isinstance(last_ts, str):
            try:
                last_dt = datetime.fromisoformat(last_ts)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
            except Exception:
                # Fallback: force collect if parsing fails
                return True, "failed to parse last timestamp"
        elif isinstance(last_ts, datetime):
            last_dt = last_ts if last_ts.tzinfo else last_ts.replace(tzinfo=timezone.utc)
        else:
            return True, "unknown timestamp type"

        age = now - last_dt
        if age >= FOUR_HOURS:
            return True, f"last snapshot {age} ago"
        return False, f"last snapshot {age} ago (< 4 hours)"


def main() -> None:
    # Small jitter to avoid synchronized runs when the laptop wakes up
    time.sleep(random.uniform(0.0, 30.0))

    ok, reason = should_collect()
    if not ok:
        print(f"skip: {reason}")
        return

    snap = collect_once()
    print(
        f"collected: provider={snap.provider_last_updated_raw} "
        f"collected_at={snap.collected_at.isoformat()} "
        f"processed_refund={snap.total_processed_refund}"
    )


if __name__ == "__main__":
    main()

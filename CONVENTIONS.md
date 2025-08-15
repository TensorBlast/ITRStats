## ITRStats: Architecture & Conventions

This document is optimized for AI agents. It explains how the app is structured, how data flows, and what to change when extending features.

### TL;DR for agents
- **Purpose**: Collect daily public statistics from the Income Tax e‑Portal and visualize trends.
- **Flow**: `scraper.fetch_stats()` → `collector.collect_once()` → SQLite `snapshots` table → `dashboard.py` (Streamlit) visualizes.
- **DB file**: `data/itrstats.sqlite3` (path constant: `itrstats.db.DEFAULT_DB_PATH`).
- **Run collector**: `PYTHONPATH=src python -m itrstats.collector`.
- **Run dashboard**: `PYTHONPATH=src streamlit run src/itrstats/dashboard.py`.
- **Automate**: macOS `launchd` via `scripts/install_launchd.sh`.

### Repository layout
```text
ITRStats/
  data/                    # SQLite database (created at runtime)
  logs/                    # launchd/stdout logs
  scripts/                 # bootstrap + launchd install/uninstall
  src/itrstats/
    scraper.py             # HTTP client + parsing → StatsPayload
    collector.py           # Orchestrates fetch + persist Snapshot
    db.py                  # Engine/session helpers; DB path
    models.py              # SQLAlchemy ORM models (Snapshot)
    run_if_needed.py       # 4-hour throttling guard for scheduled runs
    dashboard.py           # Streamlit dashboard (read-only)
```

### Runtime components
- **Scraper** (`itrstats.scraper`)
  - Endpoint: `https://eportal.incometax.gov.in/iec/oursuccessenablers/saveData` (constant `ENDPOINT`).
  - Builds browser-like headers, uses retries with exponential backoff + jitter.
  - Parses JSON into immutable `StatsPayload` (dataclass).

- **Collector** (`itrstats.collector`)
  - Initializes DB (create tables if missing), maps `StatsPayload` → `Snapshot`, inserts a row with `collected_at` (UTC) and `collected_date` (YYYY-MM-DD).

- **Database** (`itrstats.db`, `itrstats.models`)
  - SQLite via SQLAlchemy 2.x. DB path: `DEFAULT_DB_PATH` at `data/itrstats.sqlite3`.
  - Context-managed `session_scope()` for atomic writes.

- **Scheduler** (`itrstats.run_if_needed` + `scripts/*.plist/.sh`)
  - Gatekeeper decides whether to collect based on last `collected_at` ≥ 4 hours ago.
  - `install_launchd.sh` installs a LaunchAgent to run daily and on load; logs are in `logs/`.

- **Dashboard** (`itrstats.dashboard`)
  - Streamlit app queries all snapshots and computes per-provider-date maxima (latest snapshot per provider date) plus deltas versus previous provider date.
  - Visualizations: KPI metrics, daily line chart, weekly bar chart, and raw data table.

### Data model (table: `snapshots`)
Source: `src/itrstats/models.py`
- **id**: int, PK, autoincrement
- **indv_reg_users**: bigint, not null
- **e_verified_returns**: bigint, not null
- **total_aadhar_linked_pan**: bigint, not null
- **total_processed_refund**: bigint, not null
- **provider_last_updated_raw**: string(64), nullable (provider’s reported date)
- **collected_at**: datetime (UTC), indexed
- **collected_date**: string(10) YYYY-MM-DD, indexed

Note: No deduplication is enforced; multiple snapshots can exist per provider date. The dashboard picks the most recent per provider date.

### Control flow & business rules
- **Retry policy**: `fetch_stats()` uses up to 5 attempts with exponential backoff (cap ~30s) and random jitter.
- **Collection cadence**: `run_if_needed.should_collect()` allows a run if the latest `collected_at` is ≥ 4 hours old (UTC-aware; string fallback parsing for SQLite).
- **Dashboard aggregation**:
  - Convert `provider_last_updated_raw` to datetime → `provider_date` string.
  - For each `provider_date`, select the snapshot with the highest `collected_at`.
  - KPI deltas compare current provider date vs the previous provider date’s selected snapshot.

### Safe-change checklist (extend or modify)
When adding a new metric from the provider:
1) **Scraper**: Map new JSON key in `StatsPayload.from_json()`.
2) **Model**: Add a column to `Snapshot` in `models.py` with appropriate type/nullability.
3) **Collector**: Populate the new field when constructing `Snapshot`.
4) **Migration**: For existing DBs, either:
   - Quick path (dev-only): delete `data/itrstats.sqlite3` and allow auto-create, or
   - Proper path: introduce an Alembic migration (package already in requirements).
5) **Dashboard**: Update queries/derived columns/visuals to include the new field.

When changing scheduling behavior:
1) Adjust `FOUR_HOURS` or logic in `run_if_needed.should_collect()`.
2) If cadence changes materially, review `launchd` plist in `scripts/`.

When modifying the endpoint/headers:
1) Update `ENDPOINT` and `_build_headers()` in `scraper.py`.
2) Verify expected JSON keys and adapt `StatsPayload.from_json()`.

### Coding conventions
- **Python & typing**: Use modern type hints. Prefer explicit types for public functions. `from __future__ import annotations` is used across modules.
- **Time**: Treat `collected_at` as UTC. When parsing SQLite strings, ensure timezone awareness (see `run_if_needed.py`).
- **Errors**: Do not swallow exceptions silently. Use retries with capped backoff for network calls. Let unexpected errors surface.
- **DB access**: Use SQLAlchemy 2.x patterns. Create engines via `db.get_engine()`. Use `session_scope()` for atomic writes.
- **File paths**: Prefer absolute paths derived from `DEFAULT_DB_PATH` for DB operations; avoid hard-coded relative paths in code.
- **Dependencies**: Listed in `requirements.txt`. Keep versions pinned.
- **Style**: Readable names, early returns, minimal nesting. Avoid inline comments; place concise comments above complex logic.

### Operations & commands
Collector (one-off):
```bash
PYTHONPATH=src python -m itrstats.collector
```

Dashboard:
```bash
PYTHONPATH=src streamlit run src/itrstats/dashboard.py
```

Automate (macOS launchd):
```bash
./scripts/install_launchd.sh
```
Uninstall:
```bash
./scripts/uninstall_launchd.sh
```

### Known limitations
- No deduplication of provider dates; dashboard resolves by taking the most recent snapshot per provider date.
- No formal migration history is included yet (Alembic is installed but not configured). Schema changes require either migrations or DB reset.
- Dashboard reads the full `snapshots` table; fine for small datasets.

### Glossary
- **Provider date**: Value in `provider_last_updated_raw`, the source’s reported last updated timestamp.
- **Snapshot**: One persisted row representing a single scrape, with raw counts and capture metadata.



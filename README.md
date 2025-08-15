## ITR Stats

A tiny project to collect daily public statistics from the Income Tax e-Portal and visualize trends.

### Setup

- Create and activate a virtual environment
- Install requirements

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Or run the bootstrap script:

```bash
./scripts/bootstrap.sh
```

### Collect one snapshot

```bash
PYTHONPATH=src python -m itrstats.collector
```

- Database will be created at `data/itrstats.sqlite3`.

### Run the dashboard

```bash
PYTHONPATH=src streamlit run src/itrstats/dashboard.py
```

### Automate daily collection (macOS launchd)

1) Install the LaunchAgent:

```bash
./scripts/install_launchd.sh
```

2) Logs will be in `logs/collector.log`, with `launchd` stdio in `logs/launchd.*.log`.
3) The job runs at 01:05 daily and also at load.

To remove/disable:

```bash
launchctl unload "$HOME/Library/LaunchAgents/com.moot.itrstats.collector.plist"
```

### Source endpoint

Public stats endpoint documented via exploratory inspection:

- https://eportal.incometax.gov.in/iec/oursuccessenablers/saveData

# pagemon

Monitor web pages for changes from your terminal.

[![PyPI version](https://img.shields.io/pypi/v/pagemon)](https://pypi.org/project/pagemon/)
[![Python versions](https://img.shields.io/pypi/pyversions/pagemon)](https://pypi.org/project/pagemon/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/Ltbltbltbltb/pagemon/blob/main/LICENSE)
[![CI](https://github.com/Ltbltbltbltb/pagemon/actions/workflows/ci.yml/badge.svg)](https://github.com/Ltbltbltbltb/pagemon/actions/workflows/ci.yml)

## Why pagemon?

- **CLI-first** -- designed for developers who live in the terminal
- **Lightweight** -- pure Python, no Docker, no browser engine, no background daemon
- **Smart diffing** -- strips HTML noise (scripts, nav, timestamps) so you only see real content changes
- **CSS selectors** -- watch a specific element instead of the whole page
- **Webhook notifications** -- POST JSON to Slack, Discord, or any HTTP endpoint when something changes
- **Zero config** -- works out of the box with sensible defaults and a local SQLite database

## Features

- Add, remove, and list monitored URLs
- Check one or all targets for changes on demand
- CSS selector support to monitor specific page elements
- Colored unified diffs in the terminal (via Rich)
- Snapshot history with content hashes
- Smart noise filtering (whitespace, timestamps, dates)
- Webhook notifications on change (Slack, Discord, custom)
- JSON and CSV export
- JSON output mode for scripting (`--json`)
- Python API for programmatic use
- SQLite storage -- single file, no server needed

## Installation

```bash
pip install pagemon
```

Requires Python 3.10+.

## Quick Start

Add a page to monitor:

```
$ pagemon add https://example.com/pricing --name "Pricing Page" --interval 60
Added: https://example.com/pricing
  Selector: -
  Interval: every 60m
```

Monitor a specific element with a CSS selector:

```
$ pagemon add https://example.com/status --name "Status" --selector "div.status-banner"
Added: https://example.com/status
  Selector: div.status-banner
  Interval: every 30m
```

Check all targets for changes:

```
$ pagemon check --all
  NEW      Pricing Page
  NEW      Status
```

After subsequent checks, changed pages show a diff:

```
$ pagemon check --all
  OK       Pricing Page
  CHANGED  Status
--- previous
+++ current
@@ -1,3 +1,3 @@
-All systems operational
+Degraded performance on API endpoints
```

List monitored pages:

```
$ pagemon ls
        Monitored Pages
┌────┬──────────────┬────────────────────┬──────────┐
│ ID │ Name / URL   │ Selector           │ Interval │
├────┼──────────────┼────────────────────┼──────────┤
│  1 │ Pricing Page │ -                  │      60m │
│  2 │ Status       │ div.status-banner  │      30m │
└────┴──────────────┴────────────────────┴──────────┘
```

View snapshot history:

```
$ pagemon history https://example.com/status --limit 5
           History: https://example.com/status
┌────┬─────────────────────┬──────────────┬────────┬───────┐
│ ID │ Timestamp           │ Hash         │ Status │  Size │
├────┼─────────────────────┼──────────────┼────────┼───────┤
│  3 │ 2026-03-29T14:30:00 │ a1b2c3d4e5f6 │    200 │   482 │
│  2 │ 2026-03-29T14:00:00 │ f6e5d4c3b2a1 │    200 │   471 │
│  1 │ 2026-03-29T13:30:00 │ 9e8d7c6b5a4f │    200 │   471 │
└────┴─────────────────────┴──────────────┴────────┴───────┘
```

## CLI Reference

```
pagemon [OPTIONS] COMMAND [ARGS]
```

### `pagemon add URL`

Add a URL to monitor.

| Option | Short | Default | Description |
|---|---|---|---|
| `--name` | `-n` | -- | Friendly name for display |
| `--selector` | `-s` | -- | CSS selector to watch a specific element |
| `--interval` | `-i` | `30` | Check interval in minutes |

### `pagemon rm URL`

Remove a URL from monitoring.

### `pagemon ls`

List all monitored URLs.

| Option | Description |
|---|---|
| `--json` | Output as JSON |

### `pagemon check [URL]`

Check for changes. Checks a single URL, or all targets if no URL is given.

| Option | Short | Description |
|---|---|---|
| `--all` | -- | Check all targets |
| `--json` | -- | Output as JSON |
| `--webhook` | `-w` | Webhook URL for notifications (or set `PAGEMON_WEBHOOK`) |

### `pagemon diff URL`

Show the latest diff between the two most recent snapshots for a URL.

### `pagemon history URL`

Show snapshot history for a URL.

| Option | Short | Default | Description |
|---|---|---|---|
| `--limit` | `-l` | `10` | Number of snapshots to show |

### `pagemon export`

Export all targets and their latest snapshots.

| Option | Default | Description |
|---|---|---|
| `--format` | `json` | Output format: `json` or `csv` |

### `pagemon --version`

Print the installed version.

## Python API

```python
from pathlib import Path
from pagemon.core import PageMon

# Initialize with defaults (SQLite at ~/.pagemon/pagemon.db)
mon = PageMon()

# Or with custom settings
mon = PageMon(
    db_path=Path("/tmp/my-monitor.db"),
    webhook_url="https://hooks.slack.com/services/T.../B.../xxx",
    timeout=15.0,
)

# Add a target
target = mon.add(
    "https://example.com/pricing",
    name="Pricing",
    selector="div.pricing-table",
    interval=60,
)

# Check all targets
results = mon.check_all()
for result in results:
    print(f"{result.target.url}: {result.status.value}")
    if result.diff_text:
        print(result.diff_text)

# Check a single target
result = mon.check(target)

# Get snapshot history
snapshots = mon.get_history("https://example.com/pricing", limit=5)

# Get the latest diff
diff = mon.get_diff("https://example.com/pricing")

# List all targets
targets = mon.list_targets()

# Remove a target
mon.remove("https://example.com/pricing")

# Always close when done
mon.close()
```

## Configuration

pagemon works with zero configuration. All settings can be overridden via environment variables or CLI options.

| Variable | CLI Option | Default | Description |
|---|---|---|---|
| `PAGEMON_DB` | `--db` | `~/.pagemon/pagemon.db` | Path to the SQLite database |
| `PAGEMON_WEBHOOK` | `--webhook` / `-w` | -- | Webhook URL for POST notifications |

The webhook sends a JSON payload on every detected change:

```json
{
  "url": "https://example.com/status",
  "name": "Status",
  "status": "changed",
  "diff": "--- previous\n+++ current\n@@ ...",
  "timestamp": "2026-03-29T14:30:00.000000"
}
```

## How It Works

pagemon follows a simple pipeline for each monitored URL:

```
Fetch --> Extract --> Diff --> Notify
```

1. **Fetch** -- HTTP GET via httpx with configurable timeout and custom headers
2. **Extract** -- HTML is parsed with BeautifulSoup; scripts, styles, nav, and footer elements are stripped. If a CSS selector is set, only matching elements are extracted
3. **Diff** -- Content is hashed (SHA-256) for fast comparison. If the hash differs, a normalization pass filters out whitespace and timestamp noise. Only meaningful changes produce a unified diff
4. **Notify** -- Changed results are sent to the configured webhook (or printed to the console)

All snapshots are stored in a local SQLite database for history and diffing.

## Contributing

Contributions are welcome. To get started:

```bash
git clone https://github.com/Ltbltbltbltb/pagemon.git
cd pagemon
pip install -e ".[dev]"
pytest
ruff check src/ tests/
```

Please open an issue before submitting large changes.

## License

MIT -- see [LICENSE](LICENSE) for details.

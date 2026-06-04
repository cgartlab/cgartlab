# RSS Updater — cgartlab

## Overview

Python RSS feed updater for the cgartlab.github.io blog. Monitors configured RSS feeds, detects new entries, generates markdown blog posts, and optionally sends notifications.

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11 |
| Config | JSON (`rss_config.json`) |
| Tests | `pytest` (in `tests/`) |

## Configuration

Edit `rss_config.json`:

```json
{
  "feeds": [
    {
      "url": "https://example.com/feed.xml",
      "target": "src/content/blog/",
      "interval_minutes": 60
    }
  ]
}
```

| Field | Description |
|---|---|
| `url` | RSS/Atom feed URL |
| `target` | Output directory for generated posts |
| `interval_minutes` | Polling interval (if running daemon mode) |

## Usage

```bash
# Run once (fetch and process all feeds)
python rss_updater.py

# Run with specific config
python rss_updater.py --config rss_config.json

# Run in daemon mode (poll continuously)
python rss_updater.py --daemon

# Run tests
pytest tests/
```

## Project Structure

```
cgartlab/
├── rss_updater.py        # Main entry point
├── rss_updater/          # Core package
│   ├── __init__.py
│   ├── fetcher.py        # RSS feed fetching
│   ├── parser.py         # Feed parsing
│   ├── generator.py      # Markdown generation
│   └── notifier.py       # Notification (optional)
├── tests/                # Pytest test suite
├── assets/               # Related assets
├── rss_config.json       # Feed configuration
├── pyproject.toml        # Python project config
└── requirements.txt      # Python dependencies
```

## Dependencies

- `feedparser` — RSS/Atom feed parsing
- `httpx` — HTTP client
- `pyyaml` — YAML (if needed)
- `pytest` — Testing (dev dependency)

## See Also

- `Home.md` — project wiki / overview
- `CODE_WIKI.md` — code-level documentation
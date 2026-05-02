# AGENTS.md

## Purpose
This repo contains a personal blog site (CGArtLab) with an automated RSS updater that fetches blog posts and updates README.md.

## Developer Commands

```bash
# Run RSS updater (checks feeds and updates README.md if new content)
python rss_updater.py

# Check mode (detect changes without updating)
python rss_updater.py --check-mode

# Force update regardless of changes
python rss_updater.py --force

# Verbose output
python rss_updater.py --verbose
```

## Configuration

Edit `rss_config.json` to manage feeds:
- `feeds[].url` - RSS feed URL
- `feeds[].section_marker` - HTML comment marker in README (e.g., `BLOG_POSTS_START`)
- `feeds[].max_posts` - Number of posts to display
- `feeds[].enabled` - Enable/disable feed

The updater replaces content between `<!-- {section_marker} -->` and `<!-- {section_marker.replace('START', 'END')} -->`.

## Dependencies

```
feedparser==6.0.11
requests==2.32.3
urllib3>=2.6.0,<3.0.0
```

Install with: `pip install -r requirements.txt`

## GitHub Workflow

- Runs every 4 hours on schedule
- Also runs on push to `main` when `rss_config.json`, `rss_updater.py`, or workflow file changes
- Can be triggered manually via `workflow_dispatch`

History is cached in `.rss_history/` (preserved across workflow runs).
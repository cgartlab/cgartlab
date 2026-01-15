# Copilot Instructions for cgartlab

## Project Overview

**cgartlab** is a personal portfolio and blogging platform for a digital artist. The project maintains a dynamic README that automatically displays the latest blog posts by aggregating RSS feeds.

### Core Purpose

- Showcase digital art and 3D visual design work
- Automatically update the README with latest blog posts via RSS feed aggregation
- Serve as a living portfolio that reflects current content

## Architecture & Key Components

### 1. Blog Post Automation Pipeline

**Location:** [`scripts/get_latest_posts.py`](scripts/get_latest_posts.py)

**What it does:**

- Fetches blog posts from configured RSS feeds (currently: `https://cgartlab.com/rss.xml`)
- Parses feed entries and extracts title, URL, and publication date
- Sorts posts by date (newest first) and limits display to 10 posts total
- Uses regex-based chunk replacement to update README.md dynamically

**Key functions:**

- `fetch_posts_from_feed()` - Handles individual RSS feed requests with error handling
- `build_blog_content()` - Aggregates multiple feeds and formats output
- `replace_chunk()` - Uses regex to find and replace content blocks marked by `<!-- MARKER_START -->...<!-- MARKER_END -->` comments

**Important pattern:** The script returns exit code `2` when updates succeed and `0` when no changes needed or failure occurs (see line 106-142).

### 2. CI/CD Automation

**Location:** [`.github/workflows/update-blog-posts.yml`](.github/workflows/update-blog-posts.yml)

**Trigger events:**

- Daily schedule (2 AM UTC)
- Manual workflow dispatch
- On push to script files

**Dependencies installed:** `feedparser`, `requests` (Python 3.9+)

### 3. README Structure

**Location:** [README.md](README.md)

**Content markers:**

- Blog content is wrapped with `<!-- BLOG_POSTS_START -->...<!-- BLOG_POSTS_END -->` comments
- The script replaces content between these markers (note: current code uses `blog` marker internally, but README uses `BLOG_POSTS_START/END`)

## Developer Conventions & Patterns

### Code Style

- **Python version:** 3.9+
- **String formatting:** Use f-strings and `.format()` for flexibility
- **Error handling:** Comprehensive try-catch blocks with informative logging
- **Logging:** Use print statements with prefixes like `[fetch]`, `[build]`, `[main]` for debugging

### RSS Feed Integration

- **User-Agent header:** Required to identify bot requests (`Mozilla/5.0 (compatible; cgartlab/1.0)`)
- **Timeout:** 15 seconds for HTTP requests
- **Feed parsing:** Uses `feedparser.parse()` - handles various RSS/Atom formats automatically
- **Date extraction:** Prioritize `published_parsed` over `updated_parsed` from feed entries

### Content Update Strategy

- **Idempotent updates:** Script handles cases where content blocks don't exist or are already updated
- **Graceful degradation:** Single feed failure doesn't stop entire pipeline; warnings are logged but execution continues
- **Maximum posts:** 10 total posts displayed, 5 per feed (configurable in function parameters)

## Common Workflows

### Adding a New RSS Feed

1. Edit `update_readme()` in [`scripts/get_latest_posts.py`](scripts/get_latest_posts.py) (line 103-107)
2. Add entry to `feeds` dictionary: `"feed_name": "https://example.com/rss.xml"`
3. Test locally: `python scripts/get_latest_posts.py`
4. Verify README.md updated correctly

### Testing the Script Locally

```bash
# Install dependencies
pip install feedparser requests

# Run the update script
python scripts/get_latest_posts.py

# Check for exit code
echo $?  # Returns 0 or 2 on success
```

### Debugging Failed Workflow Runs

1. Check GitHub Actions logs in `.github/workflows/update-blog-posts.yml`
2. Look for `[fetch]`, `[build]`, `[main]` prefixed messages in output
3. Common issues:
   - **403 Forbidden:** RSS feed URL is blocking requests. May need stronger User-Agent or alternative feed URL.
   - **Network timeouts:** Feed server is slow or unreachable. Check firewall/network restrictions.
   - **Malformed RSS feed:** Feed structure is invalid. Validate with an RSS validator tool.
   - **Missing README markers:** Check that `<!-- BLOG_POSTS_START -->...<!-- BLOG_POSTS_END -->` comments exist in README.md
4. Script continues on single feed failure - check for `⚠️` warnings

## Integration Points & Dependencies

### External Services

- **RSS Feed Source:** `https://cgartlab.com/rss.xml` (configurable)
- **GitHub Actions:** Handles scheduling and automated execution

### Python Dependencies

- `feedparser` - RSS/Atom feed parsing
- `requests` - HTTP requests with proper timeout handling
- `pathlib` - Cross-platform file path handling

### GitHub Integration

- Uses `GITHUB_TOKEN` for authenticated commits
- Requires `contents: write` and `pull-requests: write` permissions
- Commits are triggered automatically by workflow

## Important Notes for AI Agents

1. **Marker format matters:** The script looks for `<!-- MARKER -->...<!-- MARKER ends -->` patterns. Don't change these without updating the regex in `replace_chunk()`.

2. **Exit codes are intentional:** The script returns `2` when successful updates occur and `0` when no changes needed - this is used by the workflow to determine success.

3. **Content generation order:** Feeds are aggregated, then sorted by date, then limited to 10 items. Preserve this order when modifying.

4. **Localization awareness:** Code contains Chinese comments and messages. Maintain bilingual support where present (English function names, Chinese comments).

5. **GitHub Actions context:** The workflow uses `token: ${{ secrets.GITHUB_TOKEN }}` for commits, not a personal access token. This is the modern best practice.

## References

- [GitHub Actions Workflow Documentation](https://docs.github.com/en/actions)
- [Python feedparser Documentation](https://pythonhosted.org/feedparser/)
- [Chunk replacement pattern source](https://github.com/tw93/tw93) - This project adapts the strategy from tw93/tw93

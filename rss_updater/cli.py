from __future__ import annotations

import argparse
import sys
import time
from typing import Any

from rss_updater.fetcher import FeedFetcher
from rss_updater.models import AppConfig, load_config
from rss_updater.updater import RSSUpdater


def _setup_stdout_utf8() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
            sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except AttributeError:
            pass


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rss-updater",
        description="RSS feed updater for README.md",
    )
    parser.add_argument(
        "--config",
        "-c",
        default="rss_config.json",
        help="Path to config file (default: rss_config.json)",
    )
    parser.add_argument(
        "--check-mode",
        action="store_true",
        help="Check for changes without writing to README",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Force update without change detection",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Perform health check on all feeds",
    )
    return parser


def _print_health_table(results: list[dict[str, Any]]) -> None:
    header = f"{'Feed Name':<25} | {'Status':<10} | {'Response Time':<13} | {'Articles':<8} | {'Error':<30}"
    print(header)
    print("-" * len(header))
    for row in results:
        feed_name = row.get("feed_name", "")[:24]
        status = row.get("status", "")[:9]
        response_time = f"{row.get('response_time', 0):.2f}s"
        articles = str(row.get("articles_count", ""))[:7]
        error = (row.get("error_message") or "")[:29]
        print(f"{feed_name:<25} | {status:<10} | {response_time:<13} | {articles:<8} | {error:<30}")


def _health_check(config: AppConfig) -> int:
    fetcher = FeedFetcher()
    results: list[dict[str, Any]] = []

    for feed in config.feeds:
        if not feed.enabled:
            continue
        start = time.time()
        try:
            articles = fetcher._fetch_direct(
                fetcher.session,
                feed.url,
                fetcher._build_headers(feed.url),
                config.settings.timeout_seconds,
            )
            elapsed = time.time() - start
            if articles is not None:
                results.append({
                    "feed_name": feed.name,
                    "status": "ok",
                    "response_time": elapsed,
                    "articles_count": len(articles),
                    "error_message": None,
                })
            else:
                results.append({
                    "feed_name": feed.name,
                    "status": "fail",
                    "response_time": elapsed,
                    "articles_count": 0,
                    "error_message": "No articles returned",
                })
        except Exception as exc:
            elapsed = time.time() - start
            results.append({
                "feed_name": feed.name,
                "status": "error",
                "response_time": elapsed,
                "articles_count": 0,
                "error_message": str(exc),
            })

    _print_health_table(results)
    return 0


def main(argv: list[str] | None = None) -> int:
    _setup_stdout_utf8()
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except Exception as exc:
        print(f"Failed to load config: {exc}", file=sys.stderr)
        return 1

    if args.health_check:
        return _health_check(config)

    updater = RSSUpdater(
        config=config,
        check_mode=args.check_mode,
        force=args.force,
    )
    return updater.run()


if __name__ == "__main__":
    sys.exit(main())

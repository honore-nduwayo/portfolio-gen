#!/usr/bin/env python3
"""Generate a Markdown portfolio page from a user's public GitHub repositories.

Usage:
    python portfolio_gen.py --user YOUR_USERNAME --out docs/index.md

Set GITHUB_TOKEN in the environment to raise the API rate limit from
60 requests/hour to 5,000. The token is never written to the output.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

API_ROOT = "https://api.github.com"
USER_AGENT = "portfolio-gen"
REQUEST_TIMEOUT = 15


def fetch_repos(username, token=None):
    """Return the raw list of repo dicts for `username` from the GitHub API.

    This is the only function that touches the network. Everything else
    works on plain dicts, which is what makes the rest of this testable.
    """
    url = "{0}/users/{1}/repos?per_page=100&sort=pushed".format(API_ROOT, username)
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
    }
    if token:
        headers["Authorization"] = "Bearer {0}".format(token)

    request = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            payload = response.read()
    except urllib.error.HTTPError as error:
        raise RuntimeError(describe_http_error(error.code, username)) from error
    except urllib.error.URLError as error:
        raise RuntimeError("could not reach github.com: {0}".format(error.reason)) from error

    try:
        repos = json.loads(payload)
    except json.JSONDecodeError as error:
        raise RuntimeError("GitHub returned something that is not JSON") from error

    if not isinstance(repos, list):
        raise RuntimeError("expected a list of repositories, got {0}".format(type(repos).__name__))

    return repos


def describe_http_error(code, username):
    """Turn an HTTP status code into a sentence the user can act on."""
    if code == 404:
        return "no GitHub user named '{0}'".format(username)
    if code == 403:
        return (
            "GitHub rate limit reached (60 requests/hour without a token). "
            "Set GITHUB_TOKEN and try again, or wait an hour."
        )
    if code == 401:
        return "GITHUB_TOKEN was rejected - check that it is valid and not expired"
    return "GitHub returned HTTP {0}".format(code)


def filter_repos(repos, include_forks=False, exclude=()):
    """Drop private, archived, forked and explicitly excluded repositories."""
    excluded = {name.lower() for name in exclude}
    kept = []

    for repo in repos:
        if repo.get("private"):
            continue
        if repo.get("archived"):
            continue
        if repo.get("fork") and not include_forks:
            continue
        if (repo.get("name") or "").lower() in excluded:
            continue
        kept.append(repo)

    return kept


def parse_timestamp(value):
    """Parse a GitHub ISO-8601 timestamp. Returns None if absent or malformed."""
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except (ValueError, TypeError):
        return None
    return parsed.replace(tzinfo=timezone.utc)


def summarize_repo(repo):
    """Reduce a GitHub repo object to the handful of fields the page needs.

    GitHub sends null for description and language on empty or bare repos,
    so every field is normalised here rather than guarded at render time.
    """
    return {
        "name": repo.get("name") or "untitled",
        "description": (repo.get("description") or "").strip(),
        "url": repo.get("html_url") or "",
        "language": repo.get("language") or "",
        "stars": repo.get("stargazers_count") or 0,
        "pushed_at": parse_timestamp(repo.get("pushed_at")),
    }


def sort_repos(summaries):
    """Most recently pushed first. Repos with no timestamp sink to the bottom."""
    fallback = datetime.min.replace(tzinfo=timezone.utc)
    return sorted(summaries, key=lambda item: item["pushed_at"] or fallback, reverse=True)


def format_date(moment):
    """Format a datetime as '8 Sep 2026'. Returns 'date unknown' for None."""
    if moment is None:
        return "date unknown"
    return "{0} {1}".format(moment.day, moment.strftime("%b %Y"))


def render_repo(summary):
    """Render one repository as a Markdown block."""
    lines = ["### [{0}]({1})".format(summary["name"], summary["url"])]

    if summary["description"]:
        lines.extend(["", summary["description"]])

    facts = []
    if summary["language"]:
        facts.append("`{0}`".format(summary["language"]))
    if summary["stars"]:
        facts.append("{0} stars".format(summary["stars"]))
    facts.append("updated {0}".format(format_date(summary["pushed_at"])))

    lines.extend(["", " · ".join(facts)])
    return "\n".join(lines)


def render_page(summaries, username, generated_on):
    """Render the whole Markdown document."""
    lines = [
        "# {0}".format(username),
        "",
        "Public projects, generated from the GitHub API.",
        "",
        "## Projects",
        "",
    ]

    if not summaries:
        lines.append("_No public repositories yet._")
        lines.append("")
    else:
        for summary in summaries:
            lines.append(render_repo(summary))
            lines.append("")

    lines.extend([
        "---",
        "",
        "Generated {0} by `portfolio_gen.py`.".format(format_date(generated_on)),
    ])

    return "\n".join(lines).rstrip() + "\n"


def write_page(text, path):
    """Write `text` to `path`, creating parent directories as needed."""
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def build_parser():
    parser = argparse.ArgumentParser(
        description="Generate a Markdown portfolio page from your public GitHub repos."
    )
    parser.add_argument("--user", required=True, help="GitHub username")
    parser.add_argument("--out", default="docs/index.md", help="output path (default: docs/index.md)")
    parser.add_argument("--include-forks", action="store_true", help="include forked repositories")
    parser.add_argument("--exclude", nargs="*", default=[], metavar="REPO",
                        help="repository names to leave out")
    parser.add_argument("--limit", type=int, default=None, metavar="N",
                        help="list at most N repositories")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.limit is not None and args.limit < 1:
        print("error: --limit must be 1 or greater", file=sys.stderr)
        return 2

    try:
        repos = fetch_repos(args.user, os.environ.get("GITHUB_TOKEN"))
    except RuntimeError as error:
        print("error: {0}".format(error), file=sys.stderr)
        return 1

    kept = filter_repos(repos, include_forks=args.include_forks, exclude=args.exclude)
    summaries = sort_repos([summarize_repo(repo) for repo in kept])

    if args.limit is not None:
        summaries = summaries[:args.limit]

    page = render_page(summaries, args.user, datetime.now(timezone.utc))

    try:
        write_page(page, args.out)
    except OSError as error:
        print("error: could not write {0}: {1}".format(args.out, error), file=sys.stderr)
        return 1

    print("Wrote {0} repository entries to {1}".format(len(summaries), args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())

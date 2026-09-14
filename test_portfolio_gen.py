"""Tests for portfolio_gen.py.

Every test here runs on plain dicts shaped like the GitHub API response.
Nothing touches the network - fetch_repos is deliberately the only impure
function, and it is deliberately not tested.
"""

from datetime import datetime, timezone

import portfolio_gen as pg


def repo(**overrides):
    """A GitHub-shaped repo dict with sensible defaults, overridable per test."""
    base = {
        "name": "example",
        "description": "An example repository.",
        "html_url": "https://github.com/someone/example",
        "language": "Python",
        "stargazers_count": 0,
        "pushed_at": "2026-09-08T10:30:00Z",
        "private": False,
        "archived": False,
        "fork": False,
    }
    base.update(overrides)
    return base


# --- filter_repos ---------------------------------------------------------

def test_keeps_an_ordinary_public_repo():
    assert pg.filter_repos([repo()]) == [repo()]


def test_drops_private_repos():
    assert pg.filter_repos([repo(private=True)]) == []


def test_drops_archived_repos():
    assert pg.filter_repos([repo(archived=True)]) == []


def test_drops_forks_by_default():
    assert pg.filter_repos([repo(fork=True)]) == []


def test_keeps_forks_when_asked():
    assert len(pg.filter_repos([repo(fork=True)], include_forks=True)) == 1


def test_exclude_is_case_insensitive():
    assert pg.filter_repos([repo(name="Dotfiles")], exclude=["dotfiles"]) == []


def test_exclude_leaves_other_repos_alone():
    repos = [repo(name="keep"), repo(name="drop")]
    kept = pg.filter_repos(repos, exclude=["drop"])
    assert [item["name"] for item in kept] == ["keep"]


# --- parse_timestamp ------------------------------------------------------

def test_parses_a_github_timestamp():
    parsed = pg.parse_timestamp("2026-09-08T10:30:00Z")
    assert parsed == datetime(2026, 9, 8, 10, 30, tzinfo=timezone.utc)


def test_missing_timestamp_returns_none():
    assert pg.parse_timestamp(None) is None


def test_malformed_timestamp_returns_none():
    assert pg.parse_timestamp("not a date") is None


# --- summarize_repo -------------------------------------------------------

def test_null_description_becomes_empty_string():
    assert pg.summarize_repo(repo(description=None))["description"] == ""


def test_null_language_becomes_empty_string():
    assert pg.summarize_repo(repo(language=None))["language"] == ""


def test_description_whitespace_is_stripped():
    assert pg.summarize_repo(repo(description="  spaced  "))["description"] == "spaced"


def test_missing_name_falls_back_to_untitled():
    assert pg.summarize_repo({})["name"] == "untitled"


# --- sort_repos -----------------------------------------------------------

def test_newest_push_comes_first():
    old = pg.summarize_repo(repo(name="old", pushed_at="2026-01-01T00:00:00Z"))
    new = pg.summarize_repo(repo(name="new", pushed_at="2026-09-01T00:00:00Z"))
    assert [item["name"] for item in pg.sort_repos([old, new])] == ["new", "old"]


def test_repos_without_a_timestamp_sink_to_the_bottom():
    dated = pg.summarize_repo(repo(name="dated"))
    undated = pg.summarize_repo(repo(name="undated", pushed_at=None))
    assert [item["name"] for item in pg.sort_repos([undated, dated])] == ["dated", "undated"]


# --- render_repo ----------------------------------------------------------

def test_renders_a_markdown_heading_with_a_link():
    block = pg.render_repo(pg.summarize_repo(repo()))
    assert block.startswith("### [example](https://github.com/someone/example)")


def test_never_prints_the_word_none_for_a_null_description():
    block = pg.render_repo(pg.summarize_repo(repo(description=None)))
    assert "None" not in block


def test_stars_are_hidden_when_there_are_none():
    block = pg.render_repo(pg.summarize_repo(repo(stargazers_count=0)))
    assert "stars" not in block


def test_stars_are_shown_when_there_are_some():
    block = pg.render_repo(pg.summarize_repo(repo(stargazers_count=12)))
    assert "12 stars" in block


# --- render_page ----------------------------------------------------------

def test_empty_portfolio_renders_a_placeholder_instead_of_crashing():
    page = pg.render_page([], "someone", datetime(2026, 9, 14, tzinfo=timezone.utc))
    assert "_No public repositories yet._" in page


def test_page_carries_the_username_as_the_title():
    page = pg.render_page([], "honore", datetime(2026, 9, 14, tzinfo=timezone.utc))
    assert page.startswith("# honore")


def test_page_ends_with_exactly_one_newline():
    page = pg.render_page([pg.summarize_repo(repo())], "someone",
                          datetime(2026, 9, 14, tzinfo=timezone.utc))
    assert page.endswith("\n") and not page.endswith("\n\n")


# --- describe_http_error --------------------------------------------------

def test_404_names_the_missing_user():
    assert "nosuchuser" in pg.describe_http_error(404, "nosuchuser")


def test_403_explains_the_rate_limit():
    assert "rate limit" in pg.describe_http_error(403, "someone")

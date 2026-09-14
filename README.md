# portfolio-gen

Generates the Markdown page for my GitHub Pages portfolio from the GitHub API,
so I stop editing it by hand every time I push a new project.

## What it does

Fetches every public repository for a given GitHub user and writes a Markdown
page listing each one with its description, primary language, star count and
last-push date, newest first. Forks, archived repos and private repos are left
out by default.

## Why I built it

I was keeping a portfolio page up to date manually. Every new repo meant
another block of Markdown copied from the last one, and the "last updated"
dates went stale within a week. The GitHub API already knows all of this, so
the page should generate itself.

## How to run it

Python 3.8 or newer. No dependencies - standard library only.

```
python portfolio_gen.py --user YOUR_USERNAME --out docs/index.md
```

Options:

| Flag | Effect |
| --- | --- |
| `--user` | GitHub username (required) |
| `--out` | Output path (default `docs/index.md`) |
| `--include-forks` | Include forked repositories |
| `--exclude NAME ...` | Leave specific repositories out |
| `--limit N` | List at most N repositories |

Unauthenticated requests are capped at 60/hour by GitHub. To raise that to
5,000/hour, set a token in the environment:

```
export GITHUB_TOKEN=ghp_your_token_here
python portfolio_gen.py --user YOUR_USERNAME
```

The token is read from the environment only - it is never written to the
output file or stored in the repository.

## Example output

```markdown
# honore-nduwayo

Public projects, generated from the GitHub API.

## Projects

### [portfolio-gen](https://github.com/honore-nduwayo/portfolio-gen)

Generates my portfolio page from the GitHub API.

`Python` · updated 14 Sep 2026

### [cs50p-final-project](https://github.com/honore-nduwayo/cs50p-final-project)

CLI log analyzer and intrusion detection script.

`Python` · 3 stars · updated 8 Sep 2026

---

Generated 14 Sep 2026 by `portfolio_gen.py`.
```

## Tests

```
pip install pytest
python -m pytest
```

25 tests covering filtering, timestamp parsing, field normalisation, sorting
and rendering. They run on dicts shaped like the API response, so the suite
needs no network access. `fetch_repos` is the only function that makes a
request, and it is kept deliberately thin for that reason.

## Notes

- The API returns up to 100 repositories per page and this script requests one
  page. Past 100 public repos it would need pagination.
- GitHub sends `null` rather than an empty string for missing descriptions and
  for the language of an empty repo. Both are normalised in `summarize_repo`
  so the rendered page never prints `None`.

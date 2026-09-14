# portfolio-gen

A small Python script that builds the project list for my portfolio page straight from the GitHub API, so I never have to update it by hand again.

## What it does

You give it a GitHub username. It fetches every public repository that user owns and writes a Markdown page listing each one with its description, main language, star count and the date it was last pushed to. The newest work appears first. Forks, archived repositories and private repositories are left out unless you ask for them.

## Why I built it

I was maintaining my portfolio page manually. Every time I pushed a new project I copied the previous block of Markdown, changed the name and the link, and moved on. Within a week the "last updated" dates were wrong again, and after a few rounds of this the page said less about my work than my GitHub profile already did.

GitHub already stores all of this. The page should build itself.

## Running it

You need Python 3.8 or newer. There is nothing to install: the script uses only the standard library.

```
python portfolio_gen.py --user YOUR_USERNAME --out docs/index.md
```

Five options are available:

`--user` is the GitHub username you want to generate a page for. This one is required.

`--out` is where the file gets written. It defaults to `docs/index.md`, which is the path GitHub Pages looks for.

`--include-forks` adds forked repositories, which are skipped by default.

`--exclude` takes one or more repository names to leave off the page. Useful for coursework or scratch repos you would rather not feature.

`--limit` caps how many repositories appear, for when you only want your best few.

## About the rate limit

GitHub allows 60 API requests an hour from an address with no credentials attached. That is plenty for normal use, but if you hit it the script will tell you so clearly instead of crashing. Setting a personal access token raises the ceiling to 5,000 an hour:

```
export GITHUB_TOKEN=your_token_here
python portfolio_gen.py --user YOUR_USERNAME
```

The script reads the token from your environment and nowhere else. It never lands in the output file and it is never written to the repository.

## What the output looks like

```markdown
# honore-nduwayo

Public projects, generated from the GitHub API.

## Projects

### [portfolio-gen](https://github.com/honore-nduwayo/portfolio-gen)

Generates my portfolio page from the GitHub API.

`Python` · updated 14 Sep 2026

### [cs50p-final-project](https://github.com/honore-nduwayo/cs50p-final-project)

CLI log analyzer and intrusion detection script. CS50P final project.

`Python` · updated 13 Sep 2026
```

## Tests

```
pip install pytest
python -m pytest
```

There are 25 tests covering filtering, timestamp parsing, field cleanup, sorting and rendering. They run on dictionaries shaped the way GitHub sends them, so nothing in the suite touches the network and the tests pass on a plane.

That is deliberate. `fetch_repos` is the only function that makes a request, and it does nothing except make that request and hand back the result. Everything else is a plain function operating on plain data, which is what makes the whole thing testable.

## Things worth knowing

GitHub returns up to 100 repositories in a single response and the script asks for one page. If you ever pass 100 public repositories it would need pagination added.

When a repository has no description, or when it is empty and has no detected language, GitHub sends back `null` rather than an empty string. Both cases are cleaned up in `summarize_repo`, so the finished page never prints the word `None` at a visitor.

The generated page is output, not source. I keep it out of version control and regenerate it whenever I push something new.

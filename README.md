# GitHub Management CLI (`ghm`)

A Python CLI tool to manage GitHub organization repository settings, with a focus on standardizing merge commit message formats across all repositories.

## Features

- **Flexible targeting**: Manage entire organizations, specific users, or individual repositories (`owner/repo`)
- **Bulk repository management**: Update merge/squash settings across multiple repositories at once
- **Smart authentication**: Automatically uses `gh` CLI token, with fallback to `GITHUB_TOKEN` env var
- **Safe by default**: Dry-run mode shows what would change before applying updates
- **Progress tracking**: Real-time progress bars for long-running operations
- **Filtering**: Skip archived repos and forks by default
- **Summary reports**: See which repos need attention at a glance

## Installation

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- [gh CLI](https://cli.github.com/) (optional, but recommended for auth)

### Quick Start

```bash
# Clone or navigate to the project
cd ~/git/github-management

# Run directly with uv (no installation needed)
uv run ghm --help

# Or install as a tool
uv tool install .

# Now you can use it anywhere
ghm --help
```

## Authentication

`ghm` will automatically find your GitHub token in this order:

1. `--token` flag (if provided)
2. `GITHUB_TOKEN` environment variable
3. `gh` CLI (`gh auth token`)

**Recommended**: Just use `gh` CLI:

```bash
gh auth login
# Then ghm will automatically use your gh token
```

## Usage

### List Repository Settings

Get a summary of merge settings across your target (organization, user, or single repository):

```bash
# Target an organization
uv run ghm repos list acme-uk

# Target a user
uv run ghm repos list octocat

# Target a single repository
uv run ghm repos list acme-uk/backbone

# Verbose table view
uv run ghm repos list acme-uk --verbose

# Include archived and forked repos (for orgs/users)
uv run ghm repos list acme-uk --include-archived --include-forks
```

**Example output:**

```
Summary:
  Total repositories: 70
  Squash merge enabled: 70
    - Using PR_TITLE + PR_BODY: 18
    - Need update: 52
  Merge commit enabled: 41
    - Using PR_TITLE + PR_TITLE: 0
    - Need update: 41

Repositories needing updates (53):
  acme-uk/backbone: squash_msg=COMMIT_MESSAGES
  acme-uk/.github: squash_title=COMMIT_OR_PR_TITLE, squash_msg=COMMIT_MESSAGES, merge_title=MERGE_MESSAGE
  ...
```

### Update Merge Settings

#### Quick Fix: Squash to PR Title + Body

The most common use case - set squash merge to use PR title and description:

```bash
# Dry run (shows what would change)
uv run ghm repos fix-squash acme-uk

# Apply the changes
uv run ghm repos fix-squash acme-uk --apply
```

#### Full Control: Custom Merge Settings

Update both squash and merge commit settings with custom values:

```bash
# Update squash merge settings
uv run ghm repos update-merge acme-uk \
  --squash-title PR_TITLE \
  --squash-message PR_BODY \
  --apply

# Update merge commit settings
uv run ghm repos update-merge acme-uk \
  --merge-title PR_TITLE \
  --merge-message PR_TITLE \
  --apply

# Update both at once
uv run ghm repos update-merge acme-uk \
  --squash-title PR_TITLE \
  --squash-message PR_BODY \
  --merge-title PR_TITLE \
  --merge-message PR_TITLE \
  --apply
```

**Valid values for merge settings:**

- **Squash title**: `PR_TITLE`, `COMMIT_OR_PR_TITLE`
- **Squash message**: `PR_BODY`, `COMMIT_MESSAGES`, `BLANK`
- **Merge title**: `PR_TITLE`, `MERGE_MESSAGE`
- **Merge message**: `PR_TITLE`, `PR_BODY`, `BLANK`

### Filtering Options

All commands support filtering:

```bash
# Skip archived repos (default)
uv run ghm repos list acme-uk

# Include archived repos
uv run ghm repos list acme-uk --include-archived

# Include forked repos
uv run ghm repos list acme-uk --include-forks

# Include everything
uv run ghm repos list acme-uk --include-archived --include-forks
```

## Common Workflows

### Standardize squash merge across org or repo

**Use case**: You want all repos (or a specific one) to use PR title + description for squash merges.

```bash
# Preview changes for a single repo
uv run ghm repos fix-squash acme-uk/backbone

# Apply changes to an entire org
uv run ghm repos fix-squash acme-uk --apply
```

### Set merge commits to use PR title

**Use case**: You want merge commits to use the PR title only.

```bash
# 1. Check current state
uv run ghm repos list acme-uk

# 2. Preview changes
uv run ghm repos update-merge acme-uk \
  --merge-title PR_TITLE \
  --merge-message PR_TITLE

# 3. Apply changes
uv run ghm repos update-merge acme-uk \
  --merge-title PR_TITLE \
  --merge-message PR_TITLE \
  --apply
```

### Audit repos that need attention

```bash
# Get summary of repos needing updates
uv run ghm repos list acme-uk | grep -A 50 "needing updates"
```

## Performance Notes

- Fetching the repo list is fast (~5 seconds for 77 repos)
- Fetching merge settings requires 1 API call per repo (~0.6s each)
- For 70 repos, expect ~45 seconds total for list command
- Updates are applied in sequence with progress tracking

## Troubleshooting

### No GitHub token found

```
Error: No GitHub token found. Please either:
  1. Set GITHUB_TOKEN environment variable
  2. Log in with: gh auth login
  3. Pass token explicitly with --token
```

**Solution**: Run `gh auth login` or set `GITHUB_TOKEN` environment variable.

### Permission denied (403 or 404)

```
Error: 403 Resource not accessible by personal access token
```

OR

```
✗ acme-uk/backbone: Failed - 404 {"message": "Not Found", ...}
```

**Note on 404s**: GitHub's API often returns `404 Not Found` instead of `403 Forbidden` if your token lacks the necessary write scopes or if you don't have administrative access to the repository.

**Solution**: Ensure your token has `repo` or `write:org` scope and that you have Admin/Maintainer permissions. With `gh` CLI:

```bash
gh auth refresh -s repo
```

If the organization requires SAML SSO, ensure your token is authorized for that organization.

### Command takes too long

**Explanation**: PyGithub makes 1 API call per repository to fetch merge settings. For large orgs (100+ repos), this can take 1-2 minutes.

**Workaround**: Use `--include-archived` and `--include-forks` flags sparingly to reduce the number of repos fetched.

## Project Structure

```
github-management/
├── src/
│   └── github_mgmt/
│       ├── __init__.py
│       ├── main.py          # Typer CLI app
│       ├── auth.py           # Authentication (gh CLI fallback)
│       ├── repos.py          # Repository operations
│       └── output.py         # Rich output formatting (future)
├── tests/
├── pyproject.toml
├── README.md
└── .gitignore
```

## Development

```bash
# Install dependencies
cd ~/git/github-management
uv sync

# Run tests (when available)
uv run pytest

# Format code
uv run ruff format

# Lint
uv run ruff check
```

## Why This Tool?

**Problem**: GitHub doesn't provide an org-level setting to enforce merge commit message formats. Each repository has its own settings for:

- Squash merge commit title/message
- Merge commit title/message

**Solution**: This CLI tool lets you:

1. Audit current settings across all repos
2. Bulk update settings to match your org's standards
3. Re-run periodically or after adding new repos

**Recommended settings** (for clean, PR-focused commit history):

- Squash merge: `PR_TITLE` + `PR_BODY`
- Merge commit: `PR_TITLE` + `PR_TITLE`

## License

MIT

## Contributing

PRs welcome! This tool was built with:

- [uv](https://github.com/astral-sh/uv) - Fast Python package manager
- [typer](https://typer.tiangolo.com/) - Modern CLI framework
- [PyGithub](https://github.com/PyGithub/PyGithub) - GitHub API client
- [rich](https://github.com/Textualize/rich) - Terminal formatting

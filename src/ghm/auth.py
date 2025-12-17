"""GitHub authentication helper with gh CLI fallback."""

import os
import subprocess
from typing import Optional

from github import Auth, Github
from rich.console import Console

console = Console()


def get_github_token(token: Optional[str] = None) -> str:
    """
    Get GitHub token from multiple sources in priority order:
    1. Explicit token argument
    2. GITHUB_TOKEN environment variable
    3. gh CLI (via `gh auth token`)

    Args:
        token: Explicitly provided token

    Returns:
        GitHub token string

    Raises:
        ValueError: If no token can be found
    """
    # 1. Explicit token
    if token:
        return token

    # 2. Environment variable
    env_token = os.getenv("GITHUB_TOKEN")
    if env_token:
        console.print("[dim]Using token from GITHUB_TOKEN environment variable[/dim]")
        return env_token

    # 3. gh CLI fallback
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True,
        )
        gh_token = result.stdout.strip()
        if gh_token:
            console.print("[dim]Using token from gh CLI (gh auth token)[/dim]")
            return gh_token
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    raise ValueError(
        "No GitHub token found. Please either:\n"
        "  1. Set GITHUB_TOKEN environment variable\n"
        "  2. Log in with: gh auth login\n"
        "  3. Pass token explicitly with --token"
    )


def create_github_client(
    token: Optional[str] = None,
    base_url: str = "https://api.github.com",
) -> Github:
    """
    Create authenticated GitHub client.

    Args:
        token: Optional explicit token
        base_url: GitHub API base URL (for enterprise instances)

    Returns:
        Authenticated Github client instance
    """
    github_token = get_github_token(token)
    auth = Auth.Token(github_token)
    return Github(auth=auth, base_url=base_url)

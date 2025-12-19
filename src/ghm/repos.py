"""Repository management operations."""

from dataclasses import dataclass
from typing import List, Optional

from github import Github, Repository, Organization, NamedUser
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
)
from rich.table import Table

console = Console()


@dataclass
class RepoSettings:
    """Repository merge settings."""

    name: str
    full_name: str
    is_archived: bool
    is_fork: bool
    allow_squash_merge: bool
    squash_merge_commit_title: Optional[str]
    squash_merge_commit_message: Optional[str]
    allow_merge_commit: bool
    merge_commit_title: Optional[str]
    merge_commit_message: Optional[str]
    allow_rebase_merge: bool

    @classmethod
    def from_repo(cls, repo: Repository.Repository) -> "RepoSettings":
        """Create RepoSettings from PyGithub Repository object."""
        return cls(
            name=repo.name,
            full_name=repo.full_name,
            is_archived=repo.archived,
            is_fork=repo.fork,
            allow_squash_merge=repo.allow_squash_merge,
            squash_merge_commit_title=repo.squash_merge_commit_title,
            squash_merge_commit_message=repo.squash_merge_commit_message,
            allow_merge_commit=repo.allow_merge_commit,
            merge_commit_title=repo.merge_commit_title,
            merge_commit_message=repo.merge_commit_message,
            allow_rebase_merge=repo.allow_rebase_merge,
        )

    def needs_squash_update(
        self, title: str = "PR_TITLE", message: str = "PR_BODY"
    ) -> bool:
        """Check if squash merge settings need updating."""
        if not self.allow_squash_merge:
            return False
        return (
            self.squash_merge_commit_title != title
            or self.squash_merge_commit_message != message
        )

    def needs_merge_update(
        self, title: str = "PR_TITLE", message: str = "PR_TITLE"
    ) -> bool:
        """Check if merge commit settings need updating."""
        if not self.allow_merge_commit:
            return False
        return self.merge_commit_title != title or self.merge_commit_message != message


def get_target_repos(
    github_client: Github,
    target: str,
    include_archived: bool = False,
    include_forks: bool = False,
) -> List[RepoSettings]:
    """
    Get repository settings for a target (repo, org, or user).

    Args:
        github_client: Authenticated GitHub client
        target: Target identifier (e.g., 'org', 'user', or 'owner/repo')
        include_archived: Include archived repositories
        include_forks: Include forked repositories

    Returns:
        List of RepoSettings objects
    """
    # Check if target is a single repository
    if "/" in target:
        console.print(f"[dim]Fetching single repository {target}...[/dim]")
        repo = github_client.get_repo(target)
        return [RepoSettings.from_repo(repo)]

    # Otherwise, treat as an organization or user
    try:
        # Try organization first
        owner = github_client.get_organization(target)
        console.print(f"[dim]Fetching repositories from organization {target}...[/dim]")
    except Exception:
        # Fallback to user
        owner = github_client.get_user(target)
        console.print(f"[dim]Fetching repositories from user {target}...[/dim]")

    all_repos = list(owner.get_repos())
    console.print(f"[dim]Found {len(all_repos)} total repositories[/dim]")

    filtered_repos = []
    skipped_archived = 0
    skipped_forks = 0

    for repo in all_repos:
        if not include_archived and repo.archived:
            skipped_archived += 1
            continue
        if not include_forks and repo.fork:
            skipped_forks += 1
            continue
        filtered_repos.append(repo)

    if skipped_archived > 0:
        console.print(f"[dim]Skipping {skipped_archived} archived repositories[/dim]")
    if skipped_forks > 0:
        console.print(f"[dim]Skipping {skipped_forks} forked repositories[/dim]")

    # Fetch detailed settings
    return fetch_repos_settings(filtered_repos)


def fetch_repos_settings(repos: List[Repository.Repository]) -> List[RepoSettings]:
    """Fetch detailed merge settings for a list of repositories."""
    if not repos:
        return []

    # Skip progress bar for single repo
    if len(repos) == 1:
        return [RepoSettings.from_repo(repos[0])]

    repos_settings = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching merge settings...", total=len(repos))

        for repo in repos:
            settings = RepoSettings.from_repo(repo)
            repos_settings.append(settings)
            progress.update(task, advance=1)

    return repos_settings


def display_repos_table(repos: List[RepoSettings], verbose: bool = False) -> None:
    """Display repositories in a formatted table."""

    if not verbose:
        # Summary view: only show counts and repos that need attention
        console.print("\n[bold]Summary:[/bold]")

        squash_enabled = sum(1 for r in repos if r.allow_squash_merge)
        merge_enabled = sum(1 for r in repos if r.allow_merge_commit)

        # Count squash settings
        squash_pr_title_body = sum(
            1
            for r in repos
            if r.allow_squash_merge
            and r.squash_merge_commit_title == "PR_TITLE"
            and r.squash_merge_commit_message == "PR_BODY"
        )
        squash_needs_update = squash_enabled - squash_pr_title_body

        # Count merge settings
        merge_pr_title = sum(
            1
            for r in repos
            if r.allow_merge_commit
            and r.merge_commit_title == "PR_TITLE"
            and r.merge_commit_message == "PR_TITLE"
        )
        merge_needs_update = merge_enabled - merge_pr_title

        console.print(f"  Total repositories: {len(repos)}")
        console.print(f"  Squash merge enabled: {squash_enabled}")
        console.print(f"    - Using PR_TITLE + PR_BODY: {squash_pr_title_body}")
        if squash_needs_update > 0:
            console.print(f"    - [yellow]Need update: {squash_needs_update}[/yellow]")
        console.print(f"  Merge commit enabled: {merge_enabled}")
        console.print(f"    - Using PR_TITLE + PR_TITLE: {merge_pr_title}")
        if merge_needs_update > 0:
            console.print(f"    - [yellow]Need update: {merge_needs_update}[/yellow]")

        # Show repos that need updates
        needs_attention = [
            r
            for r in repos
            if (
                r.allow_squash_merge
                and (
                    r.squash_merge_commit_title != "PR_TITLE"
                    or r.squash_merge_commit_message != "PR_BODY"
                )
            )
            or (
                r.allow_merge_commit
                and (
                    r.merge_commit_title != "PR_TITLE"
                    or r.merge_commit_message != "PR_TITLE"
                )
            )
        ]

        if needs_attention:
            console.print(
                f"\n[yellow]Repositories needing updates ({len(needs_attention)}):[/yellow]"
            )
            for repo in needs_attention[:10]:  # Show first 10
                issues = []
                if repo.allow_squash_merge:
                    if repo.squash_merge_commit_title != "PR_TITLE":
                        issues.append(f"squash_title={repo.squash_merge_commit_title}")
                    if repo.squash_merge_commit_message != "PR_BODY":
                        issues.append(f"squash_msg={repo.squash_merge_commit_message}")
                if repo.allow_merge_commit:
                    if repo.merge_commit_title != "PR_TITLE":
                        issues.append(f"merge_title={repo.merge_commit_title}")
                    if repo.merge_commit_message != "PR_TITLE":
                        issues.append(f"merge_msg={repo.merge_commit_message}")
                console.print(f"  {repo.full_name}: {', '.join(issues)}")

            if len(needs_attention) > 10:
                console.print(f"  ... and {len(needs_attention) - 10} more")

        return

    # Verbose view: full table
    table = Table(title="Repository Merge Settings (Verbose)")

    table.add_column("Repository", style="cyan", no_wrap=False)
    table.add_column("Squash", justify="center", style="green")
    table.add_column("Squash Title", style="blue")
    table.add_column("Squash Msg", style="blue")
    table.add_column("Merge", justify="center", style="green")
    table.add_column("Merge Title", style="blue")
    table.add_column("Merge Msg", style="blue")

    for repo in repos:
        # Abbreviate common values
        squash_title = repo.squash_merge_commit_title or "—"
        squash_msg = repo.squash_merge_commit_message or "—"
        merge_title = repo.merge_commit_title or "—"
        merge_msg = repo.merge_commit_message or "—"

        table.add_row(
            repo.full_name,
            "✓" if repo.allow_squash_merge else "—",
            squash_title,
            squash_msg,
            "✓" if repo.allow_merge_commit else "—",
            merge_title,
            merge_msg,
        )

    console.print(table)


def update_repo_settings(
    github_client: Github,
    repo_full_name: str,
    squash_title: Optional[str] = None,
    squash_message: Optional[str] = None,
    merge_title: Optional[str] = None,
    merge_message: Optional[str] = None,
    dry_run: bool = True,
) -> bool:
    """
    Update repository merge settings.

    Args:
        github_client: Authenticated GitHub client
        repo_full_name: Full repository name (org/repo)
        squash_title: Squash merge commit title
        squash_message: Squash merge commit message
        merge_title: Merge commit title
        merge_message: Merge commit message
        dry_run: If True, only show what would change

    Returns:
        True if update succeeded or would succeed in dry-run
    """
    repo = github_client.get_repo(repo_full_name)
    settings = RepoSettings.from_repo(repo)

    changes = {}

    # Determine what needs updating
    if squash_title and settings.allow_squash_merge:
        if settings.squash_merge_commit_title != squash_title:
            changes["squash_merge_commit_title"] = squash_title

    if squash_message and settings.allow_squash_merge:
        if settings.squash_merge_commit_message != squash_message:
            changes["squash_merge_commit_message"] = squash_message

    if merge_title and settings.allow_merge_commit:
        if settings.merge_commit_title != merge_title:
            changes["merge_commit_title"] = merge_title

    if merge_message and settings.allow_merge_commit:
        if settings.merge_commit_message != merge_message:
            changes["merge_commit_message"] = merge_message

    if not changes:
        console.print(f"[dim]{repo_full_name}: No changes needed[/dim]")
        return True

    if dry_run:
        console.print(f"[yellow]{repo_full_name}: Would update:[/yellow]")
        for key, value in changes.items():
            console.print(f"  {key}: {value}")
        return True

    try:
        repo.edit(**changes)
        console.print(f"[green]✓ {repo_full_name}: Updated successfully[/green]")
        return True
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            error_msg = (
                "404 Not Found (Check permissions or if target is an organization)"
            )
        console.print(f"[red]✗ {repo_full_name}: Failed - {error_msg}[/red]")
        return False


def bulk_update_repos(
    github_client: Github,
    repos: List[RepoSettings],
    squash_title: Optional[str] = None,
    squash_message: Optional[str] = None,
    merge_title: Optional[str] = None,
    merge_message: Optional[str] = None,
    dry_run: bool = True,
) -> tuple[int, int]:
    """
    Bulk update repository settings.

    Args:
        github_client: Authenticated GitHub client
        repos: List of repositories to update
        squash_title: Squash merge commit title
        squash_message: Squash merge commit message
        merge_title: Merge commit title
        merge_message: Merge commit message
        dry_run: If True, only show what would change

    Returns:
        Tuple of (success_count, total_count)
    """
    success_count = 0
    total_count = 0

    for repo_settings in repos:
        # Skip if repo doesn't need any updates
        needs_update = False

        if squash_title or squash_message:
            if repo_settings.allow_squash_merge:
                needs_update = True

        if merge_title or merge_message:
            if repo_settings.allow_merge_commit:
                needs_update = True

        if not needs_update:
            console.print(
                f"[dim]{repo_settings.full_name}: No applicable merge methods enabled[/dim]"
            )
            continue

        total_count += 1
        if update_repo_settings(
            github_client,
            repo_settings.full_name,
            squash_title=squash_title,
            squash_message=squash_message,
            merge_title=merge_title,
            merge_message=merge_message,
            dry_run=dry_run,
        ):
            success_count += 1

    return success_count, total_count

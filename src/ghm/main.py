"""GitHub Management CLI - Main entry point."""

from typing import Optional

import typer
from rich.console import Console

from ghm.auth import create_github_client
from ghm.repos import (
    bulk_update_repos,
    display_repos_table,
    list_org_repos,
)

app = typer.Typer(
    name="ghm",
    help="GitHub Management CLI - Manage organization repository settings",
    no_args_is_help=True,
)

repos_app = typer.Typer(
    help="Repository management commands",
    no_args_is_help=True,
)
app.add_typer(repos_app, name="repos")

console = Console()


@repos_app.command("list")
def list_repos(
    org: str = typer.Argument(..., help="Organization name"),
    include_archived: bool = typer.Option(
        False, "--include-archived", help="Include archived repositories"
    ),
    include_forks: bool = typer.Option(
        False, "--include-forks", help="Include forked repositories"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Show full table instead of summary"
    ),
    token: Optional[str] = typer.Option(
        None, "--token", help="GitHub token (defaults to gh CLI or GITHUB_TOKEN env)"
    ),
):
    """List all repositories in an organization with their merge settings."""
    try:
        github_client = create_github_client(token=token)
        repos = list_org_repos(
            github_client,
            org,
            include_archived=include_archived,
            include_forks=include_forks,
        )

        display_repos_table(repos, verbose=verbose)

        github_client.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@repos_app.command("update-merge")
def update_merge_settings(
    org: str = typer.Argument(..., help="Organization name"),
    squash_title: Optional[str] = typer.Option(
        None,
        "--squash-title",
        help="Squash merge commit title (e.g., PR_TITLE, COMMIT_OR_PR_TITLE)",
    ),
    squash_message: Optional[str] = typer.Option(
        None,
        "--squash-message",
        help="Squash merge commit message (e.g., PR_BODY, COMMIT_MESSAGES, BLANK)",
    ),
    merge_title: Optional[str] = typer.Option(
        None,
        "--merge-title",
        help="Merge commit title (e.g., PR_TITLE, MERGE_MESSAGE)",
    ),
    merge_message: Optional[str] = typer.Option(
        None,
        "--merge-message",
        help="Merge commit message (e.g., PR_TITLE, PR_BODY, BLANK)",
    ),
    include_archived: bool = typer.Option(
        False, "--include-archived", help="Include archived repositories"
    ),
    include_forks: bool = typer.Option(
        False, "--include-forks", help="Include forked repositories"
    ),
    dry_run: bool = typer.Option(
        True, "--dry-run/--apply", help="Dry run mode (default: True)"
    ),
    token: Optional[str] = typer.Option(
        None, "--token", help="GitHub token (defaults to gh CLI or GITHUB_TOKEN env)"
    ),
):
    """
    Update merge commit settings for all repositories in an organization.

    Common patterns:
      - Squash to PR title + body: --squash-title PR_TITLE --squash-message PR_BODY
      - Merge to PR title: --merge-title PR_TITLE --merge-message PR_TITLE
    """
    if not any([squash_title, squash_message, merge_title, merge_message]):
        console.print(
            "[red]Error: At least one merge setting must be specified[/red]\n"
            "Use --squash-title, --squash-message, --merge-title, or --merge-message"
        )
        raise typer.Exit(1)

    try:
        github_client = create_github_client(token=token)

        console.print(f"[bold]Organization:[/bold] {org}")
        if dry_run:
            console.print(
                "[yellow]Mode: DRY RUN (use --apply to make changes)[/yellow]\n"
            )
        else:
            console.print("[red]Mode: APPLY (making real changes)[/red]\n")

        repos = list_org_repos(
            github_client,
            org,
            include_archived=include_archived,
            include_forks=include_forks,
        )

        console.print(f"\n[bold]Found {len(repos)} repositories[/bold]\n")

        success, total = bulk_update_repos(
            github_client,
            repos,
            squash_title=squash_title,
            squash_message=squash_message,
            merge_title=merge_title,
            merge_message=merge_message,
            dry_run=dry_run,
        )

        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Processed: {total} repositories")
        if dry_run:
            console.print(f"  Would update: {success} repositories")
            console.print("\n[yellow]Run with --apply to make changes[/yellow]")
        else:
            console.print(f"  [green]Updated: {success} repositories[/green]")
            if success < total:
                console.print(f"  [red]Failed: {total - success} repositories[/red]")

        github_client.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@repos_app.command("fix-squash")
def fix_squash_defaults(
    org: str = typer.Argument(..., help="Organization name"),
    include_archived: bool = typer.Option(
        False, "--include-archived", help="Include archived repositories"
    ),
    include_forks: bool = typer.Option(
        False, "--include-forks", help="Include forked repositories"
    ),
    dry_run: bool = typer.Option(
        True, "--dry-run/--apply", help="Dry run mode (default: True)"
    ),
    token: Optional[str] = typer.Option(
        None, "--token", help="GitHub token (defaults to gh CLI or GITHUB_TOKEN env)"
    ),
):
    """
    Quick fix: Set squash merge to use PR title + body (most common use case).

    This is a convenience command equivalent to:
      ghm repos update-merge ORG --squash-title PR_TITLE --squash-message PR_BODY
    """
    try:
        github_client = create_github_client(token=token)

        console.print(f"[bold]Organization:[/bold] {org}")
        console.print("[bold]Action:[/bold] Set squash merge to PR_TITLE + PR_BODY\n")
        if dry_run:
            console.print(
                "[yellow]Mode: DRY RUN (use --apply to make changes)[/yellow]\n"
            )
        else:
            console.print("[red]Mode: APPLY (making real changes)[/red]\n")

        repos = list_org_repos(
            github_client,
            org,
            include_archived=include_archived,
            include_forks=include_forks,
        )

        console.print(f"\n[bold]Found {len(repos)} repositories[/bold]\n")

        success, total = bulk_update_repos(
            github_client,
            repos,
            squash_title="PR_TITLE",
            squash_message="PR_BODY",
            dry_run=dry_run,
        )

        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Processed: {total} repositories")
        if dry_run:
            console.print(f"  Would update: {success} repositories")
            console.print("\n[yellow]Run with --apply to make changes[/yellow]")
        else:
            console.print(f"  [green]Updated: {success} repositories[/green]")
            if success < total:
                console.print(f"  [red]Failed: {total - success} repositories[/red]")

        github_client.close()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()

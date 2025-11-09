"""Command-line interface for Music Keepers."""

from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from .core.config import Config
from .core.database import DatabaseManager
from .core.scanner import LibraryScanner
from .organizer.file_organizer import FileOrganizer
from .cleaner.duplicates import DuplicateDetector
from .discovery.recommendations import MusicDiscovery
from .curator.playlists import PlaylistManager

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Music Keepers - Intelligent Music Library Management.

    An agent for organizing, discovering, cleaning, and curating your music library.
    """
    pass


@main.command()
@click.argument('library_path', type=click.Path(exists=True), required=False)
def init(library_path: Optional[str]):
    """Initialize Music Keepers with your music library.

    LIBRARY_PATH: Path to your music library (optional, defaults to ~/Music)
    """
    console.print("[cyan]Initializing Music Keepers...[/cyan]")

    config = Config()

    if library_path:
        config.set('library.path', library_path)
        console.print(f"[green]Library path set to:[/green] {library_path}")

    db_manager = DatabaseManager(config.database_path)
    db_manager.init_db()

    console.print(f"[green]Database initialized at:[/green] {config.database_path}")
    console.print("\n[green]✓[/green] Music Keepers initialized successfully!")
    console.print("\n[cyan]Next steps:[/cyan]")
    console.print("  1. Run 'music-keepers scan' to index your library")
    console.print("  2. Run 'music-keepers --help' to see available commands")


@main.command()
@click.option('--path', type=click.Path(exists=True), help='Path to scan (defaults to configured library path)')
def scan(path: Optional[str]):
    """Scan and index your music library."""
    config = Config()
    db_manager = DatabaseManager(config.database_path)
    scanner = LibraryScanner(config, db_manager)

    scan_path = Path(path) if path else None

    console.print("[cyan]Scanning library...[/cyan]")
    count = scanner.scan_library(scan_path)
    console.print(f"\n[green]✓[/green] Scanned {count} tracks")


@main.command()
@click.option('--pattern', help='Organization pattern (e.g., "{artist}/{album}/{track} - {title}")')
@click.option('--dry-run', is_flag=True, default=True, help='Show what would be done without moving files')
@click.option('--execute', is_flag=True, help='Actually move files (disables dry-run)')
def organize(pattern: Optional[str], dry_run: bool, execute: bool):
    """Organize library files based on metadata."""
    config = Config()
    db_manager = DatabaseManager(config.database_path)
    organizer = FileOrganizer(config, db_manager)

    # If execute is specified, disable dry-run
    if execute:
        dry_run = False

    console.print("[cyan]Organizing library...[/cyan]")
    if dry_run:
        console.print("[yellow]DRY RUN MODE - No files will be moved[/yellow]\n")

    count = organizer.organize_library(pattern=pattern, dry_run=dry_run)

    if dry_run:
        console.print(f"\n[yellow]Would organize {count} files[/yellow]")
        console.print("[cyan]Run with --execute to apply changes[/cyan]")
    else:
        console.print(f"\n[green]✓[/green] Organized {count} files")


@main.group()
def clean():
    """Clean and maintain your library."""
    pass


@clean.command()
@click.option('--fingerprint/--metadata', default=True, help='Use audio fingerprinting or metadata matching')
@click.option('--remove', is_flag=True, help='Remove duplicates (keeps highest quality)')
@click.option('--auto', is_flag=True, help='Auto-delete without confirmation')
def duplicates(fingerprint: bool, remove: bool, auto: bool):
    """Find and remove duplicate tracks."""
    config = Config()
    db_manager = DatabaseManager(config.database_path)
    detector = DuplicateDetector(config, db_manager)

    console.print("[cyan]Finding duplicates...[/cyan]")
    duplicate_groups = detector.find_duplicates(use_fingerprint=fingerprint)

    detector.display_duplicates(duplicate_groups)

    if remove and duplicate_groups:
        console.print()
        if auto or click.confirm("Do you want to remove duplicates?"):
            count = detector.remove_duplicates(duplicate_groups, keep_best=True, auto_delete=auto)
            console.print(f"\n[green]✓[/green] Removed {count} duplicate files")


@main.group()
def discover():
    """Discover new music and analyze your library."""
    pass


@discover.command()
@click.option('--limit', default=20, help='Number of recommendations')
@click.option('--genre', help='Filter by genre')
@click.option('--min-rating', type=int, help='Minimum track rating')
def recommendations(limit: int, genre: Optional[str], min_rating: Optional[int]):
    """Get music recommendations based on your library."""
    config = Config()
    db_manager = DatabaseManager(config.database_path)
    discovery = MusicDiscovery(config, db_manager)

    console.print("[cyan]Getting recommendations...[/cyan]\n")
    recs = discovery.get_recommendations(limit=limit, genre=genre, min_rating=min_rating)

    if recs:
        table = Table(title="Recommended Tracks")
        table.add_column("Artist", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Album", style="yellow")
        table.add_column("Popularity", style="magenta")

        for rec in recs:
            table.add_row(
                rec['artist'],
                rec['title'],
                rec['album'],
                str(rec.get('popularity', 'N/A'))
            )

        console.print(table)
    else:
        console.print("[yellow]No recommendations available[/yellow]")


@discover.command()
@click.argument('artist_name')
@click.option('--limit', default=10, help='Number of similar artists')
def similar(artist_name: str, limit: int):
    """Find artists similar to a given artist."""
    config = Config()
    db_manager = DatabaseManager(config.database_path)
    discovery = MusicDiscovery(config, db_manager)

    console.print(f"[cyan]Finding artists similar to {artist_name}...[/cyan]\n")
    similar_artists = discovery.find_similar_artists(artist_name, limit=limit)

    if similar_artists:
        table = Table(title=f"Artists Similar to {artist_name}")
        table.add_column("Artist", style="cyan")
        table.add_column("Genres", style="yellow")
        table.add_column("Popularity", style="magenta")

        for artist in similar_artists:
            table.add_row(
                artist['name'],
                ', '.join(artist.get('genres', [])[:3]),
                str(artist.get('popularity', 'N/A'))
            )

        console.print(table)
    else:
        console.print("[yellow]No similar artists found[/yellow]")


@discover.command()
def stats():
    """Display library statistics."""
    config = Config()
    db_manager = DatabaseManager(config.database_path)
    discovery = MusicDiscovery(config, db_manager)

    console.print("[cyan]Analyzing library...[/cyan]\n")
    stats = discovery.get_library_stats()

    # Overall stats
    console.print(f"[green]Total Tracks:[/green] {stats['total_tracks']}")
    console.print(f"[green]Total Artists:[/green] {stats['total_artists']}")
    console.print(f"[green]Total Albums:[/green] {stats['total_albums']}")
    console.print(f"[green]Total Duration:[/green] {stats['total_duration_hours']} hours")

    # Top artists
    if stats['top_artists']:
        console.print("\n[cyan]Top Artists:[/cyan]")
        table = Table()
        table.add_column("Artist", style="cyan")
        table.add_column("Tracks", style="magenta")

        for artist in stats['top_artists']:
            table.add_row(artist['artist'], str(artist['track_count']))

        console.print(table)


@main.group()
def playlist():
    """Manage playlists."""
    pass


@playlist.command('create')
@click.argument('name')
@click.option('--description', help='Playlist description')
def create_playlist(name: str, description: Optional[str]):
    """Create a new playlist."""
    config = Config()
    db_manager = DatabaseManager(config.database_path)
    manager = PlaylistManager(config, db_manager)

    manager.create_playlist(name, description=description)


@playlist.command('smart')
@click.argument('name')
@click.option('--genre', help='Filter by genre')
@click.option('--min-rating', type=int, help='Minimum rating (1-5)')
@click.option('--max-rating', type=int, help='Maximum rating (1-5)')
@click.option('--min-duration', type=int, help='Minimum duration in seconds')
@click.option('--max-duration', type=int, help='Maximum duration in seconds')
@click.option('--year-start', type=int, help='Start year')
@click.option('--year-end', type=int, help='End year')
def create_smart_playlist(
    name: str,
    genre: Optional[str],
    min_rating: Optional[int],
    max_rating: Optional[int],
    min_duration: Optional[int],
    max_duration: Optional[int],
    year_start: Optional[int],
    year_end: Optional[int]
):
    """Create a smart playlist based on criteria."""
    config = Config()
    db_manager = DatabaseManager(config.database_path)
    manager = PlaylistManager(config, db_manager)

    criteria = {}
    if genre:
        criteria['genre'] = genre
    if min_rating:
        criteria['min_rating'] = min_rating
    if max_rating:
        criteria['max_rating'] = max_rating
    if min_duration:
        criteria['min_duration'] = min_duration
    if max_duration:
        criteria['max_duration'] = max_duration
    if year_start and year_end:
        criteria['year_range'] = [year_start, year_end]

    if not criteria:
        console.print("[red]Please specify at least one criterion[/red]")
        return

    manager.generate_smart_playlist(name, criteria)


@playlist.command('list')
def list_playlists():
    """List all playlists."""
    config = Config()
    db_manager = DatabaseManager(config.database_path)
    manager = PlaylistManager(config, db_manager)

    manager.list_playlists()


@playlist.command('export')
@click.argument('playlist_id', type=int)
@click.option('--format', type=click.Choice(['m3u', 'pls']), default='m3u', help='Export format')
def export_playlist(playlist_id: int, format: str):
    """Export a playlist to file."""
    config = Config()
    db_manager = DatabaseManager(config.database_path)
    manager = PlaylistManager(config, db_manager)

    manager.export_playlist(playlist_id, format=format)


@main.command()
def config_show():
    """Show current configuration."""
    config = Config()

    console.print("[cyan]Current Configuration:[/cyan]\n")
    console.print(f"[green]Config file:[/green] {config.config_path}")
    console.print(f"[green]Library path:[/green] {config.library_path}")
    console.print(f"[green]Database path:[/green] {config.database_path}")
    console.print(f"[green]Supported formats:[/green] {', '.join(config.supported_formats)}")


if __name__ == '__main__':
    main()

"""Duplicate detection and removal."""

from pathlib import Path
from typing import List, Tuple, Optional
from collections import defaultdict

import acoustid
from rich.console import Console
from rich.table import Table
from sqlalchemy.orm import Session

from ..core.database import Track, DatabaseManager
from ..core.config import Config

console = Console()


class DuplicateDetector:
    """Detects and manages duplicate tracks."""

    def __init__(self, config: Config, db_manager: DatabaseManager):
        """Initialize duplicate detector.

        Args:
            config: Configuration instance
            db_manager: Database manager instance
        """
        self.config = config
        self.db_manager = db_manager
        self.acoustid_api_key = config.get('integrations.acoustid.api_key')

    def find_duplicates(self, use_fingerprint: bool = True) -> List[List[Track]]:
        """Find duplicate tracks in library.

        Args:
            use_fingerprint: If True, use audio fingerprinting for detection

        Returns:
            List of duplicate groups (each group is a list of duplicate tracks)
        """
        session = self.db_manager.get_session()
        duplicates = []

        try:
            if use_fingerprint and self.acoustid_api_key:
                duplicates = self._find_by_fingerprint(session)
            else:
                duplicates = self._find_by_metadata(session)

        finally:
            session.close()

        return duplicates

    def _find_by_fingerprint(self, session: Session) -> List[List[Track]]:
        """Find duplicates using audio fingerprinting.

        Args:
            session: Database session

        Returns:
            List of duplicate groups
        """
        tracks = session.query(Track).all()
        fingerprint_groups = defaultdict(list)
        threshold = self.config.get('cleaning.duplicate_threshold', 0.95)

        console.print("[cyan]Generating audio fingerprints...[/cyan]")

        for track in tracks:
            try:
                # Generate fingerprint if not already stored
                if not track.acoustid:
                    fingerprint = self._generate_fingerprint(Path(track.file_path))
                    if fingerprint:
                        track.acoustid = fingerprint
                        fingerprint_groups[fingerprint].append(track)
                else:
                    fingerprint_groups[track.acoustid].append(track)

            except Exception as e:
                console.print(f"[yellow]Warning: Could not fingerprint {track.file_path}: {e}[/yellow]")

        session.commit()

        # Find groups with more than one track
        duplicates = [tracks for tracks in fingerprint_groups.values() if len(tracks) > 1]

        return duplicates

    def _find_by_metadata(self, session: Session) -> List[List[Track]]:
        """Find duplicates by comparing metadata.

        Args:
            session: Database session

        Returns:
            List of duplicate groups
        """
        tracks = session.query(Track).all()
        metadata_groups = defaultdict(list)

        for track in tracks:
            # Create a key from metadata
            key = (
                (track.artist or '').lower().strip(),
                (track.album or '').lower().strip(),
                (track.title or '').lower().strip(),
                track.duration  # Include duration for better matching
            )
            metadata_groups[key].append(track)

        # Find groups with more than one track
        duplicates = [tracks for tracks in metadata_groups.values() if len(tracks) > 1]

        return duplicates

    def _generate_fingerprint(self, file_path: Path) -> Optional[str]:
        """Generate audio fingerprint for file.

        Args:
            file_path: Path to audio file

        Returns:
            Fingerprint string or None if generation failed
        """
        try:
            duration, fingerprint = acoustid.fingerprint_file(str(file_path))
            return fingerprint
        except Exception:
            return None

    def display_duplicates(self, duplicate_groups: List[List[Track]]) -> None:
        """Display duplicate groups in a formatted table.

        Args:
            duplicate_groups: List of duplicate groups
        """
        if not duplicate_groups:
            console.print("[green]No duplicates found![/green]")
            return

        console.print(f"\n[yellow]Found {len(duplicate_groups)} groups of duplicates:[/yellow]\n")

        for i, group in enumerate(duplicate_groups, 1):
            table = Table(title=f"Duplicate Group {i}")
            table.add_column("File", style="cyan")
            table.add_column("Size", style="magenta")
            table.add_column("Bitrate", style="green")
            table.add_column("Format", style="yellow")

            for track in group:
                file_path = Path(track.file_path)
                size_mb = track.file_size / (1024 * 1024) if track.file_size else 0
                table.add_row(
                    str(file_path.name),
                    f"{size_mb:.2f} MB",
                    f"{track.bitrate // 1000 if track.bitrate else 0} kbps",
                    track.format or 'unknown'
                )

            console.print(table)
            console.print()

    def remove_duplicates(
        self,
        duplicate_groups: List[List[Track]],
        keep_best: bool = True,
        auto_delete: bool = False
    ) -> int:
        """Remove duplicate tracks.

        Args:
            duplicate_groups: List of duplicate groups
            keep_best: If True, keep the highest quality version
            auto_delete: If True, delete without confirmation

        Returns:
            Number of files deleted
        """
        session = self.db_manager.get_session()
        deleted_count = 0

        try:
            for group in duplicate_groups:
                if keep_best:
                    # Sort by quality (bitrate, then file size)
                    group.sort(key=lambda t: (t.bitrate or 0, t.file_size or 0), reverse=True)
                    to_keep = group[0]
                    to_delete = group[1:]
                else:
                    to_keep = group[0]
                    to_delete = group[1:]

                console.print(f"\n[cyan]Keeping:[/cyan] {to_keep.file_path}")

                for track in to_delete:
                    if auto_delete or console.input(f"Delete {track.file_path}? (y/N): ").lower() == 'y':
                        try:
                            Path(track.file_path).unlink()
                            session.delete(track)
                            deleted_count += 1
                            console.print(f"[red]Deleted:[/red] {track.file_path}")
                        except Exception as e:
                            console.print(f"[red]Error deleting {track.file_path}: {e}[/red]")

            session.commit()

        finally:
            session.close()

        return deleted_count

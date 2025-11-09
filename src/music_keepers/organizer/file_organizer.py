"""File organization functionality."""

import shutil
from pathlib import Path
from typing import Optional, Dict, Any

from rich.console import Console
from sqlalchemy.orm import Session

from ..core.database import Track, DatabaseManager
from ..core.config import Config

console = Console()


class FileOrganizer:
    """Organizes music files based on metadata."""

    def __init__(self, config: Config, db_manager: DatabaseManager):
        """Initialize file organizer.

        Args:
            config: Configuration instance
            db_manager: Database manager instance
        """
        self.config = config
        self.db_manager = db_manager

    def organize_library(self, pattern: Optional[str] = None, dry_run: bool = True) -> int:
        """Organize entire library based on pattern.

        Args:
            pattern: File organization pattern (e.g., "{artist}/{album}/{track} - {title}")
            dry_run: If True, only show what would be done without moving files

        Returns:
            Number of files organized
        """
        pattern = pattern or self.config.get('organization.default_pattern')
        session = self.db_manager.get_session()
        count = 0

        try:
            tracks = session.query(Track).all()
            for track in tracks:
                if self._organize_file(track, pattern, dry_run, session):
                    count += 1

            if not dry_run:
                session.commit()

        finally:
            session.close()

        return count

    def _organize_file(
        self,
        track: Track,
        pattern: str,
        dry_run: bool,
        session: Session
    ) -> bool:
        """Organize a single file.

        Args:
            track: Track to organize
            pattern: File organization pattern
            dry_run: If True, only show what would be done
            session: Database session

        Returns:
            True if file was (or would be) moved
        """
        try:
            current_path = Path(track.file_path)
            if not current_path.exists():
                console.print(f"[red]File not found: {current_path}[/red]")
                return False

            # Generate new path
            new_path = self._generate_path(track, pattern)
            if new_path == current_path:
                return False  # Already in correct location

            if dry_run:
                console.print(f"[yellow]Would move:[/yellow] {current_path}")
                console.print(f"[yellow]        to:[/yellow] {new_path}")
                return True

            # Create destination directory
            new_path.parent.mkdir(parents=True, exist_ok=True)

            # Move file
            shutil.move(str(current_path), str(new_path))

            # Update database
            track.file_path = str(new_path)

            console.print(f"[green]Moved:[/green] {current_path.name}")
            console.print(f"[green]   to:[/green] {new_path}")

            return True

        except Exception as e:
            console.print(f"[red]Error organizing {track.file_path}: {e}[/red]")
            return False

    def _generate_path(self, track: Track, pattern: str) -> Path:
        """Generate new file path based on pattern and metadata.

        Args:
            track: Track with metadata
            pattern: File organization pattern

        Returns:
            New file path
        """
        library_path = self.config.library_path

        # Prepare metadata for formatting
        metadata = {
            'artist': self._sanitize(track.artist or 'Unknown Artist'),
            'album': self._sanitize(track.album or 'Unknown Album'),
            'title': self._sanitize(track.title or Path(track.file_path).stem),
            'track': track.track_number or 0,
            'year': track.year or '',
            'genre': self._sanitize(track.genre or 'Unknown'),
            'album_artist': self._sanitize(track.album_artist or track.artist or 'Unknown Artist')
        }

        # Handle compilations
        if self.config.get('organization.handle_compilations'):
            is_compilation = track.album_artist and track.album_artist.lower() in [
                'various artists', 'various', 'compilation'
            ]
            if is_compilation:
                pattern = self.config.get('organization.compilation_pattern', pattern)

        # Format pattern
        try:
            relative_path = pattern.format(**metadata)
        except KeyError as e:
            console.print(f"[yellow]Warning: Unknown pattern key {e}, using default[/yellow]")
            relative_path = f"{metadata['artist']}/{metadata['album']}/{metadata['title']}"

        # Add file extension
        extension = Path(track.file_path).suffix
        new_path = library_path / f"{relative_path}{extension}"

        return new_path

    def _sanitize(self, text: Optional[str]) -> str:
        """Sanitize text for use in file paths.

        Args:
            text: Text to sanitize

        Returns:
            Sanitized text safe for file paths
        """
        if not text:
            return ''

        # Replace invalid filename characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            text = text.replace(char, '_')

        # Remove leading/trailing dots and spaces
        text = text.strip('. ')

        return text

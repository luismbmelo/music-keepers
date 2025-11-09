"""Library scanning functionality."""

from pathlib import Path
from typing import List, Optional, Generator
from datetime import datetime

from mutagen import File as MutagenFile
from rich.progress import Progress, TaskID
from sqlalchemy.orm import Session

from .database import Track, DatabaseManager
from .config import Config


class LibraryScanner:
    """Scanner for music library files."""

    def __init__(self, config: Config, db_manager: DatabaseManager):
        """Initialize library scanner.

        Args:
            config: Configuration instance
            db_manager: Database manager instance
        """
        self.config = config
        self.db_manager = db_manager
        self.supported_formats = config.supported_formats

    def scan_library(self, path: Optional[Path] = None) -> int:
        """Scan library and update database.

        Args:
            path: Path to scan. Uses config library path if not provided.

        Returns:
            Number of tracks scanned
        """
        scan_path = path or self.config.library_path
        if not scan_path.exists():
            raise ValueError(f"Library path does not exist: {scan_path}")

        count = 0
        session = self.db_manager.get_session()

        try:
            with Progress() as progress:
                task = progress.add_task("[cyan]Scanning library...", total=None)

                for audio_file in self._find_audio_files(scan_path):
                    self._process_file(audio_file, session)
                    count += 1
                    progress.update(task, advance=1)

                session.commit()
        finally:
            session.close()

        return count

    def _find_audio_files(self, path: Path) -> Generator[Path, None, None]:
        """Find all audio files in directory recursively.

        Args:
            path: Directory to search

        Yields:
            Path to audio files
        """
        for file_path in path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                yield file_path

    def _process_file(self, file_path: Path, session: Session) -> Optional[Track]:
        """Process an audio file and add/update in database.

        Args:
            file_path: Path to audio file
            session: Database session

        Returns:
            Track instance or None if processing failed
        """
        try:
            # Check if track already exists
            existing_track = session.query(Track).filter_by(
                file_path=str(file_path)
            ).first()

            # Get file stats
            stats = file_path.stat()
            file_modified = datetime.fromtimestamp(stats.st_mtime)

            # Skip if file hasn't been modified
            if existing_track and existing_track.file_modified == file_modified:
                return existing_track

            # Extract metadata
            metadata = self._extract_metadata(file_path)

            if existing_track:
                # Update existing track
                for key, value in metadata.items():
                    setattr(existing_track, key, value)
                existing_track.file_modified = file_modified
                existing_track.file_size = stats.st_size
                return existing_track
            else:
                # Create new track
                track = Track(
                    file_path=str(file_path),
                    file_size=stats.st_size,
                    file_modified=file_modified,
                    **metadata
                )
                session.add(track)
                return track

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return None

    def _extract_metadata(self, file_path: Path) -> dict:
        """Extract metadata from audio file.

        Args:
            file_path: Path to audio file

        Returns:
            Dictionary of metadata
        """
        metadata = {}

        try:
            audio = MutagenFile(file_path)
            if audio is None:
                return metadata

            # Extract common tags
            metadata['title'] = self._get_tag(audio, ['title', 'TIT2'])
            metadata['artist'] = self._get_tag(audio, ['artist', 'TPE1'])
            metadata['album'] = self._get_tag(audio, ['album', 'TALB'])
            metadata['album_artist'] = self._get_tag(audio, ['albumartist', 'TPE2'])
            metadata['genre'] = self._get_tag(audio, ['genre', 'TCON'])

            # Extract numeric tags
            year_str = self._get_tag(audio, ['date', 'year', 'TDRC'])
            if year_str:
                try:
                    metadata['year'] = int(str(year_str)[:4])
                except (ValueError, TypeError):
                    pass

            track_str = self._get_tag(audio, ['tracknumber', 'TRCK'])
            if track_str:
                try:
                    # Handle "3/12" format
                    metadata['track_number'] = int(str(track_str).split('/')[0])
                except (ValueError, TypeError):
                    pass

            disc_str = self._get_tag(audio, ['discnumber', 'TPOS'])
            if disc_str:
                try:
                    metadata['disc_number'] = int(str(disc_str).split('/')[0])
                except (ValueError, TypeError):
                    pass

            # Audio properties
            if hasattr(audio.info, 'length'):
                metadata['duration'] = audio.info.length
            if hasattr(audio.info, 'bitrate'):
                metadata['bitrate'] = audio.info.bitrate
            if hasattr(audio.info, 'sample_rate'):
                metadata['sample_rate'] = audio.info.sample_rate
            if hasattr(audio.info, 'channels'):
                metadata['channels'] = audio.info.channels

            metadata['format'] = file_path.suffix.lower()

        except Exception as e:
            print(f"Error extracting metadata from {file_path}: {e}")

        return metadata

    def _get_tag(self, audio, tag_names: List[str]) -> Optional[str]:
        """Get tag value from audio file trying multiple tag names.

        Args:
            audio: Mutagen audio file
            tag_names: List of possible tag names

        Returns:
            Tag value as string or None
        """
        for tag_name in tag_names:
            value = audio.get(tag_name)
            if value:
                # Handle list values
                if isinstance(value, list):
                    value = value[0] if value else None
                # Convert to string
                return str(value) if value else None
        return None

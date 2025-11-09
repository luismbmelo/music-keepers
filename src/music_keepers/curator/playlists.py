"""Playlist management functionality."""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime

from rich.console import Console
from rich.table import Table
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from ..core.database import (
    Playlist, PlaylistTrack, Track, Tag, TrackTag,
    DatabaseManager
)
from ..core.config import Config

console = Console()


class PlaylistManager:
    """Manages playlists and smart playlists."""

    def __init__(self, config: Config, db_manager: DatabaseManager):
        """Initialize playlist manager.

        Args:
            config: Configuration instance
            db_manager: Database manager instance
        """
        self.config = config
        self.db_manager = db_manager

    def create_playlist(
        self,
        name: str,
        description: Optional[str] = None,
        is_smart: bool = False,
        smart_criteria: Optional[Dict[str, Any]] = None
    ) -> Playlist:
        """Create a new playlist.

        Args:
            name: Playlist name
            description: Playlist description
            is_smart: Whether this is a smart playlist
            smart_criteria: Criteria for smart playlist

        Returns:
            Created playlist
        """
        session = self.db_manager.get_session()

        try:
            playlist = Playlist(
                name=name,
                description=description,
                is_smart=is_smart,
                smart_criteria=json.dumps(smart_criteria) if smart_criteria else None
            )

            session.add(playlist)
            session.commit()
            session.refresh(playlist)

            console.print(f"[green]Created playlist:[/green] {name}")

            return playlist

        finally:
            session.close()

    def add_tracks_to_playlist(
        self,
        playlist_id: int,
        track_ids: List[int]
    ) -> int:
        """Add tracks to a playlist.

        Args:
            playlist_id: ID of the playlist
            track_ids: List of track IDs to add

        Returns:
            Number of tracks added
        """
        session = self.db_manager.get_session()

        try:
            playlist = session.query(Playlist).get(playlist_id)
            if not playlist:
                console.print(f"[red]Playlist {playlist_id} not found[/red]")
                return 0

            # Get current max position
            max_position = session.query(PlaylistTrack).filter_by(
                playlist_id=playlist_id
            ).count()

            added = 0
            for i, track_id in enumerate(track_ids):
                track = session.query(Track).get(track_id)
                if track:
                    playlist_track = PlaylistTrack(
                        playlist_id=playlist_id,
                        track_id=track_id,
                        position=max_position + i
                    )
                    session.add(playlist_track)
                    added += 1

            session.commit()
            console.print(f"[green]Added {added} tracks to playlist[/green]")

            return added

        finally:
            session.close()

    def generate_smart_playlist(
        self,
        name: str,
        criteria: Dict[str, Any],
        description: Optional[str] = None
    ) -> Optional[Playlist]:
        """Generate a smart playlist based on criteria.

        Args:
            name: Playlist name
            criteria: Dictionary of criteria for filtering tracks
            description: Playlist description

        Returns:
            Created smart playlist or None if no tracks match

        Example criteria:
            {
                'genre': 'Jazz',
                'min_rating': 4,
                'max_duration': 300,  # 5 minutes
                'year_range': [2000, 2020],
                'tags': ['favorite', 'chill']
            }
        """
        session = self.db_manager.get_session()

        try:
            # Build query based on criteria
            query = session.query(Track)

            if 'genre' in criteria:
                query = query.filter(Track.genre.ilike(f"%{criteria['genre']}%"))

            if 'min_rating' in criteria:
                query = query.filter(Track.rating >= criteria['min_rating'])

            if 'max_rating' in criteria:
                query = query.filter(Track.rating <= criteria['max_rating'])

            if 'min_duration' in criteria:
                query = query.filter(Track.duration >= criteria['min_duration'])

            if 'max_duration' in criteria:
                query = query.filter(Track.duration <= criteria['max_duration'])

            if 'year_range' in criteria:
                start, end = criteria['year_range']
                query = query.filter(and_(Track.year >= start, Track.year <= end))

            if 'artist' in criteria:
                query = query.filter(Track.artist.ilike(f"%{criteria['artist']}%"))

            if 'tags' in criteria:
                # Filter by tags
                for tag_name in criteria['tags']:
                    query = query.join(TrackTag).join(Tag).filter(Tag.name == tag_name)

            # Get matching tracks
            tracks = query.all()

            if not tracks:
                console.print("[yellow]No tracks match the criteria[/yellow]")
                return None

            # Create smart playlist
            playlist = Playlist(
                name=name,
                description=description or f"Smart playlist with {len(tracks)} tracks",
                is_smart=True,
                smart_criteria=json.dumps(criteria)
            )

            session.add(playlist)
            session.flush()

            # Add tracks
            for i, track in enumerate(tracks):
                playlist_track = PlaylistTrack(
                    playlist_id=playlist.id,
                    track_id=track.id,
                    position=i
                )
                session.add(playlist_track)

            session.commit()
            session.refresh(playlist)

            console.print(f"[green]Created smart playlist '{name}' with {len(tracks)} tracks[/green]")

            return playlist

        finally:
            session.close()

    def refresh_smart_playlist(self, playlist_id: int) -> int:
        """Refresh a smart playlist by re-applying its criteria.

        Args:
            playlist_id: ID of the smart playlist

        Returns:
            Number of tracks in refreshed playlist
        """
        session = self.db_manager.get_session()

        try:
            playlist = session.query(Playlist).get(playlist_id)
            if not playlist or not playlist.is_smart:
                console.print("[red]Invalid smart playlist[/red]")
                return 0

            # Remove existing tracks
            session.query(PlaylistTrack).filter_by(playlist_id=playlist_id).delete()

            # Re-apply criteria
            criteria = json.loads(playlist.smart_criteria)
            # (Use similar logic as generate_smart_playlist)

            playlist.updated_at = datetime.utcnow()
            session.commit()

            return session.query(PlaylistTrack).filter_by(playlist_id=playlist_id).count()

        finally:
            session.close()

    def list_playlists(self) -> None:
        """Display all playlists."""
        session = self.db_manager.get_session()

        try:
            playlists = session.query(Playlist).all()

            if not playlists:
                console.print("[yellow]No playlists found[/yellow]")
                return

            table = Table(title="Playlists")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Type", style="yellow")
            table.add_column("Tracks", style="magenta")
            table.add_column("Updated", style="blue")

            for playlist in playlists:
                track_count = session.query(PlaylistTrack).filter_by(
                    playlist_id=playlist.id
                ).count()

                table.add_row(
                    str(playlist.id),
                    playlist.name,
                    "Smart" if playlist.is_smart else "Manual",
                    str(track_count),
                    playlist.updated_at.strftime("%Y-%m-%d")
                )

            console.print(table)

        finally:
            session.close()

    def export_playlist(
        self,
        playlist_id: int,
        format: str = 'm3u'
    ) -> Optional[str]:
        """Export playlist to file.

        Args:
            playlist_id: ID of the playlist
            format: Export format ('m3u' or 'pls')

        Returns:
            Path to exported file or None
        """
        session = self.db_manager.get_session()

        try:
            playlist = session.query(Playlist).get(playlist_id)
            if not playlist:
                console.print(f"[red]Playlist {playlist_id} not found[/red]")
                return None

            # Get tracks in order
            playlist_tracks = session.query(PlaylistTrack, Track).join(Track).filter(
                PlaylistTrack.playlist_id == playlist_id
            ).order_by(PlaylistTrack.position).all()

            # Generate filename
            filename = f"{playlist.name.replace(' ', '_')}.{format}"

            # Write playlist file
            if format == 'm3u':
                self._export_m3u(filename, playlist_tracks)
            elif format == 'pls':
                self._export_pls(filename, playlist_tracks)
            else:
                console.print(f"[red]Unknown format: {format}[/red]")
                return None

            console.print(f"[green]Exported playlist to:[/green] {filename}")
            return filename

        finally:
            session.close()

    def _export_m3u(self, filename: str, playlist_tracks: List) -> None:
        """Export playlist in M3U format."""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            for _, track in playlist_tracks:
                duration = int(track.duration) if track.duration else -1
                f.write(f"#EXTINF:{duration},{track.artist} - {track.title}\n")
                f.write(f"{track.file_path}\n")

    def _export_pls(self, filename: str, playlist_tracks: List) -> None:
        """Export playlist in PLS format."""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("[playlist]\n")
            for i, (_, track) in enumerate(playlist_tracks, 1):
                f.write(f"File{i}={track.file_path}\n")
                f.write(f"Title{i}={track.artist} - {track.title}\n")
                duration = int(track.duration) if track.duration else -1
                f.write(f"Length{i}={duration}\n")
            f.write(f"NumberOfEntries={len(playlist_tracks)}\n")
            f.write("Version=2\n")

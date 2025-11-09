"""Music discovery and recommendation functionality."""

from typing import List, Dict, Any, Optional
from collections import Counter

import discogs_client
from rich.console import Console
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..core.database import Track, DatabaseManager
from ..core.config import Config

console = Console()


class MusicDiscovery:
    """Music discovery and recommendation engine using Discogs, Bandcamp, and Beatport."""

    def __init__(self, config: Config, db_manager: DatabaseManager):
        """Initialize music discovery.

        Args:
            config: Configuration instance
            db_manager: Database manager instance
        """
        self.config = config
        self.db_manager = db_manager
        self.discogs_client = None

        # Initialize Discogs client if token is available
        discogs_token = config.get('integrations.discogs.token')
        user_agent = config.get('integrations.discogs.user_agent')

        if discogs_token and user_agent:
            try:
                self.discogs_client = discogs_client.Client(
                    user_agent=user_agent,
                    user_token=discogs_token
                )
            except Exception as e:
                console.print(f"[yellow]Warning: Could not initialize Discogs client: {e}[/yellow]")

    def search_discogs(
        self,
        artist: Optional[str] = None,
        title: Optional[str] = None,
        release_title: Optional[str] = None,
        genre: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search Discogs for releases.

        Args:
            artist: Artist name
            title: Track title
            release_title: Release/album title
            genre: Genre filter
            limit: Maximum number of results

        Returns:
            List of release information
        """
        if not self.discogs_client:
            console.print("[red]Discogs integration not configured[/red]")
            console.print("[yellow]Get a token at: https://www.discogs.com/settings/developers[/yellow]")
            return []

        try:
            search_params = {}
            if artist:
                search_params['artist'] = artist
            if title:
                search_params['track'] = title
            if release_title:
                search_params['release_title'] = release_title
            if genre:
                search_params['genre'] = genre

            results = self.discogs_client.search(**search_params)

            releases = []
            for i, result in enumerate(results[:limit]):
                try:
                    release_info = {
                        'title': result.title,
                        'type': result.type if hasattr(result, 'type') else 'unknown',
                        'year': result.year if hasattr(result, 'year') else None,
                        'country': result.country if hasattr(result, 'country') else None,
                        'format': ', '.join(result.formats) if hasattr(result, 'formats') else None,
                        'label': ', '.join([label.name for label in result.labels]) if hasattr(result, 'labels') else None,
                        'url': result.url if hasattr(result, 'url') else None,
                        'genres': result.genres if hasattr(result, 'genres') else [],
                        'styles': result.styles if hasattr(result, 'styles') else []
                    }
                    releases.append(release_info)
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not parse result: {e}[/yellow]")
                    continue

            return releases

        except Exception as e:
            console.print(f"[red]Error searching Discogs: {e}[/red]")
            return []

    def get_artist_info(self, artist_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed artist information from Discogs.

        Args:
            artist_name: Name of the artist

        Returns:
            Artist information dictionary or None
        """
        if not self.discogs_client:
            console.print("[red]Discogs integration not configured[/red]")
            return None

        try:
            results = self.discogs_client.search(artist_name, type='artist')

            if not results:
                console.print(f"[yellow]Artist '{artist_name}' not found[/yellow]")
                return None

            artist = results[0]

            artist_info = {
                'name': artist.name,
                'real_name': artist.real_name if hasattr(artist, 'real_name') else None,
                'profile': artist.profile if hasattr(artist, 'profile') else None,
                'aliases': [a.name for a in artist.aliases] if hasattr(artist, 'aliases') else [],
                'members': [m.name for m in artist.members] if hasattr(artist, 'members') else [],
                'urls': artist.urls if hasattr(artist, 'urls') else [],
                'url': artist.url if hasattr(artist, 'url') else None
            }

            return artist_info

        except Exception as e:
            console.print(f"[red]Error getting artist info: {e}[/red]")
            return None

    def get_recommendations_by_genre(
        self,
        genre: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get music recommendations by genre from Discogs.

        Args:
            genre: Genre to search for
            limit: Maximum number of recommendations

        Returns:
            List of recommended releases
        """
        return self.search_discogs(genre=genre, limit=limit)

    def find_similar_artists(
        self,
        artist_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Find artists similar to the given artist using Discogs relationships.

        Args:
            artist_name: Name of the artist
            limit: Maximum number of similar artists

        Returns:
            List of similar artists
        """
        if not self.discogs_client:
            console.print("[red]Discogs integration not configured[/red]")
            return []

        try:
            # Search for the artist
            results = self.discogs_client.search(artist_name, type='artist')

            if not results:
                console.print(f"[yellow]Artist '{artist_name}' not found[/yellow]")
                return []

            artist = results[0]
            similar_artists = []

            # Get members (for groups)
            if hasattr(artist, 'members') and artist.members:
                for member in artist.members[:limit]:
                    similar_artists.append({
                        'name': member.name,
                        'relationship': 'member',
                        'url': member.url if hasattr(member, 'url') else None
                    })

            # Get aliases
            if hasattr(artist, 'aliases') and artist.aliases:
                for alias in artist.aliases[:limit - len(similar_artists)]:
                    similar_artists.append({
                        'name': alias.name,
                        'relationship': 'alias',
                        'url': alias.url if hasattr(alias, 'url') else None
                    })

            # Get groups (for members)
            if hasattr(artist, 'groups') and artist.groups:
                for group in artist.groups[:limit - len(similar_artists)]:
                    similar_artists.append({
                        'name': group.name,
                        'relationship': 'group',
                        'url': group.url if hasattr(group, 'url') else None
                    })

            return similar_artists[:limit]

        except Exception as e:
            console.print(f"[red]Error finding similar artists: {e}[/red]")
            return []

    def get_release_info(
        self,
        artist: str,
        album: str
    ) -> Optional[Dict[str, Any]]:
        """Get detailed release information from Discogs.

        Args:
            artist: Artist name
            album: Album/release title

        Returns:
            Release information dictionary or None
        """
        if not self.discogs_client:
            console.print("[red]Discogs integration not configured[/red]")
            return None

        try:
            results = self.discogs_client.search(
                release_title=album,
                artist=artist,
                type='release'
            )

            if not results:
                return None

            release = results[0]

            release_info = {
                'title': release.title,
                'year': release.year if hasattr(release, 'year') else None,
                'country': release.country if hasattr(release, 'country') else None,
                'genres': release.genres if hasattr(release, 'genres') else [],
                'styles': release.styles if hasattr(release, 'styles') else [],
                'formats': release.formats if hasattr(release, 'formats') else [],
                'labels': [label.name for label in release.labels] if hasattr(release, 'labels') else [],
                'url': release.url if hasattr(release, 'url') else None,
                'tracklist': []
            }

            # Get tracklist
            if hasattr(release, 'tracklist'):
                for track in release.tracklist:
                    release_info['tracklist'].append({
                        'position': track.position if hasattr(track, 'position') else None,
                        'title': track.title if hasattr(track, 'title') else None,
                        'duration': track.duration if hasattr(track, 'duration') else None
                    })

            return release_info

        except Exception as e:
            console.print(f"[yellow]Could not get release info: {e}[/yellow]")
            return None

    def analyze_library_genres(self) -> Dict[str, int]:
        """Analyze genre distribution in library.

        Returns:
            Dictionary mapping genres to track counts
        """
        session = self.db_manager.get_session()

        try:
            tracks = session.query(Track).filter(Track.genre.isnot(None)).all()
            genres = [track.genre for track in tracks if track.genre]

            # Count genre occurrences
            genre_counts = Counter(genres)

            return dict(genre_counts.most_common())

        finally:
            session.close()

    def get_library_stats(self) -> Dict[str, Any]:
        """Get statistics about the music library.

        Returns:
            Dictionary with library statistics
        """
        session = self.db_manager.get_session()

        try:
            total_tracks = session.query(Track).count()
            total_artists = session.query(Track.artist).distinct().count()
            total_albums = session.query(Track.album).distinct().count()

            total_duration = session.query(Track.duration).filter(
                Track.duration.isnot(None)
            ).all()
            total_duration_seconds = sum(d[0] for d in total_duration if d[0])
            total_duration_hours = total_duration_seconds / 3600

            top_artists = session.query(
                Track.artist,
                func.count(Track.id).label('count')
            ).filter(Track.artist.isnot(None)).group_by(Track.artist).order_by(
                func.count(Track.id).desc()
            ).limit(10).all()

            top_genres = session.query(
                Track.genre,
                func.count(Track.id).label('count')
            ).filter(Track.genre.isnot(None)).group_by(Track.genre).order_by(
                func.count(Track.id).desc()
            ).limit(10).all()

            return {
                'total_tracks': total_tracks,
                'total_artists': total_artists,
                'total_albums': total_albums,
                'total_duration_hours': round(total_duration_hours, 2),
                'top_artists': [{'artist': a[0], 'track_count': a[1]} for a in top_artists],
                'top_genres': [{'genre': g[0], 'track_count': g[1]} for g in top_genres]
            }

        finally:
            session.close()

    def enrich_library_metadata(self, max_tracks: int = 100) -> int:
        """Enrich library tracks with metadata from Discogs.

        Args:
            max_tracks: Maximum number of tracks to enrich

        Returns:
            Number of tracks enriched
        """
        if not self.discogs_client:
            console.print("[red]Discogs integration not configured[/red]")
            return 0

        session = self.db_manager.get_session()
        enriched = 0

        try:
            # Get tracks without MusicBrainz IDs (likely need enrichment)
            tracks = session.query(Track).filter(
                Track.musicbrainz_id.is_(None),
                Track.artist.isnot(None),
                Track.album.isnot(None)
            ).limit(max_tracks).all()

            console.print(f"[cyan]Enriching metadata for up to {len(tracks)} tracks...[/cyan]")

            for track in tracks:
                try:
                    release_info = self.get_release_info(track.artist, track.album)

                    if release_info:
                        # Update track with enriched data
                        if release_info.get('year') and not track.year:
                            track.year = release_info['year']

                        if release_info.get('genres') and not track.genre:
                            track.genre = ', '.join(release_info['genres'][:2])

                        enriched += 1
                        console.print(f"[green]✓[/green] Enriched: {track.artist} - {track.title}")

                except Exception as e:
                    console.print(f"[yellow]Could not enrich {track.artist} - {track.title}: {e}[/yellow]")
                    continue

            session.commit()
            console.print(f"\n[green]Enriched {enriched} tracks[/green]")

        finally:
            session.close()

        return enriched

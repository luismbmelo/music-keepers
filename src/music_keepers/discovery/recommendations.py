"""Music discovery and recommendation functionality."""

from typing import List, Dict, Any, Optional
from collections import Counter

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from rich.console import Console
from sqlalchemy.orm import Session

from ..core.database import Track, DatabaseManager
from ..core.config import Config

console = Console()


class MusicDiscovery:
    """Music discovery and recommendation engine."""

    def __init__(self, config: Config, db_manager: DatabaseManager):
        """Initialize music discovery.

        Args:
            config: Configuration instance
            db_manager: Database manager instance
        """
        self.config = config
        self.db_manager = db_manager
        self.spotify_client = None

        # Initialize Spotify client if credentials are available
        client_id = config.get('integrations.spotify.client_id')
        client_secret = config.get('integrations.spotify.client_secret')

        if client_id and client_secret:
            try:
                auth_manager = SpotifyClientCredentials(
                    client_id=client_id,
                    client_secret=client_secret
                )
                self.spotify_client = spotipy.Spotify(auth_manager=auth_manager)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not initialize Spotify client: {e}[/yellow]")

    def get_recommendations(
        self,
        limit: int = 20,
        genre: Optional[str] = None,
        min_rating: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get music recommendations based on library.

        Args:
            limit: Maximum number of recommendations
            genre: Filter by genre
            min_rating: Minimum track rating

        Returns:
            List of recommended tracks
        """
        if not self.spotify_client:
            console.print("[red]Spotify integration not configured[/red]")
            return []

        session = self.db_manager.get_session()
        recommendations = []

        try:
            # Get top artists and tracks from library
            query = session.query(Track)

            if genre:
                query = query.filter(Track.genre.ilike(f"%{genre}%"))
            if min_rating:
                query = query.filter(Track.rating >= min_rating)

            top_tracks = query.order_by(Track.play_count.desc()).limit(5).all()

            if not top_tracks:
                console.print("[yellow]No tracks found matching criteria[/yellow]")
                return []

            # Get seed tracks for Spotify recommendations
            seed_tracks = []
            for track in top_tracks:
                # Search for track on Spotify
                query_str = f"{track.artist} {track.title}"
                results = self.spotify_client.search(q=query_str, type='track', limit=1)

                if results['tracks']['items']:
                    seed_tracks.append(results['tracks']['items'][0]['id'])

            if not seed_tracks:
                console.print("[yellow]Could not find matching tracks on Spotify[/yellow]")
                return []

            # Get recommendations from Spotify
            spotify_recs = self.spotify_client.recommendations(
                seed_tracks=seed_tracks[:5],  # Max 5 seeds
                limit=limit
            )

            for track in spotify_recs['tracks']:
                recommendations.append({
                    'title': track['name'],
                    'artist': ', '.join([artist['name'] for artist in track['artists']]),
                    'album': track['album']['name'],
                    'spotify_url': track['external_urls']['spotify'],
                    'preview_url': track.get('preview_url'),
                    'popularity': track.get('popularity', 0)
                })

        except Exception as e:
            console.print(f"[red]Error getting recommendations: {e}[/red]")

        finally:
            session.close()

        return recommendations

    def find_similar_artists(self, artist_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Find artists similar to the given artist.

        Args:
            artist_name: Name of the artist
            limit: Maximum number of similar artists

        Returns:
            List of similar artists
        """
        if not self.spotify_client:
            console.print("[red]Spotify integration not configured[/red]")
            return []

        try:
            # Search for artist
            results = self.spotify_client.search(q=artist_name, type='artist', limit=1)

            if not results['artists']['items']:
                console.print(f"[yellow]Artist '{artist_name}' not found[/yellow]")
                return []

            artist_id = results['artists']['items'][0]['id']

            # Get similar artists
            similar = self.spotify_client.artist_related_artists(artist_id)

            similar_artists = []
            for artist in similar['artists'][:limit]:
                similar_artists.append({
                    'name': artist['name'],
                    'genres': artist.get('genres', []),
                    'popularity': artist.get('popularity', 0),
                    'spotify_url': artist['external_urls']['spotify']
                })

            return similar_artists

        except Exception as e:
            console.print(f"[red]Error finding similar artists: {e}[/red]")
            return []

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
            ).group_by(Track.artist).order_by(
                func.count(Track.id).desc()
            ).limit(10).all()

            return {
                'total_tracks': total_tracks,
                'total_artists': total_artists,
                'total_albums': total_albums,
                'total_duration_hours': round(total_duration_hours, 2),
                'top_artists': [{'artist': a[0], 'track_count': a[1]} for a in top_artists]
            }

        finally:
            session.close()


# Import for top_artists query
from sqlalchemy import func

"""Database models and management for Music Keepers."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Boolean,
    ForeignKey, create_engine, Text
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session

Base = declarative_base()


class Track(Base):
    """Music track model."""

    __tablename__ = 'tracks'

    id = Column(Integer, primary_key=True)
    file_path = Column(String, unique=True, nullable=False, index=True)
    file_size = Column(Integer)
    file_modified = Column(DateTime)

    # Metadata
    title = Column(String, index=True)
    artist = Column(String, index=True)
    album = Column(String, index=True)
    album_artist = Column(String)
    track_number = Column(Integer)
    disc_number = Column(Integer)
    year = Column(Integer)
    genre = Column(String, index=True)
    duration = Column(Float)  # in seconds

    # Audio properties
    bitrate = Column(Integer)
    sample_rate = Column(Integer)
    channels = Column(Integer)
    format = Column(String)

    # Fingerprinting
    acoustid = Column(String, index=True)
    musicbrainz_id = Column(String, index=True)

    # User data
    rating = Column(Integer)  # 1-5 stars
    play_count = Column(Integer, default=0)
    last_played = Column(DateTime)
    date_added = Column(DateTime, default=datetime.utcnow)

    # Relationships
    playlists = relationship('PlaylistTrack', back_populates='track')
    tags = relationship('TrackTag', back_populates='track')

    def __repr__(self):
        return f"<Track('{self.artist}' - '{self.title}')>"


class Playlist(Base):
    """Playlist model."""

    __tablename__ = 'playlists'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text)
    is_smart = Column(Boolean, default=False)
    smart_criteria = Column(Text)  # JSON string for smart playlist rules
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tracks = relationship('PlaylistTrack', back_populates='playlist')

    def __repr__(self):
        return f"<Playlist('{self.name}')>"


class PlaylistTrack(Base):
    """Many-to-many relationship between playlists and tracks."""

    __tablename__ = 'playlist_tracks'

    id = Column(Integer, primary_key=True)
    playlist_id = Column(Integer, ForeignKey('playlists.id'), nullable=False)
    track_id = Column(Integer, ForeignKey('tracks.id'), nullable=False)
    position = Column(Integer)  # Order in playlist
    added_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    playlist = relationship('Playlist', back_populates='tracks')
    track = relationship('Track', back_populates='playlists')


class Tag(Base):
    """Tag model for categorizing tracks."""

    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False, index=True)
    color = Column(String)  # Hex color code

    # Relationships
    tracks = relationship('TrackTag', back_populates='tag')

    def __repr__(self):
        return f"<Tag('{self.name}')>"


class TrackTag(Base):
    """Many-to-many relationship between tracks and tags."""

    __tablename__ = 'track_tags'

    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey('tracks.id'), nullable=False)
    tag_id = Column(Integer, ForeignKey('tags.id'), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    track = relationship('Track', back_populates='tags')
    tag = relationship('Tag', back_populates='tracks')


class DatabaseManager:
    """Database manager for Music Keepers."""

    def __init__(self, db_path: Path):
        """Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(f'sqlite:///{db_path}')
        self.Session = sessionmaker(bind=self.engine)

    def init_db(self) -> None:
        """Initialize database schema."""
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Get a new database session.

        Returns:
            SQLAlchemy session
        """
        return self.Session()

    def drop_all(self) -> None:
        """Drop all tables (use with caution!)."""
        Base.metadata.drop_all(self.engine)

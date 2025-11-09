# Music Keepers 🎵

An intelligent agent for organizing, discovering, cleaning, and curating your music library.

## Overview

Music Keepers is a comprehensive music library management tool that helps you maintain a clean, well-organized, and enriched music collection. Whether you have thousands of files scattered across folders or a messy collection with inconsistent metadata, Music Keepers provides the tools to bring order to your musical chaos.

## Features

### 🗂️ Organization
- **Smart file organization** - Automatically organize files by artist, album, genre, or custom patterns
- **Folder structure management** - Create and maintain consistent directory hierarchies
- **Metadata extraction** - Read and parse audio file metadata (ID3, Vorbis Comments, MP4, FLAC tags)
- **Batch renaming** - Rename files based on metadata patterns

### 🔍 Discovery
- **Music recommendations** - Discover new music based on your library
- **Artist and release lookup** - Find detailed information about artists and releases
- **Genre exploration** - Explore music by genre and mood
- **API integrations** - Connect with Discogs, Bandcamp, Beatport, Last.fm, and MusicBrainz

### 🧹 Cleaning
- **Duplicate detection** - Find and remove duplicate tracks (by audio fingerprint or metadata)
- **Metadata correction** - Fix inconsistent or incorrect metadata
- **Quality analysis** - Identify low-quality audio files
- **Missing metadata filler** - Automatically fetch missing album art, lyrics, and tags
- **Format standardization** - Convert and normalize audio formats

### 🎨 Curating
- **Smart playlists** - Create dynamic playlists based on rules and criteria
- **Tagging system** - Add custom tags and categories to your music
- **Rating and favorites** - Rate tracks and mark favorites
- **Collection insights** - Analyze your music collection with statistics and visualizations

## Technology Stack

- **Python 3.10+** - Core programming language
- **Mutagen** - Audio metadata handling
- **Click** - Command-line interface
- **SQLAlchemy** - Database ORM for library tracking
- **Rich** - Beautiful terminal output
- **Requests** - API integrations
- **Pydub** - Audio processing
- **Chromaprint/Acoustid** - Audio fingerprinting for duplicate detection

## Installation

```bash
# Clone the repository
git clone https://github.com/luismbmelo/music-keepers.git
cd music-keepers

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

## Quick Start

```bash
# Initialize your music library
music-keepers init /path/to/your/music

# Scan and index your library
music-keepers scan

# Find and remove duplicates
music-keepers clean --duplicates

# Organize files by artist/album structure
music-keepers organize --pattern "{artist}/{album}/{track} - {title}"

# Discover new music based on your library
music-keepers discover --recommendations

# Create a smart playlist
music-keepers playlist create --genre "Jazz" --min-rating 4
```

## Configuration

Music Keepers uses a configuration file at `~/.config/music-keepers/config.yml`:

```yaml
library:
  path: /path/to/your/music
  watch: true  # Auto-scan for changes

database:
  path: ~/.local/share/music-keepers/library.db

integrations:
  discogs:
    token: YOUR_DISCOGS_TOKEN
    user_agent: MusicKeepers/0.1.0
  bandcamp:
    enabled: true  # Uses web scraping
  beatport:
    enabled: true  # Uses web scraping
  lastfm:
    api_key: YOUR_API_KEY
  musicbrainz:
    enabled: true

cleaning:
  duplicate_threshold: 0.95  # Fingerprint similarity threshold
  auto_delete: false  # Prompt before deleting

organization:
  default_pattern: "{artist}/{album}/{track:02d} - {title}"
  handle_compilations: true
```

## Project Structure

```
music-keepers/
├── src/
│   └── music_keepers/
│       ├── __init__.py
│       ├── cli.py              # Command-line interface
│       ├── core/
│       │   ├── __init__.py
│       │   ├── scanner.py      # Library scanning
│       │   ├── database.py     # Database models
│       │   └── config.py       # Configuration management
│       ├── organizer/
│       │   ├── __init__.py
│       │   ├── file_organizer.py
│       │   └── metadata.py
│       ├── cleaner/
│       │   ├── __init__.py
│       │   ├── duplicates.py
│       │   └── metadata_fixer.py
│       ├── discovery/
│       │   ├── __init__.py
│       │   ├── recommendations.py
│       │   └── api_clients.py
│       └── curator/
│           ├── __init__.py
│           ├── playlists.py
│           └── tags.py
├── tests/
├── docs/
├── requirements.txt
├── setup.py
├── pyproject.toml
└── README.md
```

## Roadmap

- [ ] Core library scanning and indexing
- [ ] Basic metadata extraction and organization
- [ ] Duplicate detection using audio fingerprinting
- [ ] Integration with MusicBrainz for metadata enrichment
- [ ] Discogs, Bandcamp, and Beatport integration
- [ ] Last.fm API integration
- [ ] Web UI for library management
- [ ] Machine learning-based recommendations
- [ ] Automatic playlist generation
- [ ] Audio quality analysis and enhancement suggestions
- [ ] Mobile app for remote library access

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Acknowledgments

Built with love for music enthusiasts who appreciate a well-organized collection.

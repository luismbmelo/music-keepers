# Getting Started with Music Keepers

This guide will help you get started with Music Keepers and make the most of its features.

## Installation

### Prerequisites

- Python 3.10 or higher
- ffmpeg (optional, for audio processing)

### Install Music Keepers

```bash
# Clone the repository
git clone https://github.com/luismbmelo/music-keepers.git
cd music-keepers

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Music Keepers
pip install -e .
```

## Initial Setup

### 1. Initialize Your Library

```bash
# Initialize with default music folder (~/Music)
music-keepers init

# Or specify a custom music folder
music-keepers init /path/to/your/music
```

This will:
- Create a configuration file at `~/.config/music-keepers/config.yml`
- Initialize a database at `~/.local/share/music-keepers/library.db`

### 2. Configure API Keys (Optional)

For music discovery features, you'll need API keys from various services:

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys
nano .env
```

Get API keys from:
- **Spotify**: https://developer.spotify.com/dashboard
- **Last.fm**: https://www.last.fm/api/account/create
- **AcoustID**: https://acoustid.org/api-key

### 3. Scan Your Library

```bash
music-keepers scan
```

This will index all music files in your library and extract their metadata.

## Basic Usage

### Organize Your Library

```bash
# Preview how files would be organized (dry-run mode)
music-keepers organize

# Actually organize files
music-keepers organize --execute

# Use a custom pattern
music-keepers organize --pattern "{artist}/{year} - {album}/{track:02d} - {title}" --execute
```

### Find and Remove Duplicates

```bash
# Find duplicates using audio fingerprinting
music-keepers clean duplicates

# Find duplicates using metadata only
music-keepers clean duplicates --metadata

# Remove duplicates (keeps highest quality)
music-keepers clean duplicates --remove

# Auto-remove without confirmation
music-keepers clean duplicates --remove --auto
```

### Discover New Music

```bash
# Get personalized recommendations
music-keepers discover recommendations

# Get recommendations by genre
music-keepers discover recommendations --genre "Jazz" --limit 30

# Find similar artists
music-keepers discover similar "Miles Davis"

# View library statistics
music-keepers discover stats
```

### Manage Playlists

```bash
# Create a manual playlist
music-keepers playlist create "My Favorites" --description "My favorite tracks"

# Create a smart playlist
music-keepers playlist smart "Jazz Classics" --genre "Jazz" --min-rating 4

# Create a smart playlist for workout music
music-keepers playlist smart "Workout Mix" --min-duration 180 --year-start 2010

# List all playlists
music-keepers playlist list

# Export a playlist
music-keepers playlist export 1 --format m3u
```

## Configuration

Edit the configuration file at `~/.config/music-keepers/config.yml`:

```yaml
library:
  path: /path/to/your/music
  watch: false  # Enable to auto-scan for changes
  supported_formats: ['.mp3', '.flac', '.m4a', '.ogg', '.wav']

database:
  path: ~/.local/share/music-keepers/library.db

organization:
  default_pattern: '{artist}/{album}/{track:02d} - {title}'
  handle_compilations: true
  compilation_pattern: 'Compilations/{album}/{track:02d} - {artist} - {title}'

cleaning:
  duplicate_threshold: 0.95
  auto_delete: false
  backup_before_delete: true
```

## Available Pattern Variables

When organizing files, you can use these variables:

- `{artist}` - Track artist
- `{album}` - Album name
- `{album_artist}` - Album artist
- `{title}` - Track title
- `{track}` - Track number
- `{track:02d}` - Track number (zero-padded to 2 digits)
- `{year}` - Release year
- `{genre}` - Genre
- `{disc}` - Disc number

## Tips and Best Practices

1. **Always run organize in dry-run mode first** to preview changes before applying them
2. **Back up your music library** before running bulk operations
3. **Use audio fingerprinting for duplicate detection** for more accurate results
4. **Regularly scan your library** after adding new music
5. **Use smart playlists** to automatically organize music by criteria
6. **Tag your music** to make it easier to create smart playlists later

## Troubleshooting

### Command not found

If `music-keepers` command is not found after installation:

```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Reinstall in editable mode
pip install -e .
```

### Permission errors

If you get permission errors when organizing files:

```bash
# Make sure you have write permissions to your music directory
chmod -R u+w /path/to/your/music
```

### Database locked errors

If you get database locked errors:

```bash
# Make sure no other instance is running
# Close all music-keepers processes and try again
```

## Next Steps

- Explore the [API Integration Guide](api-integration.md)
- Learn about [Advanced Organization Patterns](organization-patterns.md)
- Read about [Smart Playlist Criteria](smart-playlists.md)

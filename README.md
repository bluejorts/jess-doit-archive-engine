[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://black.readthedocs.io/en/stable/_static/license.svg)](https://github.com/Jess-Doit/jess-doit-archive-engine/blob/main/LICENSE)

# Jess Doit's Archive Engine (Emma's Fork)

Automated tool to monitor and archive your favorite SoundCloud, YouTube, and other media pages. Never miss an upload again!

Features:
- 🎵 Automatic downloads from SoundCloud, YouTube, and 1000+ other sites
- 🔄 Continuous monitoring with configurable intervals
- 🏷️ MP3 conversion with embedded metadata, thumbnails, and ID3 tags
- 🐳 Docker support for easy deployment
- 🔐 Cookies support for authenticated downloads
- 📦 Organized file structure by playlist/album/artist
- ⚡ Built on the powerful yt-dlp library

<img src="https://github.com/Jess-Doit/jess-doit-resources/blob/main/jdae/boot.PNG?raw=true" alt="Archive Engine Screenshot" width="500"/>

## Quick Start with Docker (Recommended)

The easiest way to run the archive engine is using Docker:

```bash
# Basic usage - replace with your URLs
docker run -d \
  --name jdae \
  -v /path/to/your/archive:/archive \
  -e URL_LIST="https://soundcloud.com/user1,https://soundcloud.com/user2" \
  ghcr.io/bluejorts/jess-doit-archive-engine:latest
```

### Docker Compose

Create a `docker-compose.yml` file:

```yaml
version: '3.8'
services:
  jdae:
    image: ghcr.io/bluejorts/jess-doit-archive-engine:latest
    container_name: jdae
    restart: unless-stopped
    volumes:
      - ./archive:/archive
      # Optional: Add cookies.txt for authenticated downloads
      # - ./cookies.txt:/archive/cookies.txt:ro
    environment:
      URL_LIST: "https://soundcloud.com/user1,https://soundcloud.com/user2"
      ARCHIVE_FREQUENCY_HOURS: 6
      EMBED_METADATA: "true"
      SKIP_INTRO: "false"
      RATE_LIMIT_SEC: 3
      # Optional: SoundCloud high quality downloads
      # SOUNDCLOUD_OAUTH: "OAuth 2-XXXXXX-XXXXXXXXX-XXXXXXXXXXXX"
      # HIGH_QUALITY_ENABLE: "true"
```

Then run: `docker-compose up -d`

## Configuration

### Environment Variables

All configuration is done through environment variables:

#### Required
- `URL_LIST` - Comma-separated list of URLs to monitor
  - Example: `"https://soundcloud.com/user1,https://soundcloud.com/user2/likes"`

#### Optional
- `OUTPUT_DIR` - Archive directory (default: `/archive`)
- `ARCHIVE_FREQUENCY_HOURS` - Hours between checks (default: `6`, set to `0` to run once)
- `EMBED_METADATA` - Enable MP3 conversion with metadata (default: `true`)
- `SKIP_INTRO` - Skip startup logo (default: `false`)
- `RATE_LIMIT_SEC` - Seconds between requests (default: `3`)
- `LIST_FORMATS` - Debug available formats (default: `false`)
- `HIGH_QUALITY_ENABLE` - Enable high quality downloads (default: `false`)
- `SOUNDCLOUD_OAUTH` - OAuth token for SoundCloud HQ downloads

### SoundCloud High Quality Downloads

For high quality SoundCloud downloads:

1. Get your OAuth token from browser cookies when logged into SoundCloud
2. Format: `OAuth 2-XXXXXX-XXXXXXXXX-XXXXXXXXXXXX`
3. Set environment variables:
   ```bash
   SOUNDCLOUD_OAUTH="OAuth 2-XXXXXX-XXXXXXXXX-XXXXXXXXXXXX"
   HIGH_QUALITY_ENABLE="true"
   ```

### Authenticated Downloads with Cookies

For private playlists or to avoid rate limits:

1. Export cookies from your browser using a cookies.txt extension
2. Place the `cookies.txt` file in your archive directory
3. The engine will automatically detect and use it

## Installation Methods

### Method 1: Docker (Recommended)

Pull and run the pre-built image:
```bash
docker pull ghcr.io/bluejorts/jess-doit-archive-engine:latest
```

### Method 2: Python Installation

Requirements:
- Python 3.8 or newer
- FFmpeg (for audio conversion)

```bash
# Clone the repository
git clone https://github.com/bluejorts/jess-doit-archive-engine.git
cd jess-doit-archive-engine

# Install the package
pip install -e .

# Set environment variables (example)
export URL_LIST="https://soundcloud.com/your-favorite-artist"
export OUTPUT_DIR="$HOME/Music/Archive"

# Run the engine
python -m jdae.start_jdae
```

## Supported URLs

The engine supports URLs from 1000+ sites including:
- SoundCloud (tracks, playlists, user pages, likes)
- YouTube (videos, playlists, channels)
- Bandcamp
- Mixcloud
- And many more...

Any URL supported by [yt-dlp](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md) will work.

## File Organization

Downloads are organized automatically:
```
/archive/
├── PlaylistName/
│   ├── Track1-Artist.mp3
│   └── Track2-Artist.mp3
└── AnotherPlaylist/
    ├── Song-Uploader.mp3
    └── download_archive.txt
```

### Metadata Handling

When downloading from playlists:
- **Artist**: Track's original uploader/creator
- **Album**: Playlist name
- **Album Artist**: Playlist creator
- **Embedded thumbnails** and **ID3 tags** included

## Advanced Usage

### Environment File

Create a `.env` file (copy from `.env.example`):
```bash
cp .env.example .env
# Edit .env with your settings
```

### One-time Download

Set `ARCHIVE_FREQUENCY_HOURS=0` to download once and exit.

### Monitoring Logs

```bash
# Docker logs
docker logs -f jdae

# Docker compose logs
docker-compose logs -f
```

## Troubleshooting

### Common Issues

1. **Permission Errors**: Ensure the archive directory is writable
2. **FFmpeg Not Found**: Install FFmpeg on your system or use Docker
3. **Rate Limiting**: Increase `RATE_LIMIT_SEC` value
4. **Private Content**: Use cookies.txt for authentication

### Getting Help

- Check the [Issues](https://github.com/bluejorts/jess-doit-archive-engine/issues) page
- View logs for detailed error information
- Ensure your URLs are valid and accessible

## Development

### Building from Source

```bash
git clone https://github.com/bluejorts/jess-doit-archive-engine.git
cd jess-doit-archive-engine

# Build Docker image
docker build -t jdae .

# Or install locally
pip install -e .
```

### Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## Acknowledgments

- Built on the amazing [yt-dlp](https://github.com/yt-dlp/yt-dlp) library
- Startup audio clips from [V1984](https://soundcloud.com/v1984/2014-sound-logo-studies)
- Support the original artist: [V1984](https://soundcloud.com/v1984)

## License

MIT License - see [LICENSE](LICENSE) file for details.

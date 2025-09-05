# Multi-stage build for smaller final image
FROM python:3.11-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
WORKDIR /app
COPY setup.py .
COPY jdae/ ./jdae/
RUN pip install --no-cache-dir --user .

# Final stage
FROM python:3.11-slim

# Install runtime dependencies including ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and directories
RUN useradd -m -u 1000 archiver && \
    mkdir -p /archive /app && \
    chown -R archiver:archiver /archive /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/archiver/.local

# Copy application
WORKDIR /app
COPY --chown=archiver:archiver . .

# Set environment variables
ENV PATH=/home/archiver/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Default environment variables (can be overridden at runtime)
ENV OUTPUT_DIR=/archive
ENV ARCHIVE_FREQUENCY_HOURS=6
ENV EMBED_METADATA=true
ENV SKIP_INTRO=false
ENV RATE_LIMIT_SEC=3
ENV LIST_FORMATS=false
ENV HIGH_QUALITY_ENABLE=false

# Required environment variables (must be set at runtime):
# URL_LIST - Comma-separated list of URLs to archive
# 
# Optional: Place a cookies.txt file in /archive directory for authenticated downloads
# Export cookies from your browser using a cookies.txt extension
#
# Optional environment variables:
# SOUNDCLOUD_OAUTH - OAuth token for high quality SoundCloud downloads
# OUTPUT_DIR - Archive output directory (default: /archive)
# ARCHIVE_FREQUENCY_HOURS - Hours between archive checks (default: 6)
# EMBED_METADATA - Enable metadata embedding (default: true)
# SKIP_INTRO - Skip intro logo (default: false)
# RATE_LIMIT_SEC - Seconds between requests (default: 3)
# LIST_FORMATS - Debug available formats (default: false)
# HIGH_QUALITY_ENABLE - Enable HQ downloads (default: false)

# Switch to non-root user
USER archiver

# Define volume for archive
VOLUME ["/archive"]

# Run the archive engine directly
ENTRYPOINT ["python", "-m", "jdae.start_jdae"]
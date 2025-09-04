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
    mkdir -p /config /archive /app && \
    chown -R archiver:archiver /config /archive /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/archiver/.local

# Copy application
WORKDIR /app
COPY --chown=archiver:archiver . .

# Copy default config files to a template directory
RUN mkdir -p /app/config-template && \
    cp /app/jdae/config/*.ini /app/config-template/ && \
    chown -R archiver:archiver /app/config-template

# Create startup script to handle config initialization
RUN echo '#!/bin/bash\n\
# Copy default configs if they dont exist\n\
if [ ! -f /config/gen_config.ini ]; then\n\
    echo "Initializing config files..."\n\
    cp /app/config-template/*.ini /config/\n\
    echo "Config files created in /config/"\n\
    echo "Please edit /config/gen_config.ini and /config/url_list.ini before restarting"\n\
    exit 0\n\
fi\n\
# Override the config path for the application\n\
export JDAE_CONFIG_PATH=/config\n\
cd /app\n\
python -m jdae.start_jdae' > /app/entrypoint.sh && \
    chmod +x /app/entrypoint.sh

# Set environment variables
ENV PATH=/home/archiver/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER archiver

# Define volumes for config and archive
VOLUME ["/config", "/archive"]

# Run the startup script
ENTRYPOINT ["/app/entrypoint.sh"]
FROM python:3.11-slim-bookworm

# Install system dependencies and apply security updates
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /var/cache/apt/archives/*

# Install Trivy (latest version)
RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Create non-root user for security (before copying files)
RUN useradd -m -u 1000 sparta

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all scripts
COPY scripts/ ./scripts/

# Make scripts executable
RUN chmod +x /app/scripts/*.py

# Copy entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Change ownership of /app to non-root user
RUN chown -R sparta:sparta /app

# Ensure Trivy is accessible (in /usr/local/bin which is in PATH)
# Switch to non-root user
USER sparta

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]


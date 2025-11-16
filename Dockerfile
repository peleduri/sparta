# Build stage: Use dev variant to install packages
FROM cgr.dev/chainguard/python:latest-dev AS builder

# Install system dependencies (Chainguard uses apk)
RUN apk add --no-cache \
    git \
    curl \
    ca-certificates

# Install Trivy (latest version)
RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Create non-root user for security
RUN adduser -D -u 1000 sparta

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

# Runtime stage: Use minimal latest variant
FROM cgr.dev/chainguard/python:latest

# Copy installed packages and tools from builder
COPY --from=builder /usr/local/bin/trivy /usr/local/bin/trivy
COPY --from=builder /usr/bin/git /usr/bin/git
COPY --from=builder /usr/bin/curl /usr/bin/curl
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Copy application files
COPY --from=builder --chown=sparta:sparta /app /app

# Copy user from builder
COPY --from=builder /etc/passwd /etc/passwd
COPY --from=builder /etc/group /etc/group

# Set working directory
WORKDIR /app

# Switch to non-root user
USER sparta

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]


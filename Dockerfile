# Build stage: Use dev variant to install packages
FROM cgr.dev/chainguard/python:latest-dev AS builder

# Switch to root for system package installation (required for apk)
USER root

# Install system dependencies
RUN apk add --no-cache \
    git \
    wget \
    ca-certificates

# Install Trivy (latest version) - download and install directly
RUN ARCH=$(uname -m) && \
    case ${ARCH} in \
        x86_64) TRIVY_ARCH="64bit" ;; \
        aarch64|arm64) TRIVY_ARCH="ARM64" ;; \
        *) TRIVY_ARCH="64bit" ;; \
    esac && \
    TRIVY_VERSION=$(wget -qO- https://api.github.com/repos/aquasecurity/trivy/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/') && \
    wget -qO- https://github.com/aquasecurity/trivy/releases/download/${TRIVY_VERSION}/trivy_${TRIVY_VERSION#v}_Linux-${TRIVY_ARCH}.tar.gz | \
    tar -xz -C /tmp && \
    mv /tmp/trivy /usr/local/bin/trivy && \
    chmod +x /usr/local/bin/trivy && \
    trivy --version

# Create non-root user (requires root)
RUN adduser -D -u 1000 sparta

# Set working directory
WORKDIR /app

# Copy requirements with proper ownership
COPY --chown=sparta:sparta requirements.txt .

# Switch to non-root user before installing Python packages
USER sparta

# Install Python dependencies as non-root user (pip installs to user directory)
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy all scripts with proper ownership
COPY --chown=sparta:sparta scripts/ ./scripts/

# Copy entrypoint with proper ownership
COPY --chown=sparta:sparta entrypoint.sh .

# Make scripts executable (as non-root user, can set execute bit on own files)
RUN chmod +x /app/entrypoint.sh && \
    chmod +x /app/scripts/*.py

# Runtime stage: Use dev variant (includes necessary tools)
FROM cgr.dev/chainguard/python:latest-dev

# Copy user from builder
COPY --from=builder /etc/passwd /etc/passwd
COPY --from=builder /etc/group /etc/group

# Copy installed packages and tools from builder
COPY --from=builder /usr/local/bin/trivy /usr/local/bin/trivy
COPY --from=builder /usr/bin/git /usr/bin/git
COPY --from=builder /usr/bin/wget /usr/bin/wget
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Copy application files with proper ownership (already set in builder)
COPY --from=builder --chown=sparta:sparta /app /app

# Copy Python packages from user directory
COPY --from=builder --chown=sparta:sparta /home/sparta/.local /home/sparta/.local

# Set working directory
WORKDIR /app

# Add user's local bin to PATH for Python packages
ENV PATH="/home/sparta/.local/bin:${PATH}"

# Switch to non-root user immediately (security: never use root)
USER sparta

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]


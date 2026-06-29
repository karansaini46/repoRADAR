# Stage 1: Tooling & Scanners
FROM python:3.12-slim AS builder

# Install system dependencies required for scanners
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install TruffleHog
RUN curl -sSfL https://raw.githubusercontent.com/trufflesecurity/trufflehog/main/scripts/install.sh | sh -s -- -b /usr/local/bin

# Install Semgrep
RUN pip install semgrep

# Install Trivy
RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# Install Gitleaks
RUN wget https://github.com/gitleaks/gitleaks/releases/download/v8.18.1/gitleaks_8.18.1_linux_x64.tar.gz \
    && tar -xzf gitleaks_8.18.1_linux_x64.tar.gz \
    && mv gitleaks /usr/local/bin/ \
    && rm gitleaks_8.18.1_linux_x64.tar.gz

# Stage 2: Final App
FROM python:3.12-slim

# Copy tools from builder
COPY --from=builder /usr/local/bin/trufflehog /usr/local/bin/trufflehog
COPY --from=builder /usr/local/bin/semgrep /usr/local/bin/semgrep
COPY --from=builder /usr/local/bin/trivy /usr/local/bin/trivy
COPY --from=builder /usr/local/bin/gitleaks /usr/local/bin/gitleaks

# Install runtime dependencies (git is needed for cloning)
RUN apt-get update && apt-get install -y \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
# We would normally copy requirements.txt here, but since it doesn't exist yet, 
# we'll create a dummy one or assume it's mapped in development.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Default command (overridden in docker-compose)
CMD ["uvicorn", "autoscan.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

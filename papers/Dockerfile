# Containerized Reproducibility Environment for HSCI
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy repository content
COPY . .

# Default entrypoint runs full regression and benchmark verification
CMD ["pytest", "hsci/tests/", "-v"]

FROM python:3.9-slim

WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create persistent directory for learning artifacts
RUN mkdir -p /app/data && chmod 755 /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run application
CMD ["python", "run_app.py", "--host", "0.0.0.0", "--port", "8000", "--no-browser"]

FROM python:3.11-slim

WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Make start script executable
RUN chmod +x start.sh

# Create persistent directory for learning artifacts
RUN mkdir -p /app/data && chmod 755 /app/data

# Expose port (dynamic via ENV)
ENV PORT=8000
EXPOSE $PORT

# Run application via start script
CMD ["./start.sh"]

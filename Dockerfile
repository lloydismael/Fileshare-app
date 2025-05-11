FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY fileshare.py .
COPY templates templates/
RUN mkdir -p uploads && \
    chown -R nobody:nogroup /app/uploads

# Set environment variables
ENV FLASK_APP=fileshare.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER nobody

# Expose port
EXPOSE 5000

# Run the application with eventlet
CMD ["python", "fileshare.py"]

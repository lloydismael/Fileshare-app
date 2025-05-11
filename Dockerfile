FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt eventlet

# Copy application files
COPY fileshare.py .
COPY templates templates/
RUN mkdir -p uploads

# Set environment variables
ENV FLASK_APP=fileshare.py
ENV FLASK_ENV=production

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]

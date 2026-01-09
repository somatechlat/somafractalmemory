# SFM API Dockerfile for Docker Compose deployment
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY api-requirements.txt .
RUN pip install --no-cache-dir -r api-requirements.txt
RUN pip install --no-cache-dir uvicorn[standard]

# Copy application code
COPY manage.py .
COPY somafractalmemory/ somafractalmemory/
COPY common/ common/

EXPOSE 10101

# Use uvicorn for production ASGI
CMD ["python", "-m", "uvicorn", "somafractalmemory.asgi:application", "--host", "0.0.0.0", "--port", "10101"]

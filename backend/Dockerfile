# Build: 2026-04-21
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Copy requirements first (better caching)
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY app ./app

# Expose port
EXPOSE 8000

# Run FastAPI with uvicorn
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}

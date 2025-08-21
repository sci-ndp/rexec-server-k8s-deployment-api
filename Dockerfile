FROM python:3.11-slim

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Optional: Set python runtime configuration environment variables
# PYTHONUNBUFFERED: Makes logs appear immediately in container instead of being buffered
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files to reduces disk usage
ENV PYTHONUNBUFFERED=1 \  
    PYTHONDONTWRITEBYTECODE=1

# Set working directory
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=appuser:appuser api/ ./api/
COPY --chown=appuser:appuser static/ ./static/

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

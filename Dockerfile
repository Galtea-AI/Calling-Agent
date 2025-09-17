# Use Python 3.10 slim image as base
FROM python:3.10-slim

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml ./

# Copy application code
COPY . .

# Install dependencies and the package using uv pip
RUN uv pip install --system --no-cache-dir .

# Create a non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["uv", "run", "uvicorn", "agent_twilio:app", "--host", "0.0.0.0", "--port", "8001"]
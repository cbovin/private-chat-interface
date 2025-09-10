# Use Python 3.11 with build tools (more stable than 3.13 for complex packages)
FROM python:3.11

# Set working directory
WORKDIR /app

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    build-essential \
    rustc \
    cargo \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies with pre-compiled wheels where possible
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create keys directory and set permissions
RUN mkdir -p keys \
    && chmod 755 keys

# Expose port
EXPOSE 8000

# Health check - use curl to check health endpoint
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ || exit 1

# Set Python path to include src directory
ENV PYTHONPATH=/app/src:$PYTHONPATH

# Run the application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

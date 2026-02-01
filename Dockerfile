# ============================================
# Perplexo Bot - Dockerfile
# Multi-stage build for Python + Node.js
# ============================================

# Stage 1: Python dependencies
FROM python:3.11-slim as python-builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Node.js dependencies
FROM node:18-slim as node-builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci --only=production

# Stage 3: Final image
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=python-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-builder /usr/local/bin /usr/local/bin

# Copy Node.js modules
COPY --from=node-builder /app/node_modules ./node_modules

# Copy application code
COPY src/ ./src/
COPY ecosystem.config.js .
COPY .env.example .env

# Create necessary directories
RUN mkdir -p data logs

# Expose ports
EXPOSE 5000 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Start command
CMD ["python3", "src/mcp_server.py"]
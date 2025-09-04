# ----------------------
# 1. Build stage
# ----------------------
FROM python:3.12-slim AS builder

# Install build tools (for compiling deps like psycopg2)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency files first (for caching)
COPY pyproject.toml uv.lock ./

# Install uv and export dependencies
RUN pip install uv \
    && uv export --format requirements-txt > requirements.txt \
    && pip install --prefix=/install -r requirements.txt

# ----------------------
# 2. Runtime stage
# ----------------------
FROM python:3.12-slim

WORKDIR /app

# Copy only installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Use a non-root user (security best practice)
RUN useradd -m appuser
USER appuser

# Expose FastAPI port
EXPOSE 8000

# Run with uvicorn (using uv is fine too if you prefer)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

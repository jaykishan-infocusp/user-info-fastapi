# Dockerfile
FROM python:3.12-slim

# Install uv
RUN pip install uv

WORKDIR /app

# Copy pyproject.toml and lockfile first (layer caching!)
COPY pyproject.toml uv.lock ./

# Install dependencies system-wide (no .venv inside container)
RUN uv export --format requirements-txt > requirements.txt
RUN pip install -r requirements.txt

# Copy app source
COPY . .

# Run app with uvicorn
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

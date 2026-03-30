FROM python:3.12-slim AS base

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install system dependencies (libgraphite2 + libicu needed by tectonic at runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgraphite2-3 \
    libicu76 \
    libssl3t64 \
    && rm -rf /var/lib/apt/lists/*

# Install tectonic (LaTeX compiler for PDF generation)
WORKDIR /tmp
RUN curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh \
    && install -m 755 tectonic /usr/local/bin/tectonic \
    && rm -f tectonic
WORKDIR /app

# Install Poetry
ENV POETRY_VERSION=1.8.5
RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

# Disable virtualenv creation inside Docker (install to system Python)
RUN poetry config virtualenvs.create false

# Copy dependency files first (layer caching: deps change less often than code)
COPY pyproject.toml poetry.lock* ./

# Install Python dependencies (--no-root: don't install the project itself yet)
RUN poetry install --no-root --no-interaction --no-ansi

# Copy application source
COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

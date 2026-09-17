# One process, no build step, no root. The image carries the app and its
# config; the database lives outside it (ERPSIM_DATABASE_URL).
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir . && \
    useradd --create-home --uid 10001 erpsim

COPY config ./config
COPY static ./static
COPY rules ./rules

USER erpsim
EXPOSE 8000

# Migrations run at startup; see src/erpsim/migrations.py.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

CMD ["uvicorn", "erpsim.main:app", "--host", "0.0.0.0", "--port", "8000"]

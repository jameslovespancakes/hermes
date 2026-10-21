# syntax=docker/dockerfile:1
# Live delivery ETA API: serves the trained model in server/model_store/<city>/ with FastAPI.
#   docker build -t hermes-eta .            (CITY build arg, default yt)
#   docker run --rm -p 8000:8000 hermes-eta  ->  http://localhost:8000/docs
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# LightGBM needs the OpenMP runtime.
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /uvx /bin/

WORKDIR /app

# Dependencies first (cached layer), exactly as locked; no dev tools in the image.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY server ./server

# Data: the pinned, checksum-verified city file from Hugging Face.
ARG CITY=yt
ENV ETA_CITY=${CITY}
RUN /app/.venv/bin/python -m server.cli download --city ${CITY}

RUN useradd --create-home --uid 10001 app   # read-only app files stay root-owned
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD /app/.venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

CMD ["/app/.venv/bin/uvicorn", "server.api.app:app", "--host", "0.0.0.0", "--port", "8000"]

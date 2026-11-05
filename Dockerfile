# syntax=docker/dockerfile:1.7
# SecureFlight API image.
# Python 3.12 is required: the pinned wheels in requirements.txt (pydantic-core,
# uvloop, httptools, watchfiles) fail to build on Python 3.14.
# requirements.txt also holds test deps (pytest, mongomock); it is used as-is
# because the exercise keeps the application untouched.

# python:3.12-slim pinned by digest for reproducible builds (bump via Dependabot).
ARG PYTHON_IMAGE=python:3.12-slim@sha256:4840d514c583a4d3d8cad3940e68dee6f0f6f3635c12fcd0a3d74c21a5b93a54

# ---- builder: resolve dependencies into an isolated virtualenv --------------
FROM ${PYTHON_IMAGE} AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

COPY requirements.txt .
RUN pip install --requirement requirements.txt

# ---- runtime: minimal, non-root ---------------------------------------------
FROM ${PYTHON_IMAGE} AS runtime

ARG APP_UID=10001

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # api/main.py imports "flights.router" (no "api." prefix) while the other
    # modules import "api.*", so both /app and /app/api must be importable.
    PYTHONPATH=/app:/app/api

RUN useradd --uid "${APP_UID}" --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY --chown=root:root api/ ./api/

USER ${APP_UID}
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/', timeout=2).status == 204 else 1)"]

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

ARG PYTHON_IMAGE=python:3.14-slim
FROM ${PYTHON_IMAGE} AS builder
WORKDIR /build
COPY requirements.txt requirements-live.txt ./
RUN python -m pip install --no-cache-dir --prefix=/install -r requirements-live.txt

FROM ${PYTHON_IMAGE} AS runtime
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 WORKSHOP_HOST=0.0.0.0 WORKSHOP_PORT=8000 WORKSHOP_DB=/data/state/workshop.db
WORKDIR /app
COPY --from=builder /install /usr/local
COPY workshop/ ./workshop/
RUN useradd --system --no-create-home workshop && mkdir -p /data/state && chown workshop /data/state
USER workshop
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=45s --retries=3 \
  CMD ["python", "-m", "workshop", "health"]
CMD ["python", "-m", "workshop", "serve"]

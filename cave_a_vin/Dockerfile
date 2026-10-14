ARG BUILD_FROM=python:3.12-slim-bookworm
FROM ${BUILD_FROM}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CAVE_DATA_DIR=/data \
    CAVE_PORT=8099

WORKDIR /opt/cave
# Bibliothèques de traitement d'image (détourage des photos). L'application elle-même
# n'utilise que la bibliothèque standard Python.
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app

EXPOSE 8099
VOLUME ["/data"]
HEALTHCHECK --interval=60s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8099/api/health', timeout=4)" || exit 1
CMD ["python", "-m", "app"]

LABEL io.hass.type="addon" io.hass.name="Cave à vin"

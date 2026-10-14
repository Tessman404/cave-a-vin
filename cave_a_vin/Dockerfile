ARG BUILD_FROM=python:3.12-alpine
FROM ${BUILD_FROM}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    CAVE_DATA_DIR=/data \
    CAVE_PORT=8099

# Aucune dépendance externe : uniquement la bibliothèque standard Python.
WORKDIR /opt/cave
COPY app ./app

EXPOSE 8099
VOLUME ["/data"]
HEALTHCHECK --interval=60s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8099/api/health', timeout=4)" || exit 1
CMD ["python", "-m", "app"]

LABEL io.hass.type="addon" io.hass.name="Cave à vin"

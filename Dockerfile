FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY web /app/web
COPY scripts /app/scripts
COPY docker/entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh /app/scripts/sync_openwebui.py

EXPOSE 8080

ENTRYPOINT ["/app/entrypoint.sh"]

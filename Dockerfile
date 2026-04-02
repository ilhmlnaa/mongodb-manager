FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MONGO_MANAGER_WEB_HOST=0.0.0.0 \
    MONGO_MANAGER_WEB_PORT=8000 \
    PATH="/app/mongo-tools/linux/bin:${PATH}"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libstdc++6 curl \
    && rm -rf /var/lib/apt/lists/*

COPY scripts/install_mongodb_tools.sh /tmp/install_mongodb_tools.sh
RUN chmod +x /tmp/install_mongodb_tools.sh \
    && /tmp/install_mongodb_tools.sh \
    && rm -f /tmp/install_mongodb_tools.sh

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

USER app

# EXPOSE 8000

CMD ["python", "main.py", "web"]

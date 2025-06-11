FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    git \
    logrotate \
    curl && \
    pip install --no-cache-dir poetry && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md /app/

RUN sed -i '0,/version = .*/ s//version = "0.1.0"/' pyproject.toml

RUN poetry config virtualenvs.create false && \
    poetry install --with dev --no-root

COPY config.yaml /app/
COPY scenarios_conductor /app/scenarios_conductor

RUN pip install .

COPY logrotate.conf /etc/logrotate.d/scenarios_conductor
RUN chmod 0644 /etc/logrotate.d/scenarios_conductor

CMD ["launch_app"]

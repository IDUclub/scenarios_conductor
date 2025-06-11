# Scenarios Conductor

**Scenarios Conductor** is a fully autonomous asynchronous microservice written in Python using the [`otteroad`](https://github.com/Jesusya-26/otteroad) framework. It is designed to orchestrate the creation of base scenarios in response to Kafka events.

This service runs in the background, consumes events from Kafka topics, processes them, and interacts with external services like Urban API.

---

## Main Features

- **Kafka-based orchestration** — consumes events like `ProjectCreated` and `RegionalScenarioCreated`
- **Automatic base scenario creation** logic (see below)
- **Prometheus integration** — exports internal metrics on a dedicated port
- **Urban API integration** — communicates with an external service via HTTP
- **Structured logging** — powered by [`structlog`](https://www.structlog.org/) and supports JSONLines output

---

## Message Processing Logic

This service handles two main types of events from Kafka, both encoded using Avro and validated against a Schema Registry:

### `ProjectCreated`

When a new project is created, the service:

- Retrieves **all regional scenarios** of the same user (from Urban API)
- For each regional scenario:
  - **Creates a base scenario** (if one doesn’t already exist)

### `RegionalScenarioCreated`

When a new regional scenario is created, the service:

- Retrieves **all projects** of the same user in the given territory (from Urban API)
- For each project:
  - **Creates a base scenario** (if one doesn’t already exist)

This ensures logical consistency between user projects and regional scenarios in the system.

---

## 🛠Running Locally

1. **Install dependencies** using [Poetry](https://python-poetry.org/):
```bash
  poetry install
```

2. **Set up configuration**:

   * Copy and edit `config.yaml.example` → `config.yaml`
   * Define `CONFIG_PATH` as an environment variable pointing to your config:

     ```bash
     export CONFIG_PATH=./config.yaml
     ```
     
        Or using `.env` file.


3. **Run the app**:

   ```bash
   poetry run launch_app
   ```

   Or using `make`:

   ```bash
   make run-app
   ```

---

## Running in Docker

1. **Create config files**:

   ```bash
   cp config.yaml.example config.yaml
   cp env.example .env
   ```

2. **Run the service**:

   ```bash
   docker-compose up -d --build
   ```

> ⚠️ Ensure that your Kafka and Schema Registry services are accessible from the container (e.g., via `host.docker.internal` or proper Docker network configuration).

---

## Logging

The service uses [`structlog`](https://www.structlog.org/) for structured logging.

* Log entries are emitted in **JSON Lines** format when saved to file.
* You can pretty-print logs using:

  ```bash
  pygmentize -l json logs/info.log
  ```

> Logging configuration is defined in `config.yaml` — you can control output files, log levels, and formats.

---

## Metrics

The service exposes internal metrics in **Prometheus-compatible** format.

* Default metrics port: `9000`
* Endpoint: `http://localhost:9000/metrics`
* Can be disabled via config (`prometheus.disable: true`)

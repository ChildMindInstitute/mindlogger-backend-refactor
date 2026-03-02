PORT = 8000
HOST = localhost

TEST_COMMAND = PYTHONPATH=src uv run pytest -s -vv --alluredir=allure-results
COVERAGE_COMMAND = coverage run --branch --concurrency=thread,gevent -m pytest  
REPORT_COVERAGE_COMMAND = coverage html --show-contexts --title "Coverage for ${SHA}"

EXPORT_COMMAND = python src/export_spec.py

RUFF_COMMAND = uv run ruff
MYPY_COMMAND = uv run mypy

DOCKER_COMPOSE_EXISTS := $(shell command -v docker-compose 2> /dev/null)

ifeq (${DOCKER_COMPOSE_EXISTS}, 0)
    DOCKER_COMPOSE_CMD=docker-compose
else
    DOCKER_COMPOSE_CMD=docker compose
endif

DOCKER_EXEC = ${DOCKER_COMPOSE_CMD} run --rm -u root app
COVERAGE_DOCKER_EXEC = ${DOCKER_COMPOSE_CMD} run --rm -u root app

# ###############
# Local
# ###############

.PHONY: install
install:
	@uv sync

# NOTE: `make audit` for all vulnerabilities
# NOTE: `make audit SEVERITY=high` for high vulnerabilities
# NOTE: `make audit SEVERITY=critical` for critical vulnerabilities
.PHONY: audit
audit: install
	@uvx uv-secure --severity $(or $(SEVERITY), low) --show-severity --aliases

# NOTE: Make sure that Redis server is running
.PHONY: run
run:
	PYTHONPATH=src uv run uvicorn src.main:app --proxy-headers --host ${HOST} --port ${PORT} --reload

# Run taskiq worker to process background tasks (MFA emails, etc.)
.PHONY: run-worker
run-worker:
	PYTHONPATH=src uv run taskiq worker worker:worker -fsd -tp src/**/tasks.py

# Start every dependency.  Not always needed
.PHONY: start-all-deps
start-all-deps:
	${DOCKER_COMPOSE_CMD} up -d redis postgres mailhog rabbitmq minio worker scheduler

# Start just the necessary day-to-day dependencies
.PHONY: start-deps
start-deps:
	${DOCKER_COMPOSE_CMD} up redis postgres rabbitmq


# Build everything in the compose file
.PHONY: build-all
build-all:
	${DOCKER_COMPOSE_CMD} build app worker scheduler postgres


.PHONY: test
test:
	${TEST_COMMAND} ./

.PHONY: migrate
migrate:
	uv run alembic upgrade head

# NOTE: cq == "Code quality"
.PHONY: cq
cq:
	${RUFF_COMMAND} check . && ${RUFF_COMMAND} format --check . && ${MYPY_COMMAND} .

# NOTE: cqf == "Code quality fix"
.PHONY: cqf
cqf:
	${RUFF_COMMAND} format . && ${RUFF_COMMAND} check --fix . && ${MYPY_COMMAND} .


# Setting pre-commit hooks to search for aws keys
.PHONY: aws-scan
aws-scan:
	git secrets --register-aws --global && \
	pre-commit install

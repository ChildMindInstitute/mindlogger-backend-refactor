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

# NOTE: Make sure that Redis server is running
.PHONY: run
run:
	PYTHONPATH=src uv run uvicorn src.main:app --proxy-headers --host ${HOST} --port ${PORT} --reload

.PHONY: run_local
run_local:
	${DOCKER_COMPOSE_CMD} up -d redis postgres mailhog rabbitmq minio

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

PORT = 8000
HOST = localhost

TEST_COMMAND = pytest -s -vv

RUFF_COMMAND = ruff
ISORT_COMMAND = isort
MYPY_COMMAND = mypy

DOCKER_EXEC = docker-compose run --rm app

# ###############
# Local
# ###############

# NOTE: Make sure that Redis server is running
.PHONY: run
run:
	uvicorn src.main:app --proxy-headers --host ${HOST} --port ${PORT} --reload

.PHONY: run_local
run_local:
	docker-compose up -d redis postgres mailhog rabbitmq

.PHONY: test
test:
	${TEST_COMMAND} ./

# NOTE: cq == "Code quality"
.PHONY: cq
cq:
	${RUFF_COMMAND} ./ && ${ISORT_COMMAND} ./ && ${MYPY_COMMAND} ./

# NOTE: This command is used to run migration from Mongo to Postgres
.PHONY: migrate
migrate:
	python src/apps/migrate/run.py

.PHONY: migrate_answer
migrate_answer:
	python src/apps/migrate/answers/run.py

# ###############
# Docker
# ###############

# NOTE: dcq == "Docker code quality"
.PHONY: dcq
dcq:
	${DOCKER_EXEC} \
		${RUFF_COMMAND} ./ && ${ISORT_COMMAND} ./ && ${MYPY_COMMAND} ./

.PHONY: dtest
dtest:
	${DOCKER_EXEC} \
		${TEST_COMMAND} ./


.PHONY: dcheck
dcheck:
	${DOCKER_EXEC} \
		${RUFF_COMMAND} ./ && ${ISORT_COMMAND} ./ && ${MYPY_COMMAND} ./ && ${TEST_COMMAND}


# Setting pre-commit hooks to search for aws keys
.PHONY: aws-scan
aws-scan:
	git secrets --register-aws --global && \
	pre-commit install

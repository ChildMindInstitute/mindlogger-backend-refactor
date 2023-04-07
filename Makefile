PORT = 8000
HOST = localhost

TEST_COMMAND = pytest -s -vvv

BLACK_COMMAND = black
FLAKE8_COMMAND = flake8
ISORT_COMMAND = isort
MYPY_COMMAND = mypy

DOCKER_EXEC = docker-compose exec fastapi

# ###############
# Local
# ###############

# NOTE: Make sure that Redis server is running
.PHONY: run
run:
	uvicorn src.main:app --proxy-headers --host ${HOST} --port ${PORT} --reload

# NOTE: This command is used to run migration from Mongo to Postgres
.PHONY: run_migration_mongo_to_postgres
run_migration_mongo_to_postgres:
	uvicorn src.apps.migrate.mongo_to_psql:app --proxy-headers --host 0.0.0.0 --port 8080

.PHONY: run_local
run_local:
	docker-compose up -d redis postgres mailhog

.PHONY: test
test:
	${TEST_COMMAND} ./

# NOTE: cq == "Code quality"
.PHONY: cq
cq:
	${BLACK_COMMAND} ./ && ${FLAKE8_COMMAND} ./ && ${ISORT_COMMAND} ./ && ${MYPY_COMMAND} ./



# ###############
# Docker
# ###############

# NOTE: dcq == "Docker code quality"
.PHONY: dcq
dcq:
	${DOCKER_EXEC} \
		${BLACK_COMMAND} ./ && ${FLAKE8_COMMAND} ./ && ${ISORT_COMMAND} ./ && ${MYPY_COMMAND} ./

.PHONY: dtest
dtest:
	${DOCKER_EXEC} \
		${TEST_COMMAND} ./


.PHONY: dcheck
dcheck:
	${DOCKER_EXEC} \
		${BLACK_COMMAND} ./ && ${FLAKE8_COMMAND} ./ && ${ISORT_COMMAND} ./ && ${MYPY_COMMAND} ./ \
		&& ${TEST_COMMAND}

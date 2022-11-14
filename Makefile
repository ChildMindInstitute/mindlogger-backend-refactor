PORT = 8012
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
	uvicorn src.main:app --proxy-headers --host ${HOST} --port ${PORT} --debug

.PHONY: test
test:
	${TEST_COMMAND} ./

# NOTE: cq == "Code quality"
.PHONY: cq
cq:
	${BLACK_COMMAND} ./ && ${FLAKE8_COMMAND} ./ && ${ISORT_COMMAND} ./ && ${MYPY_COMMAND} ./


.PHONY: check
check:
	${BLACK_COMMAND} ./ && ${FLAKE8_COMMAND} ./ && ${ISORT_COMMAND} ./ && ${MYPY_COMMAND} ./ \
	&& ${TEST_COMMAND}


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

# Test Suite

## Unit/Integration tests

Current there is no separation between unit and integration tests.  To
run the full suite:

```shell
make test
```

## Test coverage

To correctly calculate test coverage, you need to run the coverage with the `--concurrency=thread,gevent` parameter:

```shell
uv run coverage run --branch --concurrency=thread,gevent -m pytest
uv run coverage report -m
```

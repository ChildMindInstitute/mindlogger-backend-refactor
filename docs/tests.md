# Test Suite

 > [!CAUTION]
 > Older tests have been separated into a legacy suite in `tests/legacy`.  
 > Do not add tests inline anywhere in the `src` (as was the old model)
 > 
 > The legacy test suite still requires
 
 > [!IMPORTANT]
 > The old test suite is deprecated and will be removed in a future release.  
 > Please add new tests to their relevant test suite instead.  Pure unit tests should be created in `tests/unit`  
 > and integration tests should be created in `tests/integration`.

## Full Test Suite

 > [!NOTE]
 > This will run the legacy test suite, therefore you must have postgres, rabbitmq, and redis running
 > via docker.

To run the full suite:

```shell
make test
```

## Running Tests Separately

To run just unit tests:

```shell
make test-unit
```

To run just integration tests:

```shell
make test-int
```

## Test coverage

To correctly calculate test coverage, you need to run the coverage with the `--concurrency=thread,gevent` parameter:

```shell
uv run coverage run --branch --concurrency=thread,gevent -m pytest
uv run coverage report -m
```

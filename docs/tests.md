## Test coverage

To correctly calculate test coverage, you need to run the coverage with the `--concurrency=thread,gevent` parameter:

```bash
uv run coverage run --branch --concurrency=thread,gevent -m pytest
uv run coverage report -m
```

## Running test via docker

(This is how tests are running on CI)

```bash
# Check the code quality
make dcq

# Check tests passing
make dtest

# Check everything in one hop
make dcheck
```
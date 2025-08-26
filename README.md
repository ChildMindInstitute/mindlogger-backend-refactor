# Child Mind Institute - Curious Backend API

This repository is used for the backend of the [Curious](https://mindlogger.org/) application stack.

---

## Getting Started

* Curious Admin - [GitHub Repo](https://github.com/ChildMindInstitute/mindlogger-admin)
* Curious Backend - **This Repo**
* Curious Mobile App - [GitHub Repo](https://github.com/ChildMindInstitute/mindlogger-app-refactor)
* Curious Web App - [GitHub Repo](https://github.com/ChildMindInstitute/mindlogger-web-refactor)

---

## Technologies

- ✅ [Python 3.13](https://www.python.org/downloads/release/python-3132/)
- ✅ [uv](https://docs.astral.sh/uv/)
- ✅ [FastAPI](https://fastapi.tiangolo.com)
- ✅ [Postgresql](https://www.postgresql.org/docs/14/index.html)
- ✅ [Redis](https://redis.io)
- ✅ [Docker](https://docs.docker.com/get-docker/)
- ✅ [Pydantic](https://pydantic-docs.helpmanual.io)
- ✅ [SQLAlchemy](https://www.sqlalchemy.org/)

And

- ✅ [The 12-Factor App](https://12factor.net)

**Code quality tools:**

- ✅ [ruff](https://github.com/astral-sh/ruff)
- ✅ [mypy](https://github.com/python/mypy)
- ✅ [pytest](https://github.com/pytest-dev/pytest)

## Getting Started

### Prerequisites

- [Homebrew](https://brew.sh/) (MacOS)
- [uv](https://docs.astral.sh/uv/)
- [Docker](https://docs.docker.com/get-docker/)

On MacOS:
```bash
brew install uv
```

On other plaftorms, follow the [uv install instructions](https://docs.astral.sh/uv/getting-started/installation/)

### Installing Dependencies

uv is used as a default dependencies and python manager.

#### Install Python

uv can automatically install the python version defined in `.python-version`.  It will use this version when
performing any python operations.

```bash
uv python install
```

> ⚠️ If the python version changes (ex: from 3.12 to 3.13) this command will need to be rerun

#### Install Project Dependencies
Install all deps from pyproject.toml
```bash
uv sync
```

---

## Initial Project Setup

### Environment Variables

#### Create `.env` file for local development

It is highly recommended to create an `.env` file as far as it is needed for setting up the project with 
local and Docker approaches.

Use `.env.default` as a baseline to get started.  It has valid defaults for local development set:

```bash
cp .env.default .env
```

> 🛑 **NOTE:** Make sure to set `RABBITMQ__USE_SSL=False` for local development

### Environment Variable Reference

| Key                                                          | Default value              | Description                                                                                                                                                                                                                                                                                                                            |
|--------------------------------------------------------------|----------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| DATABASE\_\_HOST                                             | postgres                   | Database Host                                                                                                                                                                                                                                                                                                                          |
| DATABASE\_\_USER                                             | postgres                   | User name for Postgresql Database user                                                                                                                                                                                                                                                                                                 |
| DATABASE\_\_PASSWORD                                         | postgres                   | Password for Postgresql Database user                                                                                                                                                                                                                                                                                                  |
| DATABASE\_\_DB                                               | mindlogger_backend         | Database name                                                                                                                                                                                                                                                                                                                          |
| CORS\_\_ALLOW\_ORIGINS                                       | `*`                        | Represents the list of allowed origins. Set the `Access-Control-Allow-Origin` header. Example: `https://dev.com,http://localohst:8000`                                                                                                                                                                                                 |
| CORS\_\_ALLOW\_ORIGINS\_REGEX                                | -                          | Regex pattern of allowed origins.                                                                                                                                                                                                                                                                                                      |
| CORS\_\_ALLOW\_CREDENTIALS                                   | true                       | Set the `Access-Control-Allow-Credentials` header                                                                                                                                                                                                                                                                                      |
| CORS\_\_ALLOW_METHODS                                        | `*`                        | Set the `Access-Control-Allow-Methods` header                                                                                                                                                                                                                                                                                          |
| CORS\_\_ALLOW_HEADERS                                        | `*`                        | Set the `Access-Control-Allow-Headers` header                                                                                                                                                                                                                                                                                          |
| AUTHENTICATION\_\_ACCESS\_TOKEN\_\_SECRET\_KEY               | secret1                    | Access token's salt                                                                                                                                                                                                                                                                                                                    |
| AUTHENTICATION\_\_REFRESH\_TOKEN\_\_SECRET\_KEY              | secret2                    | Refresh token salt                                                                                                                                                                                                                                                                                                                     |
| AUTHENTICATION\_\_REFRESH\_TOKEN\_\_TRANSITION\_KEY          | transition secret          | Transition refresh token salt. Used for changing refresh token key (generate new key for AUTHENTICATION\_\_REFRESH\_TOKEN\_\_SECRET\_KEY and use previous value as transition token key for accepting previously generated refresh tokens during transition period (see AUTHENTICATION\_\_REFRESH\_TOKEN\_\_TRANSITION\_EXPIRE\_DATE)) |
| AUTHENTICATION\_\_REFRESH\_TOKEN\_\_TRANSITION\_EXPIRE\_DATE | transition expiration date | Transition expiration date. After this date transition token ignored                                                                                                                                                                                                                                                                   |
| AUTHENTICATION\_\_ALGORITHM                                  | HS256                      | The JWT's algorithm                                                                                                                                                                                                                                                                                                                    |
| AUTHENTICATION\_\_ACCESS\_TOKEN\_\_EXPIRATION                | 30                         | Time in minutes after which the access token will stop working                                                                                                                                                                                                                                                                         |
| AUTHENTICATION\_\_REFRESH\_TOKEN\_\_EXPIRATION               | 30                         | Time in minutes after which the refresh token will stop working                                                                                                                                                                                                                                                                        |
| ADMIN_DOMAIN                                                 | -                          | Admin panel domain                                                                                                                                                                                                                                                                                                                     |
| RABBITMQ\_\_URL                                              | rabbitmq                   | Rabbitmq service URL                                                                                                                                                                                                                                                                                                                   |
| RABBITMQ\_\_USE_SSL                                          | True                       | Rabbitmq ssl setting, turn false to local development                                                                                                                                                                                                                                                                                  |
| MAILING\_\_MAIL\_\_USERNAME                                  | mailhog                    | Mail service username                                                                                                                                                                                                                                                                                                                  |
| MAILING\_\_MAIL\_\_PASSWORD                                  | mailhog                    | Mail service password                                                                                                                                                                                                                                                                                                                  |
| MAILING\_\_MAIL\_\_SERVER                                    | mailhog                    | Mail service URL                                                                                                                                                                                                                                                                                                                       |
| MULTI\_INFORMANT\_\_TEMP\_RELATION\_EXPIRY\_SECS             | 86400                      | Expiry (sec) of temporary multi-informant participant take now relation                                                                                                                                                                                                                                                                |
| SECRETS\_\_SECRET\_KEY                                       | -                          | Secret key for data encryption. Use this key only for local development                                                                                                                                                                                                                                                                |
| ONEUP\_HEALTH\_\_CLIENT\_ID                                  | -                          | OneUpHealth API Client ID                                                                                                                                                                                                                                                                                                              |
| ONEUP\_HEALTH\_\_CLIENT\_SECRET                              | -                          | OneUpHealth API Client secret                                                                                                                                                                                                                                                                                                          |
| ONEUP\_HEALTH\_\_MAX\_ERROR\_RETRIES                         | 5                          | Maximum number of times to re-attempt fetching health data from the OneUpHealth API. The overall total number of attempts will be this value plus one                                                                                                                                                                                  |

> ✋You can see that some environment variables have double underscore (`__`) instead of `_`.
>
> As far as `pydantic` supports [nested settings models](https://pydantic-docs.helpmanual.io/usage/settings/) it uses to have cleaner code

---

## Running Supporting Services

The application requires Postgres, Redis and RabbitMQ to be running to start up and serve requests
(as well as run the test suite).

If mail services are needed, mailhog is required and is provided via docker compose.

If uploading media files to applets or answers, then an S3 compatible service is needed.  Minio is provided
via docker compose.

### Run services using Docker

- Run Postgres
  ```bash
  docker-compose up -d postgres
  ```

- Run Redis
  ```bash
  docker-compose up -d redis
  ```

- Run RabbitMQ
  ```bash
  docker-compose up -d rabbitmq
  ```

- Alternatively, you can run all required for the backend:
  ```bash
  docker-compose up postgres redis rabbitmq
  ```

- If you also need mail and S3 storage service
  ```bash
  docker-compose up postgres redis rabbitmq mailhog minio
  ```

> ⚠️ When using Minio more configuration is needed to configure boto3 to talk to the local endpoints
> ```
> AWS_ACCESS_KEY_ID=minioadmin
> AWS_SECRET_ACCESS_KEY=minioadmin
> AWS_ENDPOINT_URL=http://localhost:9000
> AWS_DEFAULT_REGION=us-east-1
> ```

> 🛑 **NOTE:** If the application can't find the `RabbitMQ` service even though it's running normally, change your
`RABBITMQ__URL` to your local ip address instead of `localhost`


### Run services using other means

It is not recommended to run the services natively.  Please use the provided docker setup.

---

## Run the migrations

The database needs to be initialized with tables and starting data via alembic.

```bash
uv run alembic upgrade head
```

---

## Other Local Setup

If you are on a unix type system (Linux, MacOS, WSL, etc) add these entries to `/etc/hosts`.  This will need to be
done with elevated privileges (ex: `sudo vi /etc/hosts`)

```
  #mindlogger
  127.0.0.1 postgres
  127.0.0.1 rabbitmq
  127.0.0.1 redis
  127.0.0.1 mailhog
  ```

---

## Running the app

### Running locally via Docker

To run all services:
```bash
docker-compose up app
```

To run just the application:
Make sure all [required services](#required-services) are properly setup and running

Then start just the app:
  ```bash
  docker-compose up app
  ```

### Running locally via the CLI

```bash
uvicorn src.main:app --proxy-headers --port {PORT} --reload
```

Alternatively, you may run the application using [make](#running-using-makefile):
```bash
make run
```

### Running via Pycharm

---

## Project Makefile

You can use the `Makefile` to work with project (run the application / code quality tools / tests ...)

For local usage:

```bash
# Run the application
make run

# Check the code quality
make cq

# Check and fix code quality
make cqf

# Check tests passing
make test

# Check everything in one hop
make check
```


### Adjust your database for using with tests

⚠️️ Remember that you have to do this only once before the first test.

```base
# Connect to the database with Docker
docker-compose exec postgres psql -U postgres postgres

# Or connect to the database locally
psql -U postgres postgres


# Create user's database
psql# create database test;

# Create arbitrary database
psql# create database test_arbitrary;

# Create user test
psql# create user test;

# Set password for the user
psql# alter user test with password 'test';
```

### Test coverage

To correctly calculate test coverage, you need to run the coverage with the `--concurrency=thread,gevent` parameter:

```bash
coverage run --branch --concurrency=thread,gevent -m pytest
coverage report -m
```

### Running test via docker

(This is how tests are running on CI)

```bash
# Check the code quality
make dcq

# Check tests passing
make dtest

# Check everything in one hop
make dcheck
```


## License
Common Public Attribution License Version 1.0 (CPAL-1.0)

Refer to [LICENSE.md](./LICENSE.MD)


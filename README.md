# Child Mind Institute - Curious Backend API

This repository is used for the backend of the [Curious](https://mindlogger.org/) application stack.

---

## Curious Application Stack

* Curious Admin - [GitHub Repo](https://github.com/ChildMindInstitute/mindlogger-admin)
* Curious Backend - **This Repo**
* Curious Mobile App - [GitHub Repo](https://github.com/ChildMindInstitute/mindlogger-app-refactor)
* Curious Web App - [GitHub Repo](https://github.com/ChildMindInstitute/mindlogger-web-refactor)

---

## Getting Started

### Prerequisites

- [Homebrew](https://brew.sh/) (MacOS)
- [uv](https://docs.astral.sh/uv/)
- [Docker](https://docs.docker.com/get-docker/)

On MacOS:
```bash
brew install uv
```

On other platforms, follow the [uv install instructions](https://docs.astral.sh/uv/getting-started/installation/)

### Optional Dev Tools

- [ipdb](https://github.com/gotcha/ipdb) - iPython debugger
- [PuDB](https://documen.tician.de/pudb/) - console-based visual debugger

With `uv`:

```bash
uvx ipdb
uvx pudb
```

### Managing Python and Project Dependencies

Python versions and dependencies are managed via `uv`. There is no need to use other tooling such as pip,
pyenv, pipenv, etc.


#### Install Python

Install the python version specified in pyproject.toml

```bash
uv python install
```

> ⚠️ If the python version changes (ex: from 3.12 to 3.13) this command will need to be rerun

#### Install Project Dependencies
Install all dependencies from pyproject.toml
```bash
uv sync
```

---

## Initial Project Setup

### Environment Variables

#### Create `.env` file for local development

The backend leverages the python package `dotenv` to read environment variables from a `.env` file
on the file system.  This is useful during local development due to the large number
of necessary environment variables to configure the application.

Use the supplied `.env.default` as a baseline to get started.  It has valid defaults for for nearly
all local development:

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
| DATABASE\_\_POOL\_SIZE                                       | 5                          | Database connection pool size                                                                                                                                                                                                                                                                                                          |
| DATABASE\_\_POOL\_OVERFLOW\_SIZE                             | 10                         | Allowed overflow size of the connection pool                                                                                                                                                                                                                                                                                           |
| DATABASE\_\_POOL\_TIMEOUT                                    | 30                         | The number of seconds to wait for a connection from the pool to become available                                                                                                                                                                                                                                                       |
| CDN\_\_BUCKET                                                | -                          | Bucket name to store applet media files                                                                                                                                                                                                                                                                                                |
| CDN\_\_BUCKET\_ANSWER                                        | -                          | Bucket name to store applet answer files                                                                                                                                                                                                                                                                                               |
| CDN\_\_BUCKET\_OPERATIONS                                    | -                          | Bucket to store intermediate files                                                                                                                                                                                                                                                                                                     |
| CDN\_\_BUCKET\_OVERRIDE                                      | -                          | Bucket name to store applet media files in DR environment                                                                                                                                                                                                                                                                              |
| CDN\_\_BUCKET\_ANSWER\_OVERRIDE                              | -                          | Bucket name to store applet answer files in DR environment                                                                                                                                                                                                                                                                             |
| CDN\_\_BUCKET\_OPERATIONS\_OVERRIDE                          | -                          | Bucket to store intermediate files in DR environment                                                                                                                                                                                                                                                                                   |
| CDN\_\_DOMAIN                                                | -                          | Domain name that fronts the applet media bucket                                                                                                                                                                                                                                                                                        |
| CDN\_\_REGION                                                | -                          | Region that buckets exist in                                                                                                                                                                                                                                                                                                           |
| CORS\_\_ALLOW\_ORIGINS                                       | `*`                        | Represents the list of allowed origins. Set the `Access-Control-Allow-Origin` header. Example: `https://dev.com,http://localhost:8000`                                                                                                                                                                                                 |
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
| AUTHENTICATION\_\_MFA\_TOKEN\_\_SECRET\_KEY                  | secret3                    | MFA token's secret key for signing JWT tokens used during MFA verification                                                                                                                                                                                                                                                             |
| REDIS\_\_MFA\_SESSION\_TTL                                   | 300                        | MFA session time-to-live in seconds (default: 5 minutes)                                                                                                                                                                                                                                                                               |
| REDIS\_\_MFA\_MAX\_ATTEMPTS                                  | 5                          | Maximum TOTP verification attempts per MFA session before lockout                                                                                                                                                                                                                                                                      |
| REDIS\_\_MFA\_GLOBAL\_LOCKOUT\_ATTEMPTS                      | 10                         | Maximum failed MFA attempts across all sessions before global user lockout                                                                                                                                                                                                                                                             |
| REDIS\_\_MFA\_GLOBAL\_LOCKOUT\_TTL                           | 900                        | Global MFA lockout duration in seconds (default: 15 minutes)                                                                                                                                                                                                                                                                           |
| MFA\_\_TOTP\_ENCRYPTION\_KEY                                 | -                          | Base64-encoded Fernet encryption key for encrypting TOTP secrets. Generate using: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`                                                                                                                                                          |
| MFA\_\_TOTP\_ISSUER\_NAME                                    | MindLogger                 | Issuer name shown in authenticator apps (e.g., Google Authenticator)                                                                                                                                                                                                                                                                   |
| MFA\_\_TOTP\_VALID\_WINDOW                                   | 1                          | Number of time steps to check before/after current time for TOTP validation (default allows ±30 seconds)                                                                                                                                                                                                                               |
| MFA\_\_PENDING\_MFA\_EXPIRATION\_SECONDS                     | 600                        | Expiration time in seconds for pending MFA setup (default: 10 minutes)                                                                                                                                                                                                                                                                 |
| MFA\_\_RECOVERY\_CODE\_ENCRYPTION\_KEY                       | -                          | Base64-encoded Fernet encryption key for encrypting recovery codes. Generate using: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`                                                                                                                                                        |
| MFA\_\_RECOVERY\_CODE\_COUNT                                 | 10                         | Number of recovery codes to generate per user                                                                                                                                                                                                                                                                                          |
| MFA\_\_RECOVERY\_CODE\_LENGTH                                | 10                         | Length of random characters in each recovery code (formatted as XXXXX-XXXXX)                                                                                                                                                                                                                                                           |
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

> ✋Note: most environment variables have double underscore (`__`) instead of `_`.
>
> The application leverages `pydantic-settings` which supports [nested settings models](https://pydantic-docs.helpmanual.io/usage/settings/) 
> to effectively namespace related settings.

---

## Running Supporting Services

The application requires Postgres, Redis, and RabbitMQ to be running to start up and serve requests
(as well as running the test suite).

If mail services are needed, mailhog is required and is provided via docker compose.

If uploading media files to applets or answers, then an S3 compatible service is needed. MinIO is provided
via docker compose.

### Start Supporting Services using Docker

To run all services required for the backend:
  ```bash
  docker-compose up postgres redis rabbitmq
  ```

If you also need mail and S3 storage service
  ```bash
  docker-compose up postgres redis rabbitmq mailhog minio
  ```

Also, services can be run individually:

Run Postgres
  ```bash
  docker-compose up -d postgres
  ```

Run Redis
  ```bash
  docker-compose up -d redis
  ```

Run RabbitMQ
  ```bash
  docker-compose up -d rabbitmq
  ```



> 🛑 **NOTE:** If the application can't find the `RabbitMQ` service even though it's running normally, change your
`RABBITMQ__URL` to your local ip address instead of `localhost`


### Run services using other means

It is not recommended to run the services natively.  Please use the provided docker setup.

---

## Run Database Migrations

The database needs to be initialized with tables and starting data via alembic (ensure your postgres container
is running).

```bash
uv run alembic upgrade head
```

---

## Other Local Setup

If you are on a unix type system (Linux, MacOS, WSL, etc) add these entries to `/etc/hosts`.  This will need to be
done with elevated privileges (ex: `sudo vi /etc/hosts`).

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


To run just the application:
Make sure all [required services](#required-services) are properly setup and running

Then start just the app:
  ```bash
  docker-compose up app
  ```

To run all services (useful when developing the other applications in the stack):
```bash
docker-compose up
```

### Running locally via the CLI

```bash
uvicorn src.main:app --proxy-headers --port 8000 --reload
```

Alternatively, you may run the application using [make](#running-using-makefile):
```bash
make run
```

### Running via PyCharm

See the [PyCharm documentation](docs/pycharm.md) for details.

---

## Project Makefile

You can use the `Makefile` to work with project (run the application / code quality tools / tests ...)

For local usage:

```bash
# Run the application
make run

# Run the test suite
make test

# Check the code quality
make cq

# Check and fix code quality
make cqf

# Check everything in one hop
make check
```


### Adjust your database for using with tests

⚠️️ You have to do this only once before running the test suite.

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

## Further Reading

- [Alembic details](docs/alembic.md)
- [Arbitrary Server](docs/arbitrary.md)
- [Curious CLI](docs/cli.md)
- [Database](docs/db.md)
- [Local File Upload/Storage (S3, etc)](docs/storage.md)
- [Git Helpers](docs/git.md)
- [PyCharm Setup](docs/pycharm.md)
- [Security tokens (for deployments)](docs/tokens.md)


## License
Common Public Attribution License Version 1.0 (CPAL-1.0)

Refer to [LICENSE.md](./LICENSE.MD)


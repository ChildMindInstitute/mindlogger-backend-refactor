# ChildMindInstitute - Mindlogger Backend API

This repository is used as a backend for the service MindLogger

## 1. Getting Started / Installation

### 1.1 Create `.env` file for future needs

It is highly recommended to create an `.env` file as far as it is needed for setting up the project with Local and Docker approaches.

```bash
cp .env.default .env
```

### 1.2 Generate secret keys, update .env with values

```bash
openssl rand -hex 32
```

### 1.3 Setup Redis

#### 1.3.1 Locally

✅ [🐧 Linux](https://redis.io/docs/getting-started/installation/install-redis-on-linux/)

✅ [ MacOs](https://redis.io/docs/getting-started/installation/install-redis-on-mac-os/)

#### 1.3.2 Install via Docker

```bash
docker-compose up -d redis
```

### 1.4. Install all project dependencies

Pipenv used as a default dependencies manager

```bash
# Activate your environment
pipenv shell

# Install all deps from Pipfile.lock
# to install venv to current directory use `export PIPENV_VENV_IN_PROJECT=1`
pipenv sync --dev
```

<br/>

> 🛑 **NOTE:** if you don't use `pipenv` for some reason remember that you will not have automatically exported variables from your `.env` file.
>
> 🔗 [Pipenv docs](https://docs.pipenv.org/advanced/#automatic-loading-of-env)

So then you have to do it by your own manually

```bash
# Manual exporting in Unix (like this)
export PYTHONPATH=src/
export BASIC_AUTH__PASSWORD=1234
...
```

...or using a Bash-script

```bash
set -o allexport; source .env; set +o allexport
```

> 🛑 **NOTE:** Please do not forget about environment variables! Now all environment variables for the Postgres Database which runs in docker are already passed to docker-compose.yaml from the .env file.

<br/>

## 2. Usage

### 2.1 Running locally

> 🛑 **NOTE:** Don't forget to set the `PYTHONPATH` environment variable, e.g: export PYTHONPATH=src/

In project we use simplified version of imports: `from apps.application_name import class_name, function_name, module_nanme`.

To do this we must have `src/` folder specified in a **PATH**.

P.S. You don't need to do this additional step if you run application via Docker container 🤫

```bash
uvicorn src.main:app --proxy-headers --port {PORT} --reload
```

### 2.2 Running via docker

```bash
docker-compose up
```

Additional `docker-compose up` flags that might be useful for development

```bash
-d  # Run docker containers as deamons (in background)
--no-recreate  # If containers already exist, don't recreate them
```

#### 2.2.1 Stop the application 🛑

```bash
docker-compose down
```

Additional `docker-compose down` flags that might be useful for development

```bash
-v  # Remove with all volumes
```
### 2.3 Running using Makefile

You can use the `Makefile` to work with project (run the application / code quality tools / tests ...)

For local usage:

```bash
# Run the application
make run

# Check the code quality
make cq

# Check tests passing
make test

# Check everything in one hop
make check
```
### 2.4 Docker development

#### 2.4.1. Build application images

```bash
docker-compose build
```

✅ Make sure that you completed `.env` file. It is using by default in `docker-compose.yaml` file for buildnig.

✅ Check building with `docker images` command. You should see the record with `fastapi_service`.

💡 If you would like to debug the application insode Docker comtainer make sure that you use `COMPOSE_FILE=docker-compose.dev.yaml` in `.env`. It has opened stdin and tty.


## 3 Build With

- ✅ [Python3.10+](https://www.python.org/downloads/release/python-3108/)
- ✅ [Pipenv](https://pipenv.pypa.io/en/latest/)
- ✅ [FastAPI](https://fastapi.tiangolo.com)
- ✅ [Postgresql](https://www.postgresql.org/docs/14/index.html)
- ✅ [Redis](https://redis.io)
- ✅ [Docker](https://docs.docker.com/get-docker/)
- ✅ [Pydantic](https://pydantic-docs.helpmanual.io)
- ✅ [SQLAlchemy](https://www.sqlalchemy.org/)

And

- ✅ [The 12-Factor App](https://12factor.net)

<br/>

**Code quality tools:**

- ✅ [ruff](https://github.com/astral-sh/ruff)
- ✅ [isort](https://github.com/PyCQA/isort)
- ✅ [mypy](https://github.com/python/mypy)
- ✅ [pytest](https://github.com/pytest-dev/pytest)

<br/>

## 4. Environment Variables

| Key                                       | Default value      | Description                                                                                                                            |
| ----------------------------------------- | ------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| DATABASE\_\_HOST                          | postgres           | Database Host                                                                                                                          |
| DATABASE\_\_USER                          | postgres           | User name for Postgresql Database user                                                                                                 |
| DATABASE\_\_PASSWORD                      | postgres           | Password for Postgresql Database user                                                                                                  |
| DATABASE\_\_DB                            | mindlogger_backend | Database name                                                                                                                          |
| CORS\_\_ALLOW_ORIGINS                     | `*`                | Represents the list of allowed origins. Set the `Access-Control-Allow-Origin` header. Example: `https://dev.com,http://localohst:8000` |
| CORS__ALLOW_ORIGINS_REGEX                 | -       | Regex pattern of allowed origins. |
| CORS\_\_ALLOW_CREDENTIALS                 | true               | Set the `Access-Control-Allow-Credentials` header                                                                                      |
| CORS\_\_ALLOW_METHODS                     | `*`                | Set the `Access-Control-Allow-Methods` header                                                                                          |
| CORS\_\_ALLOW_HEADERS                     | `*`                | Set the `Access-Control-Allow-Headers` header                                                                                          |
| AUTHENTICATION**ACCESS_TOKEN**SECRET_KEY  | secret1            | Access token's salt                                                                                                                    |
| AUTHENTICATION**REFRESH_TOKEN**SECRET_KEY | secret2            | Refresh token salt                                                                                                                     |
| AUTHENTICATION\_\_ALGORITHM               | HS256              | The JWT's algorithm                                                                                                                    |
| AUTHENTICATION**ACCESS_TOKEN**EXPIRATION  | 30                 | Time in minutes after which the access token will stop working                                                                         |
| AUTHENTICATION**REFRESH_TOKEN**EXPIRATION | 30                 | Time in minutes after which the refresh token will stop working                                                                        |
| ADMIN_DOMAIN                              | -                  | Admin panel domain                                                                                                                     |
| RABBITMQ__USE_SSL | True                  |  Rabbitmq ssl setting, turn false to local development
##### ✋ Mandatory:

> You can see that some environment variables have double underscore (`__`) instead of `_`.
>
> As far as `pydantic` supports [nested settings models](https://pydantic-docs.helpmanual.io/usage/settings/) it uses to have cleaner code

## 5. Testing

The `pytest` framework is using in order to write unit tests.
Currently postgresql is used as a database for tests with running configurations that are defined in `pyproject.toml`

```toml
DATABASE__HOST=postgres
DATABASE__PORT=5432
DATABASE__PASSWORD=postgres
DATABASE__USER=postgres
DATABASE__DB=test
```

> 🛑 **NOTE:** To run tests localy without changing DATABASE_HOST please add row below to the `/etc/hosts` file (macOS, Linux). It will automatically redirect postgres to the localhost.

```
127.0.0.1       postgres
```

### 5.1. Adjust your database for using with tests

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

### 5.2. Test coverage

To correctly calculate test coverage, you need to run the coverage with the `--concurrency=thread,gevent` parameter:

```bash
coverage run --concurrency=thread,gevent -m pytest
coverage report -m
```

### 5.3. Running test via docker

(This is how tests are running on CI)

```bash
# Check the code quality
make dcq

# Check tests passing
make dtest

# Check everything in one hop
make dcheck
```

## 6. Scripts

### 6.1 Using pre-commit hooks

It is a good practice to use Git hooks to provide better commits.

For increased security during development, install `git-secrets` to scan code for aws keys.

Please use this link for that: https://github.com/awslabs/git-secrets#installing-git-secrets

`.pre-commit-config.yaml` is placed in the root of the repository.

👉 Once you have installed `git-secrets` and `pre-commit` simply run the following command.

```bash
make aws-scan
```

👉 Then all your staged cahnges will be checked via git hooks on every `git commit`

### 6.2 Alembic (migration)

#### 6.2.1 Add a new migrations file 🔨

```bash
alembic revision --autogenerate -m "Add a new field"
```

#### 6.2.2. Upgrade to the latest migration 🔨

```bash
alembic upgrade head
```

#### 6.2.3. Downgrade to the specific one 🔨

```bash
alembic downgrade 0e43c346b90d
```

✅ This hash is taken from the generated file in the migrations folder

#### 6.2.3. Downgrade to the specific one 🔨

```bash
alembic downgrade 0e43c346b90d
```

#### 6.2.4. Removing the migration 🔨

💡 Do not forget that alembic saves the migration version into the database.

```bash
delete from alembic_version;
```

#### 6.2.5. Upgrade arbitrary servers

```bash
alembic -c alembic_arbitrary.ini upgrade head
```

#### 6.2.6. Database relation structure

```mermaid

erDiagram

User_applet_accesses ||--o{ Applets: ""

    User_applet_accesses {
        int id
        datetime created_at
        datetime updated_at
        int user_id FK
        int applet_id FK
        string role
    }

    Users {
        int id
        datetime created_at
        datetime updated_at
        boolean is_deleted
        string email
        string full_name
        string hashed_password
    }

 Users||--o{ Applets : ""

    Applets {
        int id
        datetime created_at
        datetime updated_at
        boolean is_deleted
        string display_name
        jsonb description
        jsonb about
        string image
        string watermark
        int theme_id
        string version
        int creator_id FK
        text report_server_id
        text report_public_key
        jsonb report_recipients
        boolean report_include_user_id
        boolean report_include_case_id
        text report_email_body
    }

Applet_histories }o--|| Users: ""

    Applet_histories {
        int id
        datetime created_at
        datetime updated_at
        boolean is_deleted
        jsonb description
        jsonb about
        string image
        string watermark
        int theme_id
        string version
        int account_id
        text report_server_id
        text report_public_key
        jsonb report_recipients
        boolean report_include_user_id
        boolean report_include_case_id
        text report_email_body
        string id_version
        string display_name
        int creator_id FK
    }

Answers_activity_items }o--|| Applets: ""
Answers_activity_items }o--|| Users: ""
Answers_activity_items }o--|| Activity_item_histories: ""

    Answers_activity_items {
        int id
        datetime created_at
        datetime updated_at
        jsonb answer
        int applet_id FK
        int respondent_id FK
        int activity_item_history_id_version FK
    }

Answers_flow_items }o--|| Applets: ""
Answers_flow_items }o--|| Users: ""
Answers_flow_items ||--o{ Flow_item_histories: ""

    Answers_flow_items {
        int id
        datetime created_at
        datetime updated_at
        jsonb answer
        int applet_id FK
        int respondent_id FK
        int flow_item_history_id_version FK
    }

Activities }o--|| Applets: ""

    Activities {
        int id
        datetime created_at
        datetime updated_at
        boolean is_deleted
        UUID guid
        string name
        jsonb description
        text splash_screen
        text image
        boolean show_all_at_once
        boolean is_skippable
        boolean is_reviewable
        boolean response_is_editable
        int ordering
        int applet_id FK
    }

Activity_histories }o--|| Applets: ""

    Activity_histories {
        int id
        datetime created_at
        datetime updated_at
        boolean is_deleted
        UUID guid
        string name
        jsonb description
        text splash_screen
        text image
        boolean show_all_at_once
        boolean is_skippable
        boolean is_reviewable
        boolean response_is_editable
        int ordering
        int applet_id FK
    }

Activity_item_histories }o--|| Activity_histories: ""

    Activity_item_histories {
        int id
        datetime created_at
        datetime updated_at
        boolean is_deleted
        jsonb question
        string response_type
        jsonb answers
        text color_palette
        int timer
        boolean has_token_value
        boolean is_skippable
        boolean has_alert
        boolean has_score
        boolean is_random
        boolean is_able_to_move_to_previous
        boolean has_text_response
        int ordering
        string id_version
        int activity_id FK
    }

Activity_items }o--|| Activities: ""

    Activity_items {
        int id
        datetime created_at
        datetime updated_at
        jsonb question
        string response_type
        jsonb answers
        text color_palette
        int timer
        boolean has_token_value
        boolean is_skippable
        boolean has_alert
        boolean has_score
        boolean is_random
        boolean is_able_to_move_to_previous
        boolean has_text_response
        int ordering
        int activity_id FK
    }



Flows }o--|| Applets: ""

    Flows {
        int id
        datetime created_at
        datetime updated_at
        boolean is_deleted
        string name
        UUID guid
        jsonb description
        boolean is_single_report
        boolean hide_badge
        int ordering
        int applet_id FK
    }

Flow_items }o--|| Flows: ""
Flow_items }o--|| Activities: ""

    Flow_items {
        int id
        datetime created_at
        datetime updated_at
        boolean is_deleted
        int ordering
        int activity_flow_id FK
        int activity_id FK
    }

Flow_item_histories }o--|| Flow_histories: ""
Flow_item_histories }o--|| Activity_histories: ""

    Flow_item_histories {
        int id
        datetime created_at
        datetime updated_at
        boolean is_deleted
        string id_version
        int activity_flow_id FK
        int activity_id FK
    }

Flow_histories }o--|| Applet_histories: ""

    Flow_histories {
        int id
        datetime created_at
        datetime updated_at
        boolean is_deleted
        string name
        UUID guid
        jsonb description
        boolean is_single_report
        boolean hide_badge
        int ordering
        string id_version
        int applet_id FK
    }


```

## 7. Arbitrary setup

You can connect arbitrary file storage and database by filling special fields in table `user_workspaces`.

### 7.1. PostgreSQL

Add your database connection string into `database_uri`
In next format:

```
postgresql+asyncpg://<username>:<password>@<hostname>:port/database
```

### 7.2. AWS S3 and GCP S3

For AWS S3 bucket next fields are required:
`storage_region`,`storage_bucket`, `storage_access_key`,`storage_secret_key`.

### 7.3. Azure Blob

In case of Azure blob, specify your connection string into field `storage_secret_key`


## 8. License
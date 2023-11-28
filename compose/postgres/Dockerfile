FROM postgres:15.4

RUN apt-get update && apt-get install -y curl

RUN apt-get -y install postgresql-15-cron

COPY ./compose/postgres/init-db /docker-entrypoint-initdb.d

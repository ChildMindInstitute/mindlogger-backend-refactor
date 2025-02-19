FROM 917902836630.dkr.ecr.us-east-1.amazonaws.com/base-image:backend

COPY ./ ./

# Application scripts
COPY --chown=code:code ./compose/fastapi/entrypoint /fastapi-entrypoint
RUN sed -i 's/\r$//g' /fastapi-entrypoint && chmod +x /fastapi-entrypoint

COPY --chown=code:code ./compose/fastapi/start /fastapi-start
RUN sed -i 's/\r$//g' /fastapi-start && chmod +x /fastapi-start

COPY --chown=code:code ./compose/fastapi/migrate /fastapi-migrate
RUN sed -i 's/\r$//g' /fastapi-migrate && chmod +x /fastapi-migrate

# Select internal user
USER code

# Local Object Storage

⚠️ When using MinIO more configuration is needed to configure boto3 to talk to the local endpoints

## Environment Variables

Do not set `CDN__DOMAIN`.  It conflicts with local settings and settings validation will fail  

Ensure the following are set to these values to work with how MinIO is setup in Docker compose file:

```
CDN__ENDPOINT_URL=http://localhost:9000
CDN__SECRET_KEY=miniosecret
CDN__ACCESS_KEY=minioaccess
CDN__STORAGE_ADDRESS=http://localhost:9000/cmi-media-local
```

## Docker Startup

When starting supporting services via docker compose be sure to include the
following services in the startup command:

* `minio`
* `createbuckets`
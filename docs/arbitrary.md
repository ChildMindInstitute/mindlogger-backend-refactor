## Arbitrary setup

You can connect arbitrary file storage and database by filling special fields in table `user_workspaces`.

### PostgreSQL

Add your database connection string into `database_uri`
In next format:

```
postgresql+asyncpg://<username>:<password>@<hostname>:port/database
```

### AWS S3 and GCP S3

For AWS S3 bucket next fields are required:
`storage_region`,`storage_bucket`, `storage_access_key`,`storage_secret_key`.

### Azure Blob

In case of Azure blob, specify your connection string into field `storage_secret_key`
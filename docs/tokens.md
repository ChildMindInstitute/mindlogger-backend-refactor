### Generate secret keys, update .env with values

```bash
openssl rand -hex 32
```

Generate a key and update `.env` values:

* `AUTHENTICATION__ACCESS_TOKEN__SECRET_KEY`
* `AUTHENTICATION__REFRESH_TOKEN__SECRET_KEY`
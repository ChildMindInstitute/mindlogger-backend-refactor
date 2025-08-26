### Alembic (migration)

#### Add a new migrations file 🔨

```bash
alembic revision --autogenerate -m "Add a new field"
```

#### Upgrade to the latest migration 🔨

```bash
alembic upgrade head
```

#### Downgrade to the specific one 🔨

```bash
alembic downgrade 0e43c346b90d
```

✅ This hash is taken from the generated file in the migrations folder

#### Downgrade to the specific one 🔨

```bash
alembic downgrade 0e43c346b90d
```

#### Removing the migration 🔨

💡 Do not forget that alembic saves the migration version into the database.

```bash
delete from alembic_version;
```

#### Upgrade arbitrary servers

```bash
alembic -c alembic_arbitrary.ini upgrade head
```

# Migrations

Schema migrations are managed by **Alembic**. The legacy raw `.sql` files in `pg/` are kept for historical reference only — do not edit or re-run them.

## Layout

```
backend/
  alembic.ini                       # Alembic config; sqlalchemy.url is set in env.py
  alembic/
    env.py                          # reads settings.DATABASE_URL + Base.metadata
    versions/
      a1c99c58f11a_baseline.py      # baseline = current prod schema as of 2026-05-13
  migrations/
    pg/                             # legacy raw SQL (do not run)
    README.md                       # this file
```

## Daily workflow

From `backend/` with the venv active:

| What | Command |
|---|---|
| Apply pending migrations | `alembic upgrade head` (or `make migrate`) |
| Create a new revision after editing models | `alembic revision --autogenerate -m "describe change"` (or `make migration NAME=...`) |
| Roll back one revision | `alembic downgrade -1` (or `make migrate-down`) |
| Show current revision | `alembic current` |
| Show full history | `alembic history` |

### Authoring a new revision

1. Edit a model under `app/models/`.
2. Run `make migration NAME="add foo to bar"` — Alembic diffs your models against the current DB and writes a revision under `alembic/versions/`.
3. **Review the generated file.** Autogenerate misses things: `ENUM` changes, column renames (it sees them as drop+add and loses data), check constraints, indexes on expressions. Edit by hand as needed.
4. `make migrate` to apply locally.
5. Commit the revision file alongside the model change in the same PR.

### Bootstrapping a fresh database

`alembic upgrade head` against an empty database creates every table from scratch via the baseline + any later revisions. This is the path for new dev environments and CI.

## Production / staging adoption

Existing prod and staging databases were created by the legacy `pg/*.sql` files. They already contain the baseline schema. To bring them under Alembic without re-running anything:

```bash
# On the droplet, with prod DATABASE_URL set:
pg_dump $DATABASE_URL > /tmp/prod-backup-$(date +%Y%m%d).sql   # always back up first
alembic stamp head                                              # writes alembic_version row, no DDL
```

After stamping, future schema changes go through `alembic upgrade head` like any other environment.

> **Verify on staging first.** Run `alembic stamp head` on staging, confirm the app boots clean and `SELECT * FROM alembic_version` returns `a1c99c58f11a`, then repeat on prod.

## Why the legacy `pg/` files are kept

They document the *history* of schema changes that led to the current baseline. Useful for context when reviewing git blame or understanding why a column exists. The baseline revision (`a1c99c58f11a_baseline.py`) is the canonical source of truth for the schema as of 2026-05-13.

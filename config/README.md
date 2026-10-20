# Configuration Guide

This directory contains configuration guidelines and instructions for setting up the environment.

## Environment Variables (.env)

The pipeline expects a `.env` file at the project root based on `.env.example`:

```bash
cp .env.example .env
```

### Key Parameters:

| Variable | Description | Default Value |
|---|---|---|
| `DB_HOST` | PostgreSQL Host Address | `localhost` |
| `DB_PORT` | PostgreSQL Service Port | `5432` |
| `DB_USER` | Warehouse Admin User | `postgres` |
| `DB_PASSWORD` | PostgreSQL Password | — |
| `DB_NAME` | Database Name | `olist_dw` |
| `DB_READONLY_USER` | AI Read-Only User | `olist_readonly` |
| `DB_READONLY_PASSWORD` | AI Read-Only Password | — |
| `OPENAI_API_KEY` | (Optional) LLM Provider Key | `None` (triggers offline benchmark mode) |

## Security Best Practices
- Never commit `.env` or raw credential files to version control.
- Ensure `olist_readonly` user is restricted to `SELECT` permissions strictly on `analytics.vw_*` views.

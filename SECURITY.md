# Security Policy (Local Secret Hygiene)

## Baseline

- Keep secrets in local files only; never commit to git.
- Use least-privilege API credentials.
- Rotate credentials immediately if exposed.

## Required local controls

1. `.env` and token files must be private (`chmod 600`).
2. Sensitive files must be ignored in `.gitignore`.
3. Do not print full secrets in logs or screenshots.

## Recommended

- Use account-prefixed env keys for multi-tenant setups.
- Store canonical secrets in a password manager and materialize locally.
- Run periodic secret rotation (30-90 days).

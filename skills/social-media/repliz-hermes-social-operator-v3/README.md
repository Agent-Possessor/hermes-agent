# Repliz Social Operator — Hermes Edition v3

This package is designed for Hermes Agent's skill system. Hermes uses on-demand `SKILL.md` files compatible with the Agent Skills pattern, and bundled/custom skills are loaded from `~/.hermes/skills/`. Supporting references, templates, and scripts may live beside the skill file. citeturn217432search3turn217432search26

## Install

```bash
mkdir -p ~/.hermes/skills/social-media
unzip repliz-hermes-social-operator-v3.zip -d ~/.hermes/skills/social-media
# Result: ~/.hermes/skills/social-media/repliz-hermes-social-operator-v3/
```

Then ensure Hermes can discover the directory according to your Hermes skill configuration. This package intentionally avoids OpenClaw-only metadata and uses Hermes-compatible frontmatter (`name`, `description`, `version`, `author`, `license`, `platforms`, and `metadata.hermes`).

## What changed from the OpenClaw v2 package

- Reworked metadata and install layout for Hermes.
- Added a local SQLite audit ledger with tamper-evident chained hashes.
- Added a signed, payload-bound, short-lived approval token.
- Added content validation before create/update schedule operations.
- Added monitoring checks for schedule failures, token/account problems, comment backlog, and rate-limit symptoms.
- Added Node built-in test coverage with mocked HTTP behavior and edge cases.
- Kept brand profiles out, as requested.

## Security notes

Keep credentials and approval signing secrets in environment variables or a secrets manager. Do not commit `.env`, the audit database, approval token files, or raw API responses containing private data.

## Package map

- `SKILL.md` — primary Hermes instructions.
- `api/` — endpoint, request/response, and error contracts.
- `policies/` — approval, delegation, privacy, and injection defenses.
- `workflows/` — agent runbooks.
- `scripts/` — transport, audit, validator, approval token, monitor.
- `schemas/` — machine-readable action and policy schemas.
- `tests/` — test matrix and executable unit tests.

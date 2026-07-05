# Approval and Delegation

## Single-action approval

The agent drafts a proposal that includes exact endpoint, payload, effect, target IDs, dedupe result, and a payload SHA-256. The human approves that exact proposal. Then issue a short-lived HMAC token:

```bash
node scripts/approval-token.mjs issue \
  --action create_schedule --method POST --path /public/schedule \
  --payload examples/instagram-album.json --ttl-minutes 10
```

The execution helper checks:
- signature integrity;
- expiry;
- method/path match;
- body SHA-256 match;
- one-time use record in SQLite.

## Delegated automation

Only allow a delegated policy that passes `schemas/delegated-policy.schema.json`. It must include account IDs, platforms, allowed actions, max-per-hour and max-per-day, explicit exclusions, escalation, and expiry. Missing fields deny delegation.

Never delegate destructive deletes, account disconnect, OAuth completion, DMs, or cross-account publishing.

# Hermes Runbooks

## Comment reply
1. Discover account via `GET /public/account`.
2. Read queue and exact comment context.
3. Classify: benign/general question vs. sensitive/abusive/financial/legal/personal-data.
4. Draft response; run injection/privacy policy.
5. Create proposal and obtain signed approval.
6. Execute once using `scripts/repliz.mjs`.
7. Verify comment detail/status and write receipt.

## Schedule create or update
1. Discover target account; never guess `accountId`.
2. Produce payload file.
3. Run `validate-content.mjs`.
4. Search near-time schedules for duplicate fingerprint.
5. Propose exact caption, media, time zone, account, and platform.
6. Obtain signed approval token.
7. Execute once, then verify with schedule GET.

## Monitoring
Run `monitor.mjs` read-only on a schedule from your orchestrator. It must not retry or modify schedules automatically. It emits JSON/Markdown alert candidates for: failed schedules, unconnected accounts, stale pending comments, and rate-limit/error events stored in audit.

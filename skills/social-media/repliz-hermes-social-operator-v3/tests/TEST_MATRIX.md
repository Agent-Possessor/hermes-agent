# Test Matrix

Run from package root:

```bash
node --test tests/*.test.mjs
```

Manual integration checks (with a non-production workspace):
- invalid API key → 401, no secret leakage;
- restricted plan → 403 with clear tier message;
- malformed schedule → validator rejects before HTTP;
- 429 GET → bounded retry in orchestration only;
- POST timeout → no automatic re-post; audit `network_uncertain` event;
- same approval token twice → second execution rejected;
- changed caption/media/path/method → approval binding rejection;
- failed schedule → monitor alert candidate;
- pending comment backlog → monitor alert candidate.

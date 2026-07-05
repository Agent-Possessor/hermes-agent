# Request, Response, Pagination, and Errors

## Authentication

```http
Authorization: Basic base64(ACCESS_KEY:SECRET_KEY)
Content-Type: application/json
```

Never print the authorization header, keys, account access tokens, or raw OAuth credentials.

## Common list response

Treat fields as optional unless confirmed in the live response:

```json
{
  "docs": [],
  "totalDocs": 0,
  "limit": 20,
  "totalPages": 0,
  "page": 1,
  "hasNextPage": false,
  "nextPage": null
}
```

Cursor APIs can return `nextToken`; only replay a token returned by the server.

## Example replies

```json
POST /public/comment/{commentId}
{"text":"Thanks for reaching out — please check your inbox."}
```

```json
PUT /public/comment/{commentId}/status
{"status":"resolved"}
```

```json
POST /public/chat/{chatId}/message
{"text":"Thanks. We will help you through the official support channel."}
```

## Status policy

| Code | Handling |
|---:|---|
| 2xx | Verify with a narrow read; record receipt. |
| 400 | Stop and report validation issue, redacting secrets. |
| 401 | Stop; repair/revoke credentials. |
| 403 | Stop; report missing tier/scope. |
| 404 | Verify resource ID/path; comment reads may test legacy fallback. |
| 409 | Read latest state, re-propose. |
| 429 | Respect `Retry-After`; retry reads only. |
| 5xx | Retry idempotent reads only, max 3 attempts with jitter. |

## Retry and idempotency

Never automatically retry `POST`, `PUT`, or `DELETE` after a timeout/connection drop. Instead query relevant state and compare a fingerprint of `{method,path,accountId,resourceId,normalizedText,mediaUrls,scheduleAt}`. If ambiguity remains, escalate to the human.

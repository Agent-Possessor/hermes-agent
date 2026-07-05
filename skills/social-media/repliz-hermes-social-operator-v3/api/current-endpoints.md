# Repliz API Map

Base URL: `https://api.repliz.com`  
Authentication: HTTP Basic Auth using `ACCESS_KEY:SECRET_KEY`.

> Verify the live API documentation before production deployment because endpoint availability and subscription tiers can change. Current documented groups include Account, Comment, Schedule, Chat, Content, Research, Addon, and OAuth account connection. citeturn217432search0

## Read-only endpoints

| Group | Method | Path | Notes |
|---|---|---|---|
| Account | GET | `/public/account` | List connected accounts; page/limit filters. |
| Account | GET | `/public/account/{accountId}` | Detail; redact any token-like fields. |
| Comment | GET | `/public/comment` | Unified queue; prefer this current route. |
| Comment | GET | `/public/comment/{commentId}` | Thread/context before replying. |
| Schedule | GET | `/public/schedule` | Pending/failed schedule list. |
| Schedule | GET | `/public/schedule/{scheduleId}` | Verify post-create/update state. |
| Chat | GET | `/public/chat` | Inbox list. |
| Chat | GET | `/public/chat/{chatId}/message` | Conversation messages. |
| Content | GET | `/public/content` | Published content list. |
| Content | GET | `/public/content/{contentId}/statistic` | Per-content analytics. |

## Mutating endpoints

| Action | Method | Path | Minimum guard |
|---|---|---|---|
| Reply queue comment | POST | `/public/comment/{commentId}` | signed approval + source read |
| Update comment status | PUT | `/public/comment/{commentId}/status` | signed approval |
| Create schedule | POST | `/public/schedule` | signed approval + validation + dedupe |
| Update schedule | PUT | `/public/schedule/{scheduleId}` | signed approval + validation |
| Delete schedule | DELETE | `/public/schedule/{scheduleId}` | explicit destructive approval |
| Retry schedule | POST | `/public/schedule/{scheduleId}/retry` | explicit approval + failure reason |
| Send chat message | POST | `/public/chat/{chatId}/message` | signed approval + source read |
| Mark chat read | PUT | `/public/chat/{chatId}/read` | signed approval |
| Remove account | DELETE | `/public/account/{accountId}` | never delegated |

## Compatibility

An older uploaded OpenClaw skill used `/public/queue`. Use `/public/comment` first. Consider `/public/queue` only for a read-only compatibility probe after a confirmed `404`; never auto-switch during a mutation.

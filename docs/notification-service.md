# Notification service: design, BCC research and migration

This service started as an email sender for TeamShiksha projects. It is now a
channel-agnostic notification service: email today, with the API and
provider layer shaped so SMS, WhatsApp and push can be added without changing
how projects call it.

## 1. How projects use the service today

| Project | Client | Template ids | Provider | Audience sends |
|---|---|---|---|---|
| openlogo | `packages/app/utils/sendEmail.js` | 1, 2 | default (SES) | none |
| rsvp (server) | `apps/server/src/utils/sendEmail.ts` | 4, 5, 6, 9, 13 | default (SES) | event updates, reminders, cancellations: whole attendee list in `bcc` |
| rsvp (api-v1) | `apps/api-v1/packages/email` | 10 (tests) | default | `bcc` audience supported |
| team.shiksha | `packages/server/app/utils/notification.py` | 8–12, 15, 16, 17 | `AUTOSEND` for id 12 | assignment blast: batches of 50 as `recipient` + 49 `bcc` |
| swags.me | `packages/server/internal/module/notify/mail.go` | 13, 15 | `EMAIL_PROVIDER` env (GMAIL) | none |

### Problems found while auditing callers

These are bugs in the calling projects or in how template ids were managed.
They are not fixed by this change, which keeps every existing request working
exactly as before; they need follow-ups in each project.

1. **Template ids collide across projects.** Ids are a single global counter,
   and branches were allocating the same numbers independently:
   - `13` is `swags.me/ForgotPassword` on `prod`, but `rsvp/cancellation` on
     the `rsvp/cancel-event` branch. rsvp calls `id: 13` for event
     cancellations, so today those requests fail validation (they lack `otp`).
   - `14` is `swags.me/Verify` on `prod` but `rsvp/review` on `feat/reviewTemplate`.
   - `15` is `teamshiksha/Interview` on one branch, while swags.me uses `15`
     for its invite email.
   - team.shiksha calls `15`, `16`, `17` and swags.me calls `15`; none exist on
     `prod`, so those emails currently fail.
   This is why new templates use namespaced keys (`rsvp.cancellation`) instead.
2. **rsvp's review email** (`scripts/sendReviewMailScript.ts`) sends `to: [...]`
   (not a field the API has) with `id: 9`, which is the team.shiksha welcome
   email. It never had a valid recipient, and now gets a clear 422.
3. **Timeouts and retries can duplicate emails.** team.shiksha retries any
   failed call three times and uses httpx's 5 s default timeout; rsvp's
   reminder cron re-sends on failure. When a request delivers to some people
   and then fails, a retry resends to everyone. The service now returns
   `207` for partial delivery (a 2xx, so these clients do not retry).

## 2. Why BCC fan-out gets blocked

Every audience email (rsvp reminders/updates/cancellations, team.shiksha
assignment blasts) was sent as one message with the audience in `Bcc`. That
pattern is what mailbox providers and ESPs look for:

- **It looks like bulk mail from a personal mailbox.** Spam filters weigh
  messages whose `To` is the sender or a single address while dozens of
  hidden recipients receive it. Microsoft documents messages being blocked
  well below the hard recipient cap because of heavy Bcc use, and guidance
  from Microsoft support is to split into small batches ([Microsoft Q&A][msqa1],
  [Microsoft Q&A][msqa2]).
- **Hard per-message recipient caps.** SES rejects any message with more than
  50 recipients across To/Cc/Bcc, and the whole send fails, not just the
  extras. The cap cannot be raised ([SES SendEmail][ses-send],
  [SES quotas][ses-quotas]). Gmail caps a message at 500 (2,000 Workspace)
  and counts Bcc like To ([wpmailsmtp][gmail-limits]).
- **One complaint or bounce hits everyone.** A single message to 50 people
  is one delivery: a hard bounce, a spam complaint or a block from one
  recipient's provider is attributed to the whole send, and you cannot tell
  who did not get it.
- **No personalisation and no per-recipient tracking.** Every recipient sees
  the same `To` header (often not them), which itself lowers engagement and
  raises complaints ([Suped][suped-bcc]).
- **Bulk sender rules.** Gmail and Yahoo (since Feb 2024) require SPF, DKIM
  and DMARC for bulk senders, one-click unsubscribe (RFC 8058) on bulk
  marketing mail, and a spam-complaint rate below 0.3% (Google recommends
  under 0.1%) ([Bird][bird-req], [dmarcian][dmarcian]). Bcc blasts push the
  complaint rate up and cannot carry per-recipient unsubscribe links.
- **Autosend specifically** rate-limits API keys to 2 requests/second by
  default and caps new sending domains at 300 emails/day while they warm up
  ([Autosend rate limits][as-rate], [Autosend daily limit][as-daily]). It
  supports `cc`/`bcc` on single sends ([changelog][as-cc]), but its own
  answer for audiences is the bulk endpoint, where each recipient gets an
  individual email (up to 100 recipients per call) ([bulk API][as-bulk]).

**The fix used here:** never put an audience in `Bcc`. Every recipient gets
their own message, addressed `To:` them. With Autosend, identical messages are
grouped into bulk calls, so a 500-person update is 5 API calls instead of 500.
SES sends individually in parallel (8 at a time, under its 14/s default) with
throttling retries.

Still recommended outside this code:

- Confirm SPF, DKIM and DMARC for each sending domain, and keep transactional
  mail (OTPs, tickets) on a different subdomain from announcements so a
  complaint on a blast never delays a password reset.
- For opt-in announcements (team.shiksha assignment blasts), add an
  unsubscribe link/group (Autosend supports `unsubscribeGroupId` on bulk).
- Watch Google Postmaster Tools for the spam rate.

## 3. Architecture

```
POST /v1/notifications ─┐                ┌─ email: SES | AUTOSEND | GMAIL
                        ├─ NotificationService ─ providers ─┤  sms / whatsapp / push: add here
POST /email (legacy) ───┘   (validate, render per         └─
   └─ translates bcc → recipients     recipient, fan out)
```

| Path | Role |
|---|---|
| `app/notifications/models.py` | `Channel`, `Recipient`, `NotificationRequest`, `DeliveryResult` |
| `app/notifications/templates.py` | Single template registry: key, required data, file per channel, legacy id |
| `app/notifications/service.py` | Validates everything, renders, builds one message per recipient, delivers |
| `app/notifications/providers/base.py` | `Provider` contract, retries, rate limiter |
| `app/notifications/providers/email/*` | SES, Autosend, SMTP (Gmail) |
| `app/routers/notifications.py` | `POST /v1/notifications`, `GET /v1/templates` |
| `app/routers/legacy_email.py`, `app/schemas/legacy_email.py` | `POST /email`, unchanged contract |

Behaviour worth knowing:

- **Validate before sending.** Missing template data, a bad address or too
  many recipients is rejected before the first message goes out, so a bad
  request never produces a partial send.
- **Duplicates removed.** The same address twice (or in both `cc` and `bcc`)
  gets one message.
- **Status codes.** `200` all sent; `207` some failed (see the per-recipient
  `results`; do not retry); `404` unknown template; `422` invalid request;
  `502` nothing sent; `503` provider not configured on this deployment.
- **Providers are optional.** A provider is enabled only when its settings
  exist, so a deployment can run with only Autosend.

### Adding a channel (e.g. WhatsApp)

1. Add a message type and a `Provider` implementation under
   `app/notifications/providers/whatsapp/`.
2. Register it in `KNOWN_PROVIDERS` and `_build` in
   `app/notifications/providers/__init__.py`, and add a default.
3. Add a message builder for the channel in `_BUILDERS` in `service.py`.
4. Give templates a field for that channel's content (for WhatsApp, the
   approved template name and parameter order) and return it from
   `TemplateDefinition.channel_source`.

Callers then send the same request with `"channel": "whatsapp"` and phone
numbers as `to`.

## 4. API

### New: `POST /v1/notifications`

```json
{
  "template": "rsvp.update",
  "channel": "email",
  "provider": "AUTOSEND",
  "subject": "Your event starts soon",
  "data": { "eventName": "Meetup", "updatesText": "Starting at 6pm", "updatesLink": "https://..." },
  "recipients": [
    { "to": "asha@example.com" },
    { "to": "bilal@example.com", "data": { "updatesText": "Personal note for Bilal" } },
    { "to": "candidate@example.com", "cc": ["interviewer@example.com"] }
  ],
  "reply_to": "host@example.com"
}
```

`channel` defaults to `email`, `provider` to `DEFAULT_EMAIL_PROVIDER`.
Recipient `data` overrides the shared `data`. Use `cc` only when the copy is
genuinely part of that conversation, never to reach an audience.

Response (`details`): `template`, `channel`, `provider`, `total`, `sent`,
`failed`, `results[]` (`to`, `status`, `message_id`, `error`) and `warnings`.

`GET /v1/templates` lists every key, its channels, required data and legacy id.

### Legacy: `POST /email`

Unchanged request. `bcc` addresses now each receive their own email; the
response still echoes the request in `details` and adds `delivery` with the
same result as above.

## 5. Migrating each project

No project has to change for this release. Recommended follow-ups:

| Project | Change |
|---|---|
| rsvp | Move reminders/updates/cancellations to `/v1/notifications` with attendees as `recipients` (optionally personalise with the attendee's name). Use `provider: "AUTOSEND"` for these so they go through bulk calls. Fix the review script (`to` → recipients, real template). Add `rsvp.cancellation` and `rsvp.review` as keyed templates. |
| team.shiksha | Replace `recipient: batch[0], bcc: batch[1:]` with `recipients: [{to}...]`; the 50-recipient batching is no longer needed (limit is 500). Register the interview templates (`teamshiksha.interview_*`) with keys instead of 15/16/17. |
| swags.me | Register the invite template as `swagsme.invite` and send by key. |
| openlogo | No change needed; move to `/v1/notifications` when convenient. |

[msqa1]: https://learn.microsoft.com/en-us/answers/questions/6053574/email-not-being-sent-when-too-many-emails-in-bcc
[msqa2]: https://learn.microsoft.com/en-us/answers/questions/5929321/whats-the-limit-of-bcc-emails-i-can-send-without-b
[ses-send]: https://docs.aws.amazon.com/ses/latest/APIReference/API_SendEmail.html
[ses-quotas]: https://docs.aws.amazon.com/ses/latest/DeveloperGuide/quotas.html
[gmail-limits]: https://wpmailsmtp.com/gmail-how-many-emails-can-you-send-at-once/
[suped-bcc]: https://www.suped.com/learn/email-deliverability/how-does-using-only-bcc-recipients-affect-email-deliverability
[bird-req]: https://bird.com/explained/deliverability/what-are-the-gmail-and-yahoo-bulk-sender-requirements
[dmarcian]: https://dmarcian.com/yahoo-and-google-dmarc-required/
[as-rate]: https://docs.autosend.com/api-reference/rate-limit.md
[as-daily]: https://docs.autosend.com/wiki/daily-sending-limit.md
[as-cc]: https://docs.autosend.com/changelog/2026/jan/21
[as-bulk]: https://docs.autosend.com/api-reference/mails/bulk

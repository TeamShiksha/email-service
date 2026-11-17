# Development guide

See [docs/notification-service.md](./docs/notification-service.md) for the
architecture, the API and why audiences are never sent with BCC.

## Run and test

```bash
pip install --require-hashes --only-binary :all: -r requirements-dev.lock
python -m pytest -q
pylint app --rcfile=.pylintrc
python run.py
```

## Add a template

1. **Create the file** under `templates/<project>/`, e.g.
   `templates/rsvp/cancellation.html`. Use Jinja2 for variables:
   `{{ eventName }}`. Values are HTML-escaped.

2. **Register it** in `app/notifications/templates.py` by adding a line to
   `_DEFINITIONS`:

   ```python
   _t("rsvp.cancellation", "rsvp/cancellation.html", {"eventName", "updatesLink"}),
   ```

   - The key is `<project>.<name>`. Keys never collide across projects, so
     there is no shared number to coordinate.
   - The set lists variables the template requires; requests missing any of
     them are rejected before anything is sent.
   - Do **not** add a `legacy_id`. Numeric ids are frozen for existing
     callers of `POST /email`.

3. **Send it** with `POST /v1/notifications`:

   ```json
   {
     "template": "rsvp.cancellation",
     "subject": "Meetup has been cancelled",
     "data": { "eventName": "Meetup", "updatesLink": "https://..." },
     "recipients": [{ "to": "a@example.com" }, { "to": "b@example.com" }]
   }
   ```

   Every recipient gets their own email. Put per-person values in the
   recipient's `data`.

`python -m pytest -q` renders every registered template, so a missing file
or broken Jinja fails the build.

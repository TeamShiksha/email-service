"""
Provider behaviour against fake transports.
"""

import base64
import smtplib

import pytest

from app.notifications.errors import ProviderAuthError
from app.notifications.models import Attachment
from app.notifications.providers.email.autosend import AutosendEmailProvider
from app.notifications.providers.email.message import EmailMessage
from app.notifications.providers.email.ses import SESEmailProvider
from app.notifications.providers.email.smtp import SMTPEmailProvider


class FakeResponse:
    def __init__(self, status_code=200, json_body=None):
        self.status_code = status_code
        self._json = json_body if json_body is not None else {}
        self.text = str(self._json)

    def json(self):
        return self._json


class FakeSession:
    def __init__(self, responses=None):
        self.calls = []
        self.responses = list(responses or [])

    def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        if self.responses:
            return self.responses.pop(0)
        if url.endswith("/mails/bulk"):
            n = len(json["recipients"])
            return FakeResponse(
                200,
                {"success": True, "data": {"batchId": "b1", "totalRecipients": n,
                                           "successCount": n, "failedCount": 0}},
            )
        return FakeResponse(200, {"success": True, "data": {"emailId": "e1"}})


def autosend(session):
    provider = AutosendEmailProvider(
        name="AUTOSEND", api_key="k", from_email="no-reply@ts.test", from_name="TS",
        requests_per_second=0,
    )
    provider.session = session
    return provider


def msg(to, html="<p>hi</p>", **kwargs):
    return EmailMessage(to=to, subject="Subject", html=html, **kwargs)


# --- Autosend ---------------------------------------------------------------


def test_autosend_identical_messages_use_bulk_in_chunks_of_100():
    session = FakeSession()
    outcome = autosend(session).send_batch([msg(f"u{i}@x.com") for i in range(150)])
    urls = [c["url"] for c in session.calls]
    assert urls == ["https://api.autosend.com/v1/mails/bulk"] * 2
    assert [len(c["json"]["recipients"]) for c in session.calls] == [100, 50]
    assert all("bcc" not in r for c in session.calls for r in c["json"]["recipients"])
    assert all(r.status == "sent" for r in outcome.results)
    assert len(outcome.results) == 150


def test_autosend_personalised_messages_are_sent_individually():
    session = FakeSession()
    autosend(session).send_batch([msg("a@x.com", "<p>A</p>"), msg("b@x.com", "<p>B</p>")])
    assert [c["url"].rsplit("/", 1)[1] for c in session.calls] == ["send", "send"]
    payload = session.calls[0]["json"]
    assert payload["to"] == {"email": "a@x.com"}
    assert "bcc" not in payload
    assert session.calls[0]["headers"]["Authorization"] == "Bearer k"


def test_autosend_never_batches_handlebars_like_content():
    session = FakeSession()
    autosend(session).send_batch([msg("a@x.com", "<p>{{oops}}</p>"), msg("b@x.com", "<p>{{oops}}</p>")])
    assert all(c["url"].endswith("/mails/send") for c in session.calls)


def test_autosend_attachments_are_base64():
    session = FakeSession()
    attachment = Attachment(filename="e.ics", content=b"BEGIN:VCALENDAR", content_type="text/calendar")
    autosend(session).send(msg("a@x.com", attachments=[attachment], cc=["c@x.com"]))
    payload = session.calls[0]["json"]
    assert payload["attachments"][0]["fileName"] == "e.ics"
    assert base64.b64decode(payload["attachments"][0]["content"]) == b"BEGIN:VCALENDAR"
    assert payload["cc"] == [{"email": "c@x.com"}]


def test_autosend_retries_rate_limits():
    session = FakeSession([FakeResponse(429), FakeResponse(200, {"data": {"emailId": "e9"}})])
    assert autosend(session).send(msg("a@x.com")) == "e9"
    assert len(session.calls) == 2


def test_autosend_does_not_retry_client_errors():
    session = FakeSession([FakeResponse(400), FakeResponse(200)])
    outcome = autosend(session).send_batch([msg("a@x.com")])
    assert outcome.results[0].status == "failed"
    assert len(session.calls) == 1


def test_autosend_auth_failure_stops_the_batch():
    session = FakeSession([FakeResponse(401)])
    with pytest.raises(ProviderAuthError):
        autosend(session).send_batch([msg("a@x.com", "<p>A</p>"), msg("b@x.com", "<p>B</p>")])
    assert len(session.calls) == 1


def test_autosend_reports_bulk_rejections_as_warning():
    session = FakeSession(
        [FakeResponse(200, {"data": {"batchId": "b7", "successCount": 1, "failedCount": 1}})]
    )
    outcome = autosend(session).send_batch([msg("a@x.com"), msg("b@x.com")])
    assert outcome.warnings and "b7" in outcome.warnings[0]


def test_autosend_failed_bulk_marks_its_recipients_failed():
    session = FakeSession([FakeResponse(422)])
    outcome = autosend(session).send_batch([msg("a@x.com"), msg("b@x.com")])
    assert [r.status for r in outcome.results] == ["failed", "failed"]


# --- SES --------------------------------------------------------------------


class FakeSESClient:
    def __init__(self):
        self.calls = []

    def send_email(self, **kwargs):
        self.calls.append(("send_email", kwargs))
        return {"MessageId": "ses-1"}

    def send_raw_email(self, **kwargs):
        self.calls.append(("send_raw_email", kwargs))
        return {"MessageId": "ses-raw"}


def ses():
    provider = SESEmailProvider(
        name="SES", access_key="a", secret_key="b", region="ap-south-1", sender="no-reply@ts.test"
    )
    provider.client = FakeSESClient()
    return provider


def test_ses_sends_one_recipient_per_message_without_bcc():
    provider = ses()
    outcome = provider.send_batch([msg("a@x.com", cc=["c@x.com"]), msg("b@x.com")])
    destinations = sorted(
        (kwargs["Destination"] for _, kwargs in provider.client.calls),
        key=lambda d: d["ToAddresses"][0],
    )
    assert destinations == [
        {"ToAddresses": ["a@x.com"], "CcAddresses": ["c@x.com"]},
        {"ToAddresses": ["b@x.com"]},
    ]
    assert {r.message_id for r in outcome.results} == {"ses-1"}


def test_ses_attachments_use_raw_email():
    provider = ses()
    attachment = Attachment(filename="e.ics", content=b"BEGIN:VCALENDAR", content_type="text/calendar")
    provider.send(msg("a@x.com", attachments=[attachment]))
    method, kwargs = provider.client.calls[0]
    assert method == "send_raw_email"
    assert kwargs["Destinations"] == ["a@x.com"]
    raw = kwargs["RawMessage"]["Data"]
    assert b'filename="e.ics"' in raw and b"text/calendar" in raw and b"Bcc" not in raw


# --- SMTP -------------------------------------------------------------------


class FakeSMTP:
    instances = []

    def __init__(self, host, port, timeout=None):
        self.sent = []
        FakeSMTP.instances.append(self)

    def starttls(self):
        pass

    def login(self, user, password):
        if password == "bad":
            raise smtplib.SMTPAuthenticationError(535, b"bad credentials")

    def send_message(self, mime):
        self.sent.append(mime)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_smtp_batch_reuses_one_connection(monkeypatch):
    FakeSMTP.instances = []
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    provider = SMTPEmailProvider(
        name="GMAIL", host="smtp.test", port=587, username="me@ts.test", password="pw"
    )
    outcome = provider.send_batch([msg("a@x.com"), msg("b@x.com")])
    assert len(FakeSMTP.instances) == 1
    assert [m["To"] for m in FakeSMTP.instances[0].sent] == ["a@x.com", "b@x.com"]
    assert all(m["Bcc"] is None for m in FakeSMTP.instances[0].sent)
    assert all(r.status == "sent" for r in outcome.results)


def test_smtp_bad_login_is_auth_error(monkeypatch):
    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    provider = SMTPEmailProvider(
        name="GMAIL", host="smtp.test", port=587, username="me@ts.test", password="bad"
    )
    with pytest.raises(ProviderAuthError):
        provider.send_batch([msg("a@x.com")])

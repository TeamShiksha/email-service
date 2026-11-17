"""
POST /v1/notifications and GET /v1/templates.
"""

from app.config import config
from tests.conftest import AUTH

UPDATE_DATA = {"eventName": "Meetup", "updatesText": "Starts soon", "updatesLink": "https://x"}


def send(client, payload):
    return client.post("/v1/notifications", json=payload, headers=AUTH)


def test_sends_one_message_per_recipient(client, provider):
    response = send(
        client,
        {
            "template": "rsvp.update",
            "subject": "Update",
            "data": UPDATE_DATA,
            "recipients": [{"to": "a@example.com"}, {"to": "b@example.com"}],
        },
    )
    assert response.status_code == 200, response.text
    details = response.json()["details"]
    assert details["template"] == "rsvp.update"
    assert details["channel"] == "email"
    assert details["sent"] == 2
    assert [m.to for m in provider.sent] == ["a@example.com", "b@example.com"]


def test_per_recipient_data_personalises(client, provider):
    send(
        client,
        {
            "template": "rsvp.invite",
            "subject": "You're invited",
            "data": {"eventName": "Meetup", "inviteText": "Join us", "inviteLink": "https://x"},
            "recipients": [
                {"to": "a@example.com", "data": {"inviteeName": "Asha"}},
                {"to": "b@example.com", "data": {"inviteeName": "Bilal"}},
            ],
        },
    )
    assert "Asha" in provider.sent[0].html and "Bilal" not in provider.sent[0].html
    assert "Bilal" in provider.sent[1].html


def test_missing_data_for_one_recipient_sends_nothing(client, provider):
    response = send(
        client,
        {
            "template": "rsvp.invite",
            "subject": "s",
            "data": {"eventName": "Meetup", "inviteText": "Join us", "inviteLink": "https://x"},
            "recipients": [
                {"to": "a@example.com", "data": {"inviteeName": "Asha"}},
                {"to": "b@example.com"},
            ],
        },
    )
    assert response.status_code == 422
    assert provider.sent == []


def test_subject_is_required_for_email(client, provider):
    response = send(
        client,
        {"template": "rsvp.update", "data": UPDATE_DATA, "recipients": [{"to": "a@example.com"}]},
    )
    assert response.status_code == 422
    assert "subject" in response.json()["message"]


def test_recipient_limit(client, provider, monkeypatch):
    monkeypatch.setattr(config, "MAX_RECIPIENTS_PER_REQUEST", 2)
    response = send(
        client,
        {
            "template": "rsvp.update",
            "subject": "s",
            "data": UPDATE_DATA,
            "recipients": [{"to": f"{i}@example.com"} for i in range(3)],
        },
    )
    assert response.status_code == 422
    assert "limit" in response.json()["message"]
    assert provider.sent == []


def test_channel_without_template_version(client, provider):
    response = send(
        client,
        {
            "template": "rsvp.update",
            "channel": "whatsapp",
            "data": UPDATE_DATA,
            "recipients": [{"to": "+919999999999"}],
        },
    )
    assert response.status_code == 422
    assert "whatsapp" in response.json()["message"]


def test_unknown_template(client, provider):
    response = send(
        client, {"template": "rsvp.nope", "subject": "s", "recipients": [{"to": "a@example.com"}]}
    )
    assert response.status_code == 404


def test_empty_recipients_rejected(client, provider):
    response = send(client, {"template": "rsvp.update", "subject": "s", "recipients": []})
    assert response.status_code == 422


def test_reply_to_is_set(client, provider):
    send(
        client,
        {
            "template": "rsvp.update",
            "subject": "s",
            "data": UPDATE_DATA,
            "reply_to": "host@example.com",
            "recipients": [{"to": "a@example.com"}],
        },
    )
    assert provider.sent[0].reply_to == "host@example.com"


def test_unknown_provider_name(client):
    response = send(
        client,
        {
            "template": "rsvp.update",
            "subject": "s",
            "provider": "PIGEON",
            "data": UPDATE_DATA,
            "recipients": [{"to": "a@example.com"}],
        },
    )
    assert response.status_code == 422
    assert "PIGEON" in response.json()["message"]


def test_unconfigured_provider(client):
    response = send(
        client,
        {
            "template": "rsvp.update",
            "subject": "s",
            "provider": "AUTOSEND",
            "data": UPDATE_DATA,
            "recipients": [{"to": "a@example.com"}],
        },
    )
    assert response.status_code == 503


def test_templates_endpoint(client):
    response = client.get("/v1/templates", headers=AUTH)
    assert response.status_code == 200
    listed = {t["key"]: t for t in response.json()["details"]["templates"]}
    assert listed["rsvp.update"]["legacy_id"] == 6
    assert listed["rsvp.update"]["channels"] == ["email"]
    assert listed["rsvp.update"]["required"] == ["eventName", "updatesLink", "updatesText"]
    assert client.get("/v1/templates").status_code == 401


def test_health_needs_no_auth(client):
    assert client.get("/health").status_code == 200

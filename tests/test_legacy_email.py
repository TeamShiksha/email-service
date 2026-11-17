"""
POST /email must keep working for existing callers, with bcc audiences
delivered as individual messages.
"""

from tests.conftest import AUTH

UPDATE_BODY = {"eventName": "Meetup", "updatesText": "Starts soon", "updatesLink": "https://x"}


def post(client, payload, headers=AUTH):
    return client.post("/email", json=payload, headers=headers)


def test_bcc_audience_becomes_individual_messages(client, provider):
    response = post(
        client,
        {
            "id": 6,
            "subject": "Update",
            "recipient": "host@example.com",
            "bcc": ["a@example.com", "b@example.com", "c@example.com"],
            "body": UPDATE_BODY,
        },
    )
    assert response.status_code == 200, response.text
    assert [m.to for m in provider.sent] == [
        "host@example.com",
        "a@example.com",
        "b@example.com",
        "c@example.com",
    ]
    assert all(m.cc == [] for m in provider.sent)
    assert all(not hasattr(m, "bcc") for m in provider.sent)
    body = response.json()
    assert body["success"] is True
    assert body["details"]["id"] == 6  # request echoed as before
    assert body["delivery"]["sent"] == 4


def test_cc_stays_visible_on_the_main_recipient(client, provider):
    response = post(
        client,
        {
            "id": 10,
            "subject": "Approved",
            "recipient": "user@example.com",
            "cc": ["mentor@example.com"],
            "body": {"user": "U", "project_assigned_to": "P"},
        },
    )
    assert response.status_code == 200
    assert len(provider.sent) == 1
    assert provider.sent[0].to == "user@example.com"
    assert provider.sent[0].cc == ["mentor@example.com"]


def test_cc_only_promotes_first_cc(client, provider):
    post(
        client,
        {
            "id": 11,
            "subject": "s",
            "cc": ["one@example.com", "two@example.com"],
            "body": {"user": "U"},
        },
    )
    assert provider.sent[0].to == "one@example.com"
    assert provider.sent[0].cc == ["two@example.com"]


def test_bcc_only(client, provider):
    response = post(
        client,
        {"id": 6, "subject": "s", "bcc": ["a@example.com", "b@example.com"], "body": UPDATE_BODY},
    )
    assert response.status_code == 200
    assert [m.to for m in provider.sent] == ["a@example.com", "b@example.com"]


def test_nobody_gets_two_copies(client, provider):
    post(
        client,
        {
            "id": 6,
            "subject": "s",
            "recipient": "Host@example.com",
            "cc": ["cc@example.com"],
            "bcc": ["host@example.com", "cc@example.com", "a@example.com", "a@example.com"],
            "body": UPDATE_BODY,
        },
    )
    assert [m.to for m in provider.sent] == ["Host@example.com", "a@example.com"]


def test_self_sends_a_copy_to_the_sender(client, provider):
    post(
        client,
        {"id": 6, "subject": "s", "recipient": "a@example.com", "self": True, "body": UPDATE_BODY},
    )
    assert [m.to for m in provider.sent] == ["a@example.com", "sender@teamshiksha.org"]


def test_requires_a_recipient(client, provider):
    response = post(client, {"id": 6, "subject": "s", "body": UPDATE_BODY})
    assert response.status_code == 422
    assert "recipient" in response.json()["message"]
    assert provider.sent == []


def test_unknown_template_id(client, provider):
    response = post(client, {"id": 99, "subject": "s", "recipient": "a@example.com", "body": {}})
    assert response.status_code == 404
    assert response.json()["success"] is False


def test_missing_template_data_sends_nothing(client, provider):
    response = post(
        client,
        {
            "id": 6,
            "subject": "s",
            "recipient": "a@example.com",
            "bcc": ["b@example.com"],
            "body": {"eventName": "x"},
        },
    )
    assert response.status_code == 422
    assert "updatesLink" in response.json()["message"]
    assert provider.sent == []


def test_invalid_email_is_rejected(client, provider):
    response = post(
        client, {"id": 6, "subject": "s", "recipient": "not-an-email", "body": UPDATE_BODY}
    )
    assert response.status_code == 422
    assert response.json()["success"] is False


def test_provider_is_passed_through(client, provider):
    post(
        client,
        {
            "id": 6,
            "subject": "s",
            "recipient": "a@example.com",
            "body": UPDATE_BODY,
            "provider": "AUTOSEND",
        },
    )
    assert provider.requested["name"] == "AUTOSEND"


def test_provider_defaults_to_configured(client, provider):
    response = post(
        client, {"id": 6, "subject": "s", "recipient": "a@example.com", "body": UPDATE_BODY}
    )
    assert provider.requested["name"] is None  # resolved to DEFAULT_EMAIL_PROVIDER
    # The echo names the provider used, as the old schema's SES default did.
    assert response.json()["details"]["provider"] == "SES"


def test_ticket_attaches_calendar_invite(client, provider):
    body = {
        "name": "N",
        "eventName": "Launch",
        "badgeNumber": "7",
        "ticketLink": "t",
        "googleCalendarLink": "g",
        "iCalendarLink": "data:text/calendar,BEGIN:VCALENDAR%0AEND:VCALENDAR",
        "outlookCalendarLink": "o",
    }
    post(client, {"id": 5, "subject": "Ticket", "recipient": "a@example.com", "body": body})
    assert provider.sent[0].attachments[0].filename == "Launch.ics"


def test_partial_failure_is_207_and_lists_failures(client, provider):
    provider.fail_for = {"b@example.com"}
    response = post(
        client,
        {
            "id": 6,
            "subject": "s",
            "recipient": "a@example.com",
            "bcc": ["b@example.com", "c@example.com"],
            "body": UPDATE_BODY,
        },
    )
    assert response.status_code == 207
    delivery = response.json()["delivery"]
    assert delivery["sent"] == 2 and delivery["failed"] == 1
    failed = [r for r in delivery["results"] if r["status"] == "failed"]
    assert failed[0]["to"] == "b@example.com"


def test_total_failure_is_502(client, provider):
    provider.fail_for = {"a@example.com"}
    response = post(
        client, {"id": 6, "subject": "s", "recipient": "a@example.com", "body": UPDATE_BODY}
    )
    assert response.status_code == 502
    assert response.json()["success"] is False


def test_auth(client, provider):
    payload = {"id": 6, "subject": "s", "recipient": "a@example.com", "body": UPDATE_BODY}
    assert post(client, payload, headers={}).status_code == 401
    assert post(client, payload, headers={"Authorization": "wrong"}).status_code == 401
    assert (
        post(client, payload, headers={"Authorization": "Bearer test-secret"}).status_code == 200
    )

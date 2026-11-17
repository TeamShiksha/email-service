"""
Template registry checks.
"""

import pytest

from app.notifications import templates
from app.notifications.errors import InvalidRequestError, TemplateNotFoundError
from app.notifications.models import Channel

# The numeric ids existing callers send to POST /email. These must never
# change meaning.
FROZEN_LEGACY_IDS = {
    1: "openlogo/ForgotPassword.html",
    2: "openlogo/Verify.html",
    3: "openlogo/Respond.html",
    4: "rsvp/Verify.html",
    5: "rsvp/ticket.html",
    6: "rsvp/update.html",
    7: "rsvp/invite.html",
    8: "teamshiksha/ForgotPassword.html",
    9: "teamshiksha/Welcome.html",
    10: "teamshiksha/RequestSuccess.html",
    11: "teamshiksha/RequestFail.html",
    12: "teamshiksha/Assignment.html",
    13: "swags.me/ForgotPassword.html",
    14: "swags.me/Verify.html",
}


def test_legacy_ids_are_unchanged():
    actual = {i: templates.get_template_by_legacy_id(i).email for i in FROZEN_LEGACY_IDS}
    assert actual == FROZEN_LEGACY_IDS


@pytest.mark.parametrize("definition", templates.TEMPLATES.values(), ids=lambda d: d.key)
def test_every_template_renders(definition):
    data = {key: f"value-{key}" for key in definition.required}
    html = templates.render(definition, Channel.EMAIL, data)
    assert "<" in html


def test_keys_are_namespaced():
    for key in templates.TEMPLATES:
        project, _, name = key.partition(".")
        assert project and name, key


def test_unknown_lookups():
    with pytest.raises(TemplateNotFoundError):
        templates.get_template("nope.nothing")
    with pytest.raises(TemplateNotFoundError):
        templates.get_template_by_legacy_id(999)


def test_missing_required_data_lists_keys():
    definition = templates.get_template("rsvp.update")
    with pytest.raises(InvalidRequestError) as error:
        templates.check_required(definition, {"eventName": "x"})
    assert "updatesLink" in str(error.value) and "updatesText" in str(error.value)


def test_html_is_escaped():
    definition = templates.get_template("rsvp.update")
    html = templates.render(
        definition,
        Channel.EMAIL,
        {"eventName": "<script>x</script>", "updatesText": "t", "updatesLink": "l"},
    )
    assert "<script>x</script>" not in html
    assert "&lt;script&gt;" in html


def test_ics_attachment_from_data_url():
    definition = templates.get_template("rsvp.ticket")
    ics = "BEGIN:VCALENDAR\nEND:VCALENDAR"
    attachments = definition.attachments(
        {"iCalendarLink": "data:text/calendar;charset=utf-8," + ics, "eventName": "Py/Con 2026!"}
    )
    assert len(attachments) == 1
    assert attachments[0].filename == "PyCon 2026.ics"
    assert attachments[0].content == ics.encode()
    assert attachments[0].content_type == "text/calendar"


def test_ics_attachment_ignores_plain_links():
    definition = templates.get_template("rsvp.ticket")
    assert definition.attachments({"iCalendarLink": "https://example.com/x.ics"}) == []

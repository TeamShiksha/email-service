"""
Template registry and rendering.

Every template is registered once here with:
  - a namespaced key (`<project>.<name>`) that callers use,
  - the variables it needs,
  - the file to render for each channel it supports,
  - optionally the numeric id older callers of POST /email still send.

Namespaced keys replace the old global integer ids, which different
projects had started to reuse for different templates.
"""

import base64
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, FrozenSet, List, Mapping, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.notifications.errors import InvalidRequestError, TemplateNotFoundError
from app.notifications.models import Attachment, Channel

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"

AttachmentBuilder = Callable[[Mapping[str, Any]], List[Attachment]]


@dataclass(frozen=True)
class TemplateDefinition:
    """
    A notification template.

    email: Path of the HTML file under `templates/`.
    attachments: Builds attachments from the template data, if any.

    To support another channel later, add a field for its content (for
    example `sms: "rsvp/update.sms.txt"` or a WhatsApp approved-template
    name) and teach `channel_source` about it.
    """

    key: str
    required: FrozenSet[str] = frozenset()
    email: Optional[str] = None
    default_subject: Optional[str] = None
    legacy_id: Optional[int] = None
    attachments: Optional[AttachmentBuilder] = None

    def channel_source(self, channel: Channel) -> Optional[str]:
        """The template file for a channel, or None if not supported."""
        if channel == Channel.EMAIL:
            return self.email
        return None

    @property
    def channels(self) -> List[Channel]:
        """Channels this template can be sent on."""
        return [c for c in Channel if self.channel_source(c)]


def _decode_ics_data_url(data_url: str) -> Optional[str]:
    """
    Decodes `data:text/calendar;...,BEGIN:VCALENDAR...` into ICS text.
    Returns None for anything that is not an ICS data URL.
    """
    if not data_url or not data_url.startswith("data:") or "," not in data_url:
        return None
    header, data = data_url.split(",", 1)
    try:
        if "base64" in header:
            decoded = base64.b64decode(data).decode("utf-8")
        else:
            decoded = urllib.parse.unquote(data)
    except (ValueError, UnicodeDecodeError):
        return None
    return decoded if decoded.strip().startswith("BEGIN:VCALENDAR") else None


def ics_attachment(link_key: str, name_key: str) -> AttachmentBuilder:
    """
    Attaches the calendar invite found in `data[link_key]` as an .ics file
    named after `data[name_key]`. Mail clients do not open data: URLs in
    links, so the invite has to travel as an attachment.
    """

    def build(data: Mapping[str, Any]) -> List[Attachment]:
        ics = _decode_ics_data_url(str(data.get(link_key, "")))
        if not ics:
            return []
        name = str(data.get(name_key) or "event")
        safe = "".join(c for c in name if c.isalnum() or c in " -_").strip()[:50]
        return [
            Attachment(
                filename=f"{safe or 'event'}.ics",
                content=ics.encode("utf-8"),
                content_type="text/calendar",
            )
        ]

    return build


def _t(key: str, email: str, required=(), legacy_id=None, **kwargs) -> TemplateDefinition:
    return TemplateDefinition(
        key=key, email=email, required=frozenset(required), legacy_id=legacy_id, **kwargs
    )


_DEFINITIONS = [
    # openlogo
    _t("openlogo.forgot_password", "openlogo/ForgotPassword.html", {"url"}, 1),
    _t("openlogo.verify", "openlogo/Verify.html", {"url"}, 2),
    _t("openlogo.respond", "openlogo/Respond.html", {"query", "response"}, 3),
    # rsvp
    _t("rsvp.verify", "rsvp/Verify.html", {"email", "magicLink"}, 4),
    _t(
        "rsvp.ticket",
        "rsvp/ticket.html",
        {
            "name",
            "eventName",
            "badgeNumber",
            "ticketLink",
            "googleCalendarLink",
            "iCalendarLink",
            "outlookCalendarLink",
        },
        5,
        attachments=ics_attachment("iCalendarLink", "eventName"),
    ),
    _t("rsvp.update", "rsvp/update.html", {"eventName", "updatesText", "updatesLink"}, 6),
    _t(
        "rsvp.invite",
        "rsvp/invite.html",
        {"inviteeName", "eventName", "inviteText", "inviteLink"},
        7,
    ),
    # team.shiksha
    _t("teamshiksha.forgot_password", "teamshiksha/ForgotPassword.html", {"url", "email"}, 8),
    _t("teamshiksha.welcome", "teamshiksha/Welcome.html", (), 9),
    _t(
        "teamshiksha.request_success",
        "teamshiksha/RequestSuccess.html",
        {"user", "project_assigned_to"},
        10,
    ),
    _t("teamshiksha.request_fail", "teamshiksha/RequestFail.html", {"user"}, 11),
    _t(
        "teamshiksha.assignment",
        "teamshiksha/Assignment.html",
        {"assignment_title", "assignment_description", "deadline"},
        12,
    ),
    # swags.me
    _t("swagsme.forgot_password", "swags.me/ForgotPassword.html", {"otp", "email"}, 13),
    _t("swagsme.verify", "swags.me/Verify.html", {"email", "magicLink"}, 14),
]

TEMPLATES: Dict[str, TemplateDefinition] = {d.key: d for d in _DEFINITIONS}

# Frozen: numeric ids exist only for callers of the legacy POST /email
# endpoint. New templates get a key and no legacy_id.
LEGACY_IDS: Dict[int, str] = {d.legacy_id: d.key for d in _DEFINITIONS if d.legacy_id}

if len(TEMPLATES) != len(_DEFINITIONS):
    raise RuntimeError("Duplicate template key in the registry.")
if len(LEGACY_IDS) != sum(1 for d in _DEFINITIONS if d.legacy_id):
    raise RuntimeError("Duplicate legacy template id in the registry.")


_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "htm", "xml"]),
)


def get_template(key: str) -> TemplateDefinition:
    """Looks up a template by key."""
    definition = TEMPLATES.get(key)
    if definition is None:
        raise TemplateNotFoundError(f"Unknown template '{key}'.")
    return definition


def get_template_by_legacy_id(legacy_id: int) -> TemplateDefinition:
    """Looks up a template by the numeric id used by POST /email."""
    key = LEGACY_IDS.get(legacy_id)
    if key is None:
        raise TemplateNotFoundError(f"Unknown template id {legacy_id}.")
    return TEMPLATES[key]


def check_required(definition: TemplateDefinition, data: Mapping[str, Any]) -> None:
    """Raises if a variable the template needs is missing."""
    missing = sorted(definition.required - data.keys())
    if missing:
        raise InvalidRequestError(
            f"Template '{definition.key}' is missing required data: {', '.join(missing)}"
        )


def render(definition: TemplateDefinition, channel: Channel, data: Mapping[str, Any]) -> str:
    """Renders the template for a channel."""
    source = definition.channel_source(channel)
    if source is None:
        raise InvalidRequestError(
            f"Template '{definition.key}' has no {channel.value} version."
        )
    return _env.get_template(source).render(**data)

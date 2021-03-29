"""DutyCalls platform for notify component."""
from __future__ import annotations

import logging
from typing import Any, TypedDict

from dutycalls import Client
from dutycalls.errors import DutyCallsAuthError, DutyCallsRequestError
import voluptuous as vol

from homeassistant.components.notify import (
    ATTR_DATA,
    ATTR_TARGET,
    ATTR_TITLE,
    PLATFORM_SCHEMA,
    BaseNotificationService,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)

_LOGGER = logging.getLogger(__name__)

ATTR_DATE_TIME = "date_time"
ATTR_SEVERITY = "severity"
ATTR_SENDER = "sender"
ATTR_LINK = "link"
ATTR_IDENTIFIER = "identifier"

CONF_DEFAULT_CHANNEL = "default_channel"

DATA_TEXT_ONLY_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_DATE_TIME): int,
        vol.Optional(ATTR_SEVERITY): cv.string,
        vol.Optional(ATTR_SENDER): cv.string,
        vol.Optional(ATTR_LINK): cv.url,
        vol.Optional(ATTR_IDENTIFIER): cv.string,
    }
)

DATA_SCHEMA = vol.All(cv.ensure_list, [vol.Any(DATA_TEXT_ONLY_SCHEMA)])

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_DEFAULT_CHANNEL): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)


class TicketT(TypedDict, total=False):
    """Type for ticket data."""

    title: str  # Required key
    body: str  # Required key
    dateTime: int  # Optional key
    severity: float  # Optional key
    sender: str  # Optional key
    link: str  # Optional key
    identifier: str  # Optional key


async def async_get_service(
    hass: HomeAssistantType,
    config: ConfigType,
    discovery_info: DiscoveryInfoType | None = None,
) -> DutyCallsNotificationService | None:
    """Set up the DutyCalls notification service."""

    try:
        client = Client(login=config[CONF_USERNAME], password=config[CONF_PASSWORD])
        return DutyCallsNotificationService(hass, config[CONF_DEFAULT_CHANNEL], client)
    except RuntimeError as err:
        _LOGGER.exception("Error in creating a new DutyCalls ticket: %s", err)
        return None


class DutyCallsNotificationService(BaseNotificationService):
    """Implement the notification service for DutyCalls."""

    def __init__(
        self, hass: HomeAssistantType, default_channel: str, client: Client
    ) -> None:
        """Initialize."""
        self._hass = hass
        self._default_channel = default_channel
        self._client = client

    async def _async_post_ticket(
        self,
        targets: list[str],
        title: str,
        body: str,
        date_time: str | None,
        severity: str | None,
        sender: str | None,
        link: str | None,
        identifier: str | None,
    ) -> None:
        """Post a ticket to DutyCalls."""

        ticket_dict: TicketT = {"title": title, "body": body}

        if date_time:
            ticket_dict["dateTime"] = date_time

        if severity:
            ticket_dict["severity"] = severity

        if sender:
            ticket_dict["sender"] = sender

        if link:
            ticket_dict["link"] = link

        if identifier:
            ticket_dict["identifier"] = identifier

        try:
            await self._client.new_ticket(ticket_dict, *targets)
        except DutyCallsAuthError as err:
            _LOGGER.error("Error while posting the ticket: %r", err)
        except DutyCallsRequestError as err:
            _LOGGER.error("Error while posting the ticket: %r", err)

    async def async_send_message(self, message: str, **kwargs: Any) -> None:
        """Read the content of the message and post a ticket with this content to DutyCalls."""
        data = kwargs.get(ATTR_DATA) or {}

        try:
            DATA_SCHEMA(data)
        except vol.Invalid as err:
            _LOGGER.error("Invalid message data: %s", err)
            data = {}

        targets = kwargs.get(ATTR_TARGET, [self._default_channel])
        title = kwargs.get(ATTR_TITLE)
        body = message
        date_time = data.get(ATTR_DATE_TIME)
        severity = data.get(ATTR_SEVERITY)
        sender = data.get(ATTR_SENDER)
        link = data.get(ATTR_LINK)
        identifier = data.get(ATTR_IDENTIFIER)

        return await self._async_post_ticket(
            targets, title, body, date_time, severity, sender, link, identifier
        )

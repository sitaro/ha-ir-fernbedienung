"""Remote-Entität: remote.send_command mit Tastennamen."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Any

from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_NUM_REPEATS,
    DEFAULT_DELAY_SECS,
    RemoteEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_TASTE_NAME, CONF_TASTEN
from .entity import FernbedienungEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Remote-Entität anlegen."""
    async_add_entities([Fernbedienung(entry)])


class Fernbedienung(FernbedienungEntity, RemoteEntity):
    """Ganze Fernbedienung; Befehle = Tastennamen."""

    _attr_name = None
    _attr_icon = "mdi:remote-tv"
    _attr_assumed_state = True
    _attr_is_on = True

    def __init__(self, entry: ConfigEntry) -> None:
        super().__init__(entry, "fernbedienung")
        self._tasten: dict = entry.options.get(CONF_TASTEN, {})
        self._attr_extra_state_attributes = {
            "tasten": sorted(t[CONF_TASTE_NAME] for t in self._tasten.values())
        }

    def _finde(self, name: str) -> dict:
        for tid, t in self._tasten.items():
            if name in (tid, t[CONF_TASTE_NAME]) or name.casefold() == t[CONF_TASTE_NAME].casefold():
                return t
        raise HomeAssistantError(f"Unbekannte Taste: {name}")

    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Tasten nacheinander senden."""
        wiederholungen = int(kwargs.get(ATTR_NUM_REPEATS) or 1)
        pause = float(kwargs.get(ATTR_DELAY_SECS) or DEFAULT_DELAY_SECS)
        tasten = [self._finde(c) for c in command]
        for n in range(wiederholungen):
            for i, t in enumerate(tasten):
                await self._sende_taste(t)
                if pause and (i < len(tasten) - 1 or n < wiederholungen - 1):
                    await asyncio.sleep(pause)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Keine Wirkung (IR hat keinen Zustand)."""

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Keine Wirkung (IR hat keinen Zustand)."""

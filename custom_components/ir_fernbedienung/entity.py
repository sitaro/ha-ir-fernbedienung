"""Gemeinsame Basis für Entitäten der IR-Fernbedienung."""

from __future__ import annotations

from homeassistant.components.infrared import InfraredEmitterConsumerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

from .command import RohBefehl
from .const import CONF_SENDER, CONF_TIMINGS, CONF_TRAEGER, DOMAIN, STANDARD_TRAEGER


class FernbedienungEntity(InfraredEmitterConsumerEntity):
    """Basis: Geräteinfo + Senden über den gewählten IR-Sender."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, unique_suffix: str) -> None:
        self._entry = entry
        self._infrared_emitter_entity_id = entry.data[CONF_SENDER]
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="IR-Fernbedienung",
            model="Angelernte Fernbedienung",
        )

    async def _sende_taste(self, taste: dict, wiederholungen: int = 0) -> None:
        await self._send_command(
            RohBefehl(
                taste[CONF_TIMINGS],
                int(taste.get(CONF_TRAEGER) or STANDARD_TRAEGER),
                wiederholungen,
            )
        )

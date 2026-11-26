"""Ein Knopf pro angelernter Taste."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_TASTE_NAME, CONF_TASTEN
from .entity import FernbedienungEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Knöpfe für alle Tasten anlegen."""
    tasten: dict = entry.options.get(CONF_TASTEN, {})
    # Knöpfe gelöschter Tasten aus der Entitäten-Registry entfernen
    reg = er.async_get(hass)
    gueltig = {f"{entry.entry_id}_taste_{tid}" for tid in tasten}
    for eintrag in er.async_entries_for_config_entry(reg, entry.entry_id):
        if eintrag.domain == "button" and eintrag.unique_id not in gueltig:
            reg.async_remove(eintrag.entity_id)
    async_add_entities(TasteButton(entry, tid, t) for tid, t in tasten.items())


class TasteButton(FernbedienungEntity, ButtonEntity):
    """Sendet eine angelernte Taste."""

    _attr_icon = "mdi:remote"

    def __init__(self, entry: ConfigEntry, taste_id: str, taste: dict) -> None:
        super().__init__(entry, f"taste_{taste_id}")
        self._taste = taste
        self._attr_name = taste[CONF_TASTE_NAME]

    async def async_press(self) -> None:
        """Taste senden."""
        await self._sende_taste(self._taste)

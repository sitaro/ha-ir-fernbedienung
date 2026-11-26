"""Einrichtung und Anlernen von Tasten."""

from __future__ import annotations

import asyncio
from typing import Any
import uuid

try:  # HA ≥ 2026 nutzt probatio (voluptuous-kompatibel)
    import probatio as vol
except ImportError:  # pragma: no cover
    import voluptuous as vol

from homeassistant.components.infrared import (
    DOMAIN as INFRARED_DOMAIN,
    InfraredReceivedSignal,
    async_get_emitters,
    async_get_receivers,
    async_subscribe_receiver,
)
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_EMPFAENGER,
    CONF_SENDER,
    CONF_TASTE_NAME,
    CONF_TASTEN,
    CONF_TIMINGS,
    CONF_TRAEGER,
    DOMAIN,
    LERN_TIMEOUT,
    MIN_TIMINGS,
    STANDARD_TRAEGER,
)
from .command import nec_timings


class IrFernbedienungConfigFlow(ConfigFlow, domain=DOMAIN):
    """Neue Fernbedienung anlegen."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Name, Sender und Empfänger wählen."""
        sender = async_get_emitters(self.hass)
        empfaenger = async_get_receivers(self.hass)
        if not sender:
            return self.async_abort(reason="kein_sender")
        if not empfaenger:
            return self.async_abort(reason="kein_empfaenger")

        if user_input is not None:
            return self.async_create_entry(
                title=user_input["name"],
                data={
                    CONF_SENDER: user_input[CONF_SENDER],
                    CONF_EMPFAENGER: user_input[CONF_EMPFAENGER],
                },
                options={CONF_TASTEN: {}},
            )

        schema = vol.Schema(
            {
                vol.Required("name"): TextSelector(),
                vol.Required(CONF_SENDER, default=sender[0]): EntitySelector(
                    EntitySelectorConfig(domain=INFRARED_DOMAIN, include_entities=sender)
                ),
                vol.Required(CONF_EMPFAENGER, default=empfaenger[0]): EntitySelector(
                    EntitySelectorConfig(domain=INFRARED_DOMAIN, include_entities=empfaenger)
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Optionen = Tasten verwalten."""
        return TastenOptionsFlow()


class TastenOptionsFlow(OptionsFlow):
    """Tasten anlernen, umbenennen, löschen."""

    def __init__(self) -> None:
        self._name: str = ""
        self._signal: InfraredReceivedSignal | None = None
        self._lern_task: asyncio.Task | None = None
        self._umbenennen_id: str | None = None

    @property
    def _tasten(self) -> dict[str, dict]:
        return dict(self.config_entry.options.get(CONF_TASTEN, {}))

    def _speichern(self, tasten: dict[str, dict]) -> ConfigFlowResult:
        return self.async_create_entry(data={**self.config_entry.options, CONF_TASTEN: tasten})

    def _tasten_auswahl(self, mehrfach: bool) -> SelectSelector:
        return SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(value=tid, label=t[CONF_TASTE_NAME])
                    for tid, t in sorted(self._tasten.items(), key=lambda x: x[1][CONF_TASTE_NAME].casefold())
                ],
                multiple=mehrfach,
                mode=SelectSelectorMode.LIST if mehrfach else SelectSelectorMode.DROPDOWN,
            )
        )

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Menü."""
        optionen = ["anlernen", "code_eingeben"]
        if self._tasten:
            optionen += ["umbenennen", "loeschen"]
        return self.async_show_menu(
            step_id="init",
            menu_options=optionen,
            description_placeholders={"anzahl": str(len(self._tasten))},
        )

    # ---------- Anlernen ----------
    async def async_step_anlernen(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Tastennamen abfragen."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input[CONF_TASTE_NAME].strip()
            if not name:
                errors[CONF_TASTE_NAME] = "name_leer"
            elif any(t[CONF_TASTE_NAME].casefold() == name.casefold() for t in self._tasten.values()):
                errors[CONF_TASTE_NAME] = "name_vergeben"
            else:
                self._name = name
                self._signal = None
                self._lern_task = None
                return await self.async_step_warten()
        return self.async_show_form(
            step_id="anlernen",
            data_schema=vol.Schema({vol.Required(CONF_TASTE_NAME): TextSelector()}),
            errors=errors,
        )

    async def _warte_auf_signal(self) -> None:
        empfaenger = self.config_entry.data[CONF_EMPFAENGER]
        fertig: asyncio.Future[InfraredReceivedSignal] = self.hass.loop.create_future()

        @callback
        def empfangen(signal: InfraredReceivedSignal) -> None:
            if not fertig.done() and len(signal.timings) >= MIN_TIMINGS:
                fertig.set_result(signal)

        abmelden = async_subscribe_receiver(self.hass, empfaenger, empfangen)
        try:
            self._signal = await asyncio.wait_for(fertig, LERN_TIMEOUT)
        except TimeoutError:
            self._signal = None
        finally:
            abmelden()

    async def async_step_warten(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Auf das IR-Signal warten."""
        if self._lern_task is None:
            try:
                # Empfänger prüfen, bevor der Fortschrittsdialog erscheint
                async_subscribe_receiver(self.hass, self.config_entry.data[CONF_EMPFAENGER], lambda s: None)()
            except HomeAssistantError:
                return self.async_abort(reason="empfaenger_fehlt")
            self._lern_task = self.hass.async_create_task(self._warte_auf_signal())
        if not self._lern_task.done():
            return self.async_show_progress(
                step_id="warten",
                progress_action="warten",
                progress_task=self._lern_task,
                description_placeholders={"name": self._name, "sekunden": str(LERN_TIMEOUT)},
            )
        return self.async_show_progress_done(
            next_step_id="gelernt" if self._signal is not None else "kein_signal"
        )

    async def async_step_gelernt(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Taste speichern."""
        assert self._signal is not None
        tasten = self._tasten
        tasten[uuid.uuid4().hex[:8]] = {
            CONF_TASTE_NAME: self._name,
            CONF_TIMINGS: [int(t) for t in self._signal.timings],
            CONF_TRAEGER: int(self._signal.modulation or STANDARD_TRAEGER),
        }
        return self._speichern(tasten)

    async def async_step_kein_signal(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Zeitüberschreitung."""
        return self.async_abort(reason="kein_signal")

    # ---------- Code eingeben ----------
    async def async_step_code_eingeben(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Taste aus bekanntem NEC-Code anlegen (ohne Original-Fernbedienung)."""
        errors: dict[str, str] = {}
        if user_input is not None:
            name = user_input[CONF_TASTE_NAME].strip()
            werte: dict[str, int] = {}
            for feld in ("adresse", "befehl"):
                try:
                    werte[feld] = int(user_input[feld].strip().lower().removeprefix("0x"), 16)
                    if not 0 <= werte[feld] <= 0xFFFF:
                        raise ValueError
                except ValueError:
                    errors[feld] = "code_ungueltig"
            if not name:
                errors[CONF_TASTE_NAME] = "name_leer"
            elif any(t[CONF_TASTE_NAME].casefold() == name.casefold() for t in self._tasten.values()):
                errors[CONF_TASTE_NAME] = "name_vergeben"
            if not errors:
                tasten = self._tasten
                tasten[uuid.uuid4().hex[:8]] = {
                    CONF_TASTE_NAME: name,
                    CONF_TIMINGS: nec_timings(werte["adresse"], werte["befehl"]),
                    CONF_TRAEGER: STANDARD_TRAEGER,
                }
                return self._speichern(tasten)
        return self.async_show_form(
            step_id="code_eingeben",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_TASTE_NAME): TextSelector(),
                        vol.Required("adresse"): TextSelector(),
                        vol.Required("befehl"): TextSelector(),
                    }
                ),
                user_input or {},
            ),
            errors=errors,
        )

    # ---------- Umbenennen ----------
    async def async_step_umbenennen(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Taste wählen und neuen Namen setzen."""
        errors: dict[str, str] = {}
        if user_input is not None:
            tasten = self._tasten
            tid = user_input["taste"]
            name = user_input[CONF_TASTE_NAME].strip()
            if not name:
                errors[CONF_TASTE_NAME] = "name_leer"
            elif any(t[CONF_TASTE_NAME].casefold() == name.casefold() for k, t in tasten.items() if k != tid):
                errors[CONF_TASTE_NAME] = "name_vergeben"
            elif tid in tasten:
                tasten[tid] = {**tasten[tid], CONF_TASTE_NAME: name}
                return self._speichern(tasten)
        return self.async_show_form(
            step_id="umbenennen",
            data_schema=vol.Schema(
                {
                    vol.Required("taste"): self._tasten_auswahl(False),
                    vol.Required(CONF_TASTE_NAME): TextSelector(),
                }
            ),
            errors=errors,
        )

    # ---------- Löschen ----------
    async def async_step_loeschen(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Tasten löschen."""
        if user_input is not None:
            tasten = self._tasten
            for tid in user_input.get("tasten", []):
                tasten.pop(tid, None)
            return self._speichern(tasten)
        return self.async_show_form(
            step_id="loeschen",
            data_schema=vol.Schema({vol.Required("tasten"): self._tasten_auswahl(True)}),
        )

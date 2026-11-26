"""Gespeichertes Rohsignal als IR-Befehl."""

from __future__ import annotations

from homeassistant.components.infrared import InfraredCommand


class RohBefehl(InfraredCommand):
    """IR-Befehl aus angelernten Rohzeiten (µs; positiv = Puls, negativ = Pause)."""

    def __init__(self, timings: list[int], traeger: int, wiederholungen: int = 0) -> None:
        super().__init__(modulation=traeger, repeat_count=wiederholungen)
        self._timings = [int(t) for t in timings]

    def get_raw_timings(self) -> list[int]:
        """Rohzeiten zurückgeben (bei Wiederholungen mehrfach mit Pause)."""
        if self.repeat_count <= 0:
            return list(self._timings)
        out: list[int] = []
        for i in range(self.repeat_count + 1):
            out.extend(self._timings)
            if i < self.repeat_count:
                if out and out[-1] < 0:
                    out[-1] = min(out[-1], -40000)
                else:
                    out.append(-40000)
        return out


def nec_wert(wert: int) -> int:
    """8-Bit-NEC-Wert um das invertierte Byte ergänzen; 16-Bit-Werte unverändert."""
    if wert <= 0xFF:
        return ((~wert & 0xFF) << 8) | wert
    return wert


def nec_timings(adresse: int, befehl: int) -> list[int]:
    """NEC-Rohzeiten (µs) erzeugen.

    adresse/befehl als 8-Bit-Wert (Inverses wird ergänzt) oder 16-Bit-Wert wie
    in ESPHome (z. B. Adresse 0xFF00, Befehl 0xBF40); gesendet wird LSB zuerst.
    """
    daten = nec_wert(adresse) | (nec_wert(befehl) << 16)
    timings = [9000, -4500]
    for bit in range(32):
        timings += [560, -1690 if (daten >> bit) & 1 else -560]
    timings += [560, -10000]
    return timings

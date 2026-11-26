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

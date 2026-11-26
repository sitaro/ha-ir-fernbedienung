"""Konstanten für IR-Fernbedienung."""

DOMAIN = "ir_fernbedienung"

CONF_SENDER = "sender"
CONF_EMPFAENGER = "empfaenger"
CONF_TASTEN = "tasten"
CONF_TASTE_NAME = "name"
CONF_TIMINGS = "timings"
CONF_TRAEGER = "traeger"

STANDARD_TRAEGER = 38000  # Hz, falls der Empfänger keine Trägerfrequenz liefert
MIN_TIMINGS = 10  # kürzere Signale (Rauschen, NEC-Wiederholcodes) ignorieren
LERN_TIMEOUT = 20  # Sekunden

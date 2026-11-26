# IR-Fernbedienung für Home Assistant

Eigene Infrarot-Fernbedienungen **anlernen** und wieder **senden** – mit jedem IR-Empfänger und -Sender, den Home Assistant als `infrared`-Entität kennt (z. B. ESPHome mit `ir_rf_proxy`).

- Anlernen direkt in der HA-Oberfläche: Taste benennen → Taste auf der Fernbedienung drücken → fertig.
- Fernbedienung verloren? Tasten lassen sich auch aus einem bekannten **NEC-Code** (Adresse + Befehl) anlegen.
- Jede Taste wird ein **Knopf** (`button.<fernbedienung>_<taste>`).
- Zusätzlich eine **Remote-Entität** für Skripte: `remote.send_command` mit dem Tastennamen.
- Gespeichert wird das Rohsignal (µs-Zeiten + Trägerfrequenz) – funktioniert also auch mit Protokollen, die HA nicht kennt.

Benötigt Home Assistant **2026.11** oder neuer.

## Installation

**HACS:** *HACS → ⋮ → Benutzerdefinierte Repositories* → `https://github.com/sitaro/ha-ir-fernbedienung`, Typ *Integration* → „IR-Fernbedienung“ installieren → HA neu starten.

**Manuell:** Ordner `custom_components/ir_fernbedienung` nach `/config/custom_components/` kopieren und HA neu starten.

## IR-Hardware (Beispiel ESPHome)

```yaml
remote_transmitter:
  id: ir_tx
  pin: GPIO26
  carrier_duty_percent: 50%

remote_receiver:
  id: ir_rx
  pin:
    number: GPIO27
    inverted: true
  tolerance: 25%

infrared:
  - platform: ir_rf_proxy
    name: IR-Sender
    remote_transmitter_id: ir_tx
  - platform: ir_rf_proxy
    name: IR-Empfänger
    remote_receiver_id: ir_rx
```

## Benutzung

1. *Einstellungen → Geräte & Dienste → Integration hinzufügen → IR-Fernbedienung*: Name, IR-Sender und IR-Empfänger wählen.
2. Beim Eintrag auf **Konfigurieren** → **Taste anlernen** → Namen eingeben → **Senden** → innerhalb von 20 s die Taste auf der Fernbedienung kurz drücken (auf den Empfänger zielen).
3. Ohne Original-Fernbedienung: **NEC-Code eingeben** → Name, Adresse und Befehl (hex) eingeben. 8-Bit-Werte (z. B. `00` / `40`) werden um das invertierte Byte ergänzt, 16-Bit-Werte wie in ESPHome (`FF00` / `BF40`) bleiben unverändert.
4. Ebenso: **Taste umbenennen**, **Tasten löschen**.

Senden aus Automationen/Skripten:

```yaml
action: button.press
target:
  entity_id: button.stereoanlage_power

# oder mehrere Tasten / Wiederholungen
action: remote.send_command
target:
  entity_id: remote.stereoanlage
data:
  command: ["Lauter", "Lauter", "Lauter"]
  delay_secs: 0.3
```

## Hinweise

- IR kennt keinen Rückkanal – HA weiß nicht, ob das Gerät reagiert hat.
- Klimaanlagen-Fernbedienungen senden oft den kompletten Zustand; dort lernt man am besten jede gewünschte Einstellung als eigene „Taste“.
- Die Infrarot-Schnittstelle von HA/ESPHome ist noch als experimentell gekennzeichnet.

## Lizenz

MIT – siehe [LICENSE](LICENSE).

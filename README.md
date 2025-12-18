# ABRP Telemetry Integration für Home Assistant

Diese Custom Integration sendet Telemetriedaten deines Elektrofahrzeugs an [A Better Route Planner (ABRP)](https://abetterrouteplanner.com/).

## Features

- Automatische Übertragung von Fahrzeugdaten an ABRP
- Konfigurierbares Update-Intervall (Standard: 5 Sekunden)
- Unterstützt alle wichtigen Telemetrie-Parameter
- Optimiert für Mercedes EQA 250 mit mb2020 Integration

## Installation

### HACS (empfohlen)

1. Öffne HACS in Home Assistant
2. Klicke auf "Integrationen"
3. Klicke auf das Drei-Punkte-Menü oben rechts
4. Wähle "Benutzerdefinierte Repositories"
5. Füge die Repository-URL hinzu
6. Installiere "ABRP Telemetry"
7. Starte Home Assistant neu

### Manuelle Installation

1. Kopiere den Ordner `custom_components/abrp_telemetry` in deinen Home Assistant `custom_components` Ordner
2. Starte Home Assistant neu

## Konfiguration

### Voraussetzungen

1. **ABRP API Key**: Kontaktiere contact@iternio.com für einen kostenlosen Telemetry-API-Key
2. **User Token**: Finde deinen Token in der ABRP App unter:
   - Einstellungen → Car Settings → Generic → Show Token
3. **Car Model**: Für Mercedes EQA 250 verwende: `mercedes:eqa:22:67:other`

### Setup

1. Gehe zu Einstellungen → Geräte & Dienste → Integration hinzufügen
2. Suche nach "ABRP Telemetry"
3. Gib deine API-Credentials ein
4. Mappe die Entities deiner mb2020 Integration

## Entity Mapping für Mercedes mb2020

Typische Entity-IDs für die mb2020 Integration:

| Parameter | Beispiel Entity |
|-----------|-----------------|
| SOC (Ladezustand) | `sensor.mercedes_eqa_soc` |
| Geschwindigkeit | `sensor.mercedes_eqa_speed` |
| Breitengrad | `device_tracker.mercedes_eqa` (oder separater Sensor) |
| Längengrad | `device_tracker.mercedes_eqa` (oder separater Sensor) |
| Ladestatus | `binary_sensor.mercedes_eqa_charging` |
| Außentemperatur | `sensor.mercedes_eqa_outside_temp` |
| Kilometerstand | `sensor.mercedes_eqa_odometer` |
| Reichweite | `sensor.mercedes_eqa_range` |

**Hinweis**: Die genauen Entity-Namen können je nach Konfiguration variieren. Prüfe deine Entities unter Entwicklerwerkzeuge → Zustände.

## Parameter-Erklärung

| Parameter | Beschreibung | Einheit |
|-----------|--------------|---------|
| `utc` | UTC Timestamp | Sekunden (Epoch) |
| `soc` | State of Charge | % |
| `speed` | Geschwindigkeit | km/h |
| `lat` / `lon` | GPS Position | Grad |
| `power` | Momentanleistung (+ = Entladen, - = Laden) | kW |
| `is_charging` | Lädt das Fahrzeug | 0/1 |
| `ext_temp` | Außentemperatur | °C |
| `batt_temp` | Batterietemperatur | °C |
| `soh` | State of Health | % |
| `odometer` | Kilometerstand | km |
| `est_battery_range` | Geschätzte Reichweite | km |
| `voltage` | Batteriespannung | V |
| `current` | Batteriestrom | A |

## Update-Intervall

ABRP empfiehlt einen Datenpunkt alle **5 Sekunden** für beste Ergebnisse. Weniger als alle 30 Sekunden wird nicht empfohlen.

Für die individuelle Verbrauchskalibrierung benötigt ABRP mindestens `speed`, `power` und `is_charging` alle 10 Sekunden.

## Troubleshooting

### Logging aktivieren

Füge folgendes zu deiner `configuration.yaml` hinzu:

```yaml
logger:
  default: info
  logs:
    custom_components.abrp_telemetry: debug
```

### Häufige Probleme

1. **Keine Daten in ABRP sichtbar**: Das Backend verarbeitet Daten in 60-Sekunden-Batches. Es kann etwas dauern, bis Daten erscheinen.

2. **SOC nicht verfügbar**: Stelle sicher, dass die mb2020 Integration läuft und Daten liefert.

3. **API-Fehler 401**: Überprüfe deinen API-Key und User Token.

## Lizenz

MIT License

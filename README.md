# ABRP Telemetry Integration für Home Assistant

Diese Custom Integration sendet Telemetriedaten deines Elektrofahrzeugs an [A Better Route Planner (ABRP)](https://abetterrouteplanner.com/).

## Features

- ✅ Automatische Übertragung von Fahrzeugdaten an ABRP
- ✅ Konfigurierbares Update-Intervall (Standard: 5 Sekunden)
- ✅ **Ein/Aus-Schalter** für manuelle Kontrolle und Automationen
- ✅ **Robuste Fehlerbehandlung** mit automatischer Pause bei Problemen
- ✅ Unterstützt alle wichtigen Telemetrie-Parameter
- ✅ Optimiert für Mercedes EQA 250 mit mb2020 Integration

## Schnellübersicht

| Was | Wo |
|-----|-----|
| **Switch Entity** | `switch.abrp_telemetry_upload` |
| **Logs** | Einstellungen → System → Protokolle |
| **Status-Attribute** | Entwicklerwerkzeuge → Zustände → switch.abrp_telemetry_upload |
| **Konfiguration** | Einstellungen → Geräte & Dienste → ABRP Telemetry |

## Funktionsweise

Die Integration arbeitet vollautomatisch:

1. **Nach der Einrichtung** startet automatisch ein Hintergrund-Service
2. **Alle 5 Sekunden** (konfigurierbar) werden die aktuellen Werte deiner konfigurierten Sensoren ausgelesen
3. **Die Daten werden direkt** an die ABRP-API (`api.iternio.com`) gesendet
4. **ABRP verarbeitet** die Daten und zeigt sie in der App/Website an

**Es ist kein manueller Start erforderlich!** Sobald die Integration eingerichtet ist, läuft der Daten-Upload automatisch.

### Fehlerbehandlung

Die Integration ist robust gegen Fehler:

| Situation | Verhalten |
|-----------|-----------|
| Netzwerkfehler | Wartet und versucht es erneut |
| 10 Fehler in Folge | Pausiert automatisch (10s → 20s → 40s → max 5min) |
| Auth-Fehler (401) | Pausiert für 10 Minuten |
| SOC nicht verfügbar | Überspringt Zyklus, warnt im Log |
| Service manuell deaktiviert | Sendet nichts bis wieder aktiviert |

---

## Installation

### HACS (empfohlen)

1. Öffne HACS in Home Assistant
2. Klicke auf "Integrationen"
3. Klicke auf das Drei-Punkte-Menü (⋮) oben rechts
4. Wähle "Benutzerdefinierte Repositories"
5. Füge die Repository-URL hinzu: `https://github.com/Riffer/abrp_telemetry`
6. Kategorie: "Integration"
7. Klicke "Hinzufügen"
8. Suche nach "ABRP Telemetry" und klicke "Herunterladen"
9. **Starte Home Assistant neu**

### Manuelle Installation

1. Lade dieses Repository herunter (Code → Download ZIP)
2. Entpacke die ZIP-Datei
3. Kopiere den Ordner `custom_components/abrp_telemetry` in deinen Home Assistant `config/custom_components/` Ordner
4. Deine Ordnerstruktur sollte so aussehen:
   ```
   config/
   └── custom_components/
       └── abrp_telemetry/
           ├── __init__.py
           ├── config_flow.py
           ├── const.py
           ├── manifest.json
           ├── strings.json
           ├── telemetry.py
           └── translations/
               ├── de.json
               └── en.json
   ```
5. **Starte Home Assistant neu**

---

## Voraussetzungen (WICHTIG!)

### 1. ABRP API Key besorgen

Du benötigst einen **kostenlosen Telemetry API-Key** von Iternio:

1. Schreibe eine E-Mail an: **contact@iternio.com**
2. Betreff: "ABRP Telemetry API Key Request"
3. Inhalt: Beschreibe kurz, dass du die Home Assistant Integration nutzen möchtest
4. Du erhältst den API-Key normalerweise innerhalb von 1-2 Werktagen

### 2. User Token aus ABRP holen

1. Öffne die **ABRP App** auf deinem Smartphone (oder die Webseite)
2. Gehe zu: **Einstellungen** (⚙️)
3. Wähle: **Car Settings** → **Your Car** (oder dein Fahrzeugname)
4. Scrolle nach unten zu: **Generic**
5. Tippe auf: **Show Token**
6. Kopiere den angezeigten Token (langer alphanumerischer String)

### 3. Car Model ID herausfinden

Für die individuelle Verbrauchsberechnung benötigt ABRP das genaue Fahrzeugmodell:

| Fahrzeug | Car Model ID |
|----------|--------------|
| Mercedes EQA 250 (2022+) | `mercedes:eqa:22:67:other` |
| Mercedes EQA 300 4MATIC | `mercedes:eqa:22:67:4matic` |
| Mercedes EQA 350 4MATIC | `mercedes:eqa:22:91:4matic` |

Weitere Modelle findest du in der [ABRP Fahrzeugliste](https://api.iternio.com/1/tlm/get_carmodels_list).

---

## Einrichtung in Home Assistant

### Schritt für Schritt

1. Gehe zu: **Einstellungen** → **Geräte & Dienste**
2. Klicke auf: **+ Integration hinzufügen** (unten rechts)
3. Suche nach: **"ABRP Telemetry"**
4. Fülle das Formular aus:

   | Feld | Beschreibung |
   |------|--------------|
   | **API Key** | Dein Iternio API-Key (von contact@iternio.com) |
   | **User Token** | Dein ABRP User Token (aus der App) |
   | **Car Model** | Dein Fahrzeugmodell (z.B. `mercedes:eqa:22:67:other`) |
   | **Update Interval** | Sekunden zwischen Uploads (5-60, Standard: 5) |
   | **SOC Entity** | **PFLICHT:** Sensor für Ladezustand (%) |
   | **Speed Entity** | Optional: Sensor für Geschwindigkeit (km/h) |
   | **Latitude/Longitude** | Optional: GPS-Position |
   | **Power Entity** | Optional: Momentanleistung (kW) |
   | **Charging Entity** | Optional: Ladestatus (on/off) |
   | ... | Weitere optionale Sensoren |

5. Klicke **"Absenden"**

### Was passiert nach der Einrichtung?

✅ Die Integration startet **sofort automatisch**  
✅ Alle X Sekunden werden Daten an ABRP gesendet  
✅ Du siehst einen Log-Eintrag: "ABRP Telemetry Integration erfolgreich gestartet"  
✅ In ABRP sollten nach ca. 1 Minute deine Live-Daten erscheinen

---

## Entity Mapping für Mercedes mb2020

Typische Entity-IDs für die mb2020 Integration:

| Parameter | Beispiel Entity | Hinweis |
|-----------|-----------------|---------|
| SOC (Ladezustand) | `sensor.mercedes_eqa_soc` | **Pflichtfeld!** |
| Geschwindigkeit | `sensor.mercedes_eqa_speed` | Für Verbrauchsberechnung |
| Position | `device_tracker.mercedes_eqa` | Oder separate lat/lon Sensoren |
| Leistung | `sensor.mercedes_eqa_power` | Für Verbrauchsberechnung |
| Ladestatus | `binary_sensor.mercedes_eqa_charging` | 0/1 oder on/off |
| Außentemperatur | `sensor.mercedes_eqa_outside_temp` | Für Reichweitenprognose |
| Kilometerstand | `sensor.mercedes_eqa_odometer` | Wird in km erwartet |
| Reichweite | `sensor.mercedes_eqa_range` | Geschätzte Reichweite |

**Tipp**: Prüfe deine verfügbaren Entities unter:  
**Entwicklerwerkzeuge** → **Zustände** → Suche nach "mercedes" oder "eqa"

---

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

---

## Ein/Aus-Schalter

Nach der Einrichtung wird automatisch ein Switch erstellt:

**Entity:** `switch.abrp_telemetry_upload`

| Zustand | Bedeutung |
|---------|-----------|
| **ON** | Upload aktiv - Daten werden alle X Sekunden gesendet |
| **OFF** | Upload pausiert - Keine Daten werden gesendet |

### Verwendung in Automationen

**Beispiel 1: Upload nur während der Fahrt**
```yaml
automation:
  - alias: "ABRP nur bei Fahrt"
    trigger:
      - platform: numeric_state
        entity_id: sensor.mercedes_eqa_speed
        above: 0
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.abrp_telemetry_upload

  - alias: "ABRP aus wenn geparkt"
    trigger:
      - platform: numeric_state
        entity_id: sensor.mercedes_eqa_speed
        below: 1
        for:
          minutes: 5
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.abrp_telemetry_upload
```

**Beispiel 2: Upload beim Laden aktivieren**
```yaml
automation:
  - alias: "ABRP beim Laden"
    trigger:
      - platform: state
        entity_id: binary_sensor.mercedes_eqa_charging
        to: "on"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.abrp_telemetry_upload
```

**Beispiel 3: Nachts deaktivieren**
```yaml
automation:
  - alias: "ABRP nachts aus"
    trigger:
      - platform: time
        at: "23:00:00"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.abrp_telemetry_upload

  - alias: "ABRP morgens an"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.abrp_telemetry_upload
```

---

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

1. **Keine Daten in ABRP sichtbar**: 
   - Das ABRP-Backend verarbeitet Daten in 60-Sekunden-Batches
   - Warte mindestens 1-2 Minuten nach der Einrichtung
   - Prüfe die Logs auf Fehler

2. **SOC nicht verfügbar**: 
   - Stelle sicher, dass die mb2020 Integration läuft und Daten liefert
   - Prüfe den Entity-Status unter Entwicklerwerkzeuge → Zustände

3. **API-Fehler 401 (Unauthorized)**: 
   - Überprüfe deinen API-Key (von Iternio erhalten?)
   - Überprüfe deinen User Token (aus der ABRP App kopiert?)

4. **API-Fehler 400 (Bad Request)**: 
   - Prüfe das Car Model Format (z.B. `mercedes:eqa:22:67:other`)
   - Stelle sicher, dass SOC einen gültigen Wert hat

5. **Integration wird nicht gefunden**:
   - Hast du Home Assistant nach der Installation neu gestartet?
   - Liegt der Ordner korrekt unter `config/custom_components/abrp_telemetry/`?

---

## Entwickler-Debugging

Diese Integration enthält eingebaute Debugging-Funktionen für Entwickler.

### Methode 1: Erweiterte Logs (Einfachste Methode)

Füge dies zu deiner `configuration.yaml` hinzu:

```yaml
logger:
  default: info
  logs:
    custom_components.abrp_telemetry: debug
```

Logs findest du unter:
- **Web UI**: Einstellungen → System → Protokolle
- **Docker**: `docker logs homeassistant -f`
- **SSH**: `tail -f /config/home-assistant.log`

### Methode 2: VS Code Remote Debugging

Für vollständiges Step-by-Step Debugging mit Breakpoints:

**1. debugpy auf Home Assistant installieren:**
```bash
# In HA Terminal oder SSH:
pip install debugpy
```

**2. Debug-Modus aktivieren:**

Ändere in `custom_components/abrp_telemetry/const.py`:
```python
DEBUG_MODE = True  # Standardmäßig False
```

**3. Home Assistant neu starten**

**4. VS Code konfigurieren:**

Das Projekt enthält bereits eine `.vscode/launch.json`. Öffne das Projekt in VS Code:
- Drücke `Ctrl+Shift+D` (Run and Debug)
- Wähle **"HA: Remote Attach"**
- Passe den Host an (z.B. `homeassistant.local` oder IP-Adresse)
- Drücke `F5`

**5. Breakpoints setzen:**

Klicke links neben die Zeilennummer in:
- `telemetry.py` - Für Datenübertragung
- `switch.py` - Für Ein/Aus-Schalter
- `config_flow.py` - Für Einrichtungs-Wizard

### Methode 3: Lokale Test-Installation

Für schnelles Testen ohne produktives HA:

```powershell
# Windows PowerShell
python -m venv ha_test
.\ha_test\Scripts\Activate.ps1
pip install homeassistant

# Config-Ordner vorbereiten
mkdir ha_config\custom_components
Copy-Item -Recurse .\custom_components\abrp_telemetry ha_config\custom_components\

# Home Assistant starten
hass -c .\ha_config --debug
```

Öffne dann http://localhost:8123 im Browser.

### Debug-Status prüfen

Der Switch `switch.abrp_telemetry_upload` zeigt als Attribute:
- `is_paused` - Pausiert wegen Fehlern?
- `consecutive_errors` - Fehler in Folge
- `total_sends` - Erfolgreich gesendet
- `total_errors` - Fehler gesamt
- `last_successful_send` - Letzter erfolgreicher Upload (Unix Timestamp)

Diese Werte kannst du unter **Entwicklerwerkzeuge → Zustände** sehen.

---

## Deinstallation

1. Gehe zu: **Einstellungen** → **Geräte & Dienste**
2. Finde die ABRP Telemetry Integration
3. Klicke auf das Drei-Punkte-Menü (⋮) → **Löschen**
4. Optional: Lösche den Ordner `custom_components/abrp_telemetry`

---

## Lizenz

MIT License - Frei zur Nutzung und Modifikation.

---

## Support & Beitrag

- **Probleme melden**: [GitHub Issues](https://github.com/Riffer/abrp_telemetry/issues)
- **Verbesserungen**: Pull Requests sind willkommen!

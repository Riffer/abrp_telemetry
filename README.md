# ABRP Telemetry Integration for Home Assistant

This custom integration sends telemetry data from your electric vehicle to [A Better Route Planner (ABRP)](https://abetterrouteplanner.com/).

## Features

- ✅ Automatic transmission of vehicle data to ABRP
- ✅ **Easy setup wizard** with manufacturer/model selection (no manual ID lookup needed!)
- ✅ Configurable update interval (default: 5 seconds)
- ✅ **On/Off switch** for manual control and automations
- ✅ **Robust error handling** with automatic pause on failures
- ✅ **Options flow** to modify sensor mappings after setup
- ✅ **Live value display** in configuration dialog
- ✅ Supports all important telemetry parameters
- ✅ Works with **any Home Assistant vehicle integration** that provides the required sensor data

## Supported Vehicle Integrations

This integration works with any Home Assistant integration that provides EV telemetry data, including:

| Integration | Vehicles | Notes |
|-------------|----------|-------|
| **Mercedes me 2020 (mb2020)** | All Mercedes EQ models | EQA, EQB, EQC, EQE, EQS, etc. |
| **PSA Car Controller** | Peugeot, Citroën, Opel, DS | e-208, e-2008, Corsa-e, etc. |
| **Hyundai/Kia Connect** | Hyundai, Kia, Genesis | Ioniq 5/6, EV6, GV60, etc. |
| **Tesla Custom Integration** | All Tesla models | Model 3, Y, S, X |
| **BMW Connected Drive** | BMW iX, i4, i7, etc. | |
| **Volkswagen We Connect** | VW ID.3, ID.4, ID.5, etc. | |
| **Renault** | Zoe, Megane E-Tech, etc. | |
| **Any other** | Any EV | As long as SOC sensor is available |

## Quick Reference

| Item | Location |
|------|----------|
| **Switch Entity** | `switch.abrp_telemetry_upload` |
| **Logs** | Settings → System → Logs |
| **Status Attributes** | Developer Tools → States → switch.abrp_telemetry_upload |
| **Configuration** | Settings → Devices & Services → ABRP Telemetry |

## How It Works

The integration runs fully automatically:

1. **After setup**, a background service starts automatically
2. **Every 5 seconds** (configurable), current values from your configured sensors are read
3. **Data is sent directly** to the ABRP API (`api.iternio.com`)
4. **ABRP processes** the data and displays it in the app/website

**No manual start required!** Once configured, the data upload runs automatically.

### Error Handling

The integration is robust against failures:

| Situation | Behavior |
|-----------|----------|
| Network error | Waits and retries |
| 10 consecutive errors | Pauses automatically (10s → 20s → 40s → max 5min) |
| Auth error (401) | Pauses for 10 minutes |
| SOC unavailable | Skips cycle, warns in log |
| Service manually disabled | Sends nothing until re-enabled |

---

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click "Integrations"
3. Click the three-dot menu (⋮) in the top right
4. Select "Custom repositories"
5. Add repository URL: `https://github.com/Riffer/abrp_telemetry`
6. Category: "Integration"
7. Click "Add"
8. Search for "ABRP Telemetry" and click "Download"
9. **Restart Home Assistant**

### Manual Installation

1. Download this repository (Code → Download ZIP)
2. Extract the ZIP file
3. Copy the `custom_components/abrp_telemetry` folder to your Home Assistant `config/custom_components/` folder
4. Your folder structure should look like this:
   ```
   config/
   └── custom_components/
       └── abrp_telemetry/
           ├── __init__.py
           ├── config_flow.py
           ├── const.py
           ├── manifest.json
           ├── strings.json
           ├── switch.py
           ├── telemetry.py
           └── translations/
               ├── de.json
               └── en.json
   ```
5. **Restart Home Assistant**

---

## Prerequisites (IMPORTANT!)

### 1. Get ABRP API Key

You need a **free Telemetry API Key** from Iternio:

1. Send an email to: **contact@iternio.com**
2. Subject: "ABRP Telemetry API Key Request"
3. Content: Briefly describe that you want to use the Home Assistant integration
4. You'll typically receive the API key within 1-2 business days

### 2. Get User Token from ABRP

1. Open the **ABRP App** on your smartphone (or the website)
2. Go to: **Settings** (⚙️)
3. Select: **Car Settings** → **Your Car** (or your vehicle name)
4. Scroll down to: **Generic**
5. Tap: **Show Token**
6. Copy the displayed token (long alphanumeric string)

---

## Setup in Home Assistant

### Step by Step

1. Go to: **Settings** → **Devices & Services**
2. Click: **+ Add Integration** (bottom right)
3. Search for: **"ABRP Telemetry"**
4. **Step 1 - Credentials:**

   | Field | Description |
   |-------|-------------|
   | **API Key** | Your Iternio API Key (from contact@iternio.com) |
   | **User Token** | Your ABRP User Token (from the app) |
   | **Update Interval** | Seconds between uploads (5-60, default: 5) |

5. **Step 2 - Manufacturer:** Select your vehicle manufacturer from the dropdown list (alphabetically sorted)

6. **Step 3 - Model:** Select your exact vehicle model from the filtered list

7. **Step 4 - Basic Sensors:**

   | Field | Description |
   |-------|-------------|
   | **SOC Entity** | **REQUIRED:** Sensor for state of charge (%) |
   | **Speed Entity** | Optional: Sensor for speed (km/h) |
   | **Position Entity** | Optional: device_tracker with GPS coordinates |
   | **Power Entity** | Optional: Instantaneous power (kW) |
   | **Charging Entity** | Optional: Charging status (on/off) |
   | **Range Entity** | Optional: Estimated range (km) |
   | **Odometer Entity** | Optional: Odometer (km) |

8. **Step 5 - Advanced Sensors (optional):**

   | Field | Description |
   |-------|-------------|
   | **SOH Entity** | State of Health (%) |
   | **Voltage Entity** | Battery voltage (V) |
   | **Current Entity** | Battery current (A) |
   | **Battery Temp Entity** | Battery temperature (°C) |
   | **Ext Temp Entity** | Outside temperature (°C) |

9. Click **"Submit"**

### Changing Configuration Later

You can modify all sensor mappings after initial setup:

1. Go to: **Settings** → **Devices & Services** → **ABRP Telemetry**
2. Click: **Configure** (gear icon)
3. The current values of all assigned entities are displayed
4. Modify any sensor assignment as needed
5. Click **"Submit"** to save

### What Happens After Setup?

✅ The integration starts **immediately and automatically**  
✅ Every X seconds, data is sent to ABRP  
✅ You'll see a log entry: "ABRP Telemetry Integration started successfully"  
✅ Your live data should appear in ABRP within ~1 minute

---

## Entity Mapping Examples

### Mercedes (mb2020 Integration)

| Parameter | Example Entity |
|-----------|----------------|
| SOC | `sensor.my_mercedes_soc` |
| Speed | `sensor.my_mercedes_speed` |
| Position | `device_tracker.my_mercedes` |
| Power | `sensor.my_mercedes_power` |
| Charging | `binary_sensor.my_mercedes_charging` |
| Odometer | `sensor.my_mercedes_odometer` |
| Range | `sensor.my_mercedes_range` |

> **Note on Position:** Many vehicle integrations provide a `device_tracker` entity that stores latitude and longitude as **attributes**, not as the state value. This integration automatically detects this and extracts the coordinates from the attributes. Simply select the same `device_tracker` entity for both **Latitude** and **Longitude** fields, or just the **Latitude** field – the integration will find both coordinates automatically.

### PSA (Peugeot/Citroën/Opel)

| Parameter | Example Entity |
|-----------|----------------|
| SOC | `sensor.my_peugeot_battery_level` |
| Position | `device_tracker.my_peugeot` |
| Charging | `binary_sensor.my_peugeot_charging` |
| Range | `sensor.my_peugeot_electric_range` |
| Odometer | `sensor.my_peugeot_mileage` |

### Generic

| Parameter | Example Entity |
|-----------|----------------|
| SOC | `sensor.ev_battery_level` |
| Speed | `sensor.ev_speed` |
| Power | `sensor.ev_power_consumption` |
| Charging | `binary_sensor.ev_charging` |

**Tip:** Check your available entities under:  
**Developer Tools** → **States** → Search for your vehicle name

---

## Parameter Reference

| Parameter | Description | Unit |
|-----------|-------------|------|
| `utc` | UTC Timestamp | Seconds (Epoch) |
| `soc` | State of Charge | % |
| `speed` | Speed | km/h |
| `lat` / `lon` | GPS Position | Degrees |
| `power` | Instantaneous power (+ = discharge, - = charge) | kW |
| `is_charging` | Vehicle charging | 0/1 |
| `ext_temp` | Outside temperature | °C |
| `batt_temp` | Battery temperature | °C |
| `soh` | State of Health | % |
| `odometer` | Odometer | km |
| `est_battery_range` | Estimated range | km |
| `voltage` | Battery voltage | V |
| `current` | Battery current | A |

## Update Interval

ABRP recommends a data point every **5 seconds** for best results. Less than every 30 seconds is not recommended.

For individual consumption calibration, ABRP needs at least `speed`, `power`, and `is_charging` every 10 seconds.

---

## On/Off Switch

After setup, a switch is automatically created:

**Entity:** `switch.abrp_telemetry_upload`

| State | Meaning |
|-------|---------|
| **ON** | Upload active - Data sent every X seconds |
| **OFF** | Upload paused - No data sent |

### Using in Automations

**Example 1: Upload only while driving**
```yaml
automation:
  - alias: "ABRP on when driving"
    trigger:
      - platform: numeric_state
        entity_id: sensor.my_car_speed  # Replace with your speed sensor
        above: 0
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.abrp_telemetry_upload

  - alias: "ABRP off when parked"
    trigger:
      - platform: numeric_state
        entity_id: sensor.my_car_speed  # Replace with your speed sensor
        below: 1
        for:
          minutes: 5
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.abrp_telemetry_upload
```

**Example 2: Enable upload when charging**
```yaml
automation:
  - alias: "ABRP on when charging"
    trigger:
      - platform: state
        entity_id: binary_sensor.my_car_charging  # Replace with your charging sensor
        to: "on"
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.abrp_telemetry_upload
```

**Example 3: Disable at night**
```yaml
automation:
  - alias: "ABRP off at night"
    trigger:
      - platform: time
        at: "23:00:00"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.abrp_telemetry_upload

  - alias: "ABRP on in morning"
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

### Enable Logging

Add the following to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.abrp_telemetry: debug
```

### Common Problems

1. **No data visible in ABRP**: 
   - The ABRP backend processes data in 60-second batches
   - Wait at least 1-2 minutes after setup
   - Check logs for errors

2. **SOC unavailable**: 
   - Make sure your vehicle integration is running and providing data
   - Check entity status under Developer Tools → States

3. **API Error 401 (Unauthorized)**: 
   - Verify your API Key (received from Iternio?)
   - Verify your User Token (copied from ABRP app?)

4. **API Error 400 (Bad Request)**: 
   - Check Car Model format (e.g., `mercedes:eqa:22:67:other`)
   - Make sure SOC has a valid value

5. **Integration not found**:
   - Did you restart Home Assistant after installation?
   - Is the folder correctly placed under `config/custom_components/abrp_telemetry/`?

---

## Developer Debugging

This integration includes built-in debugging features for developers.

### Method 1: Extended Logs (Easiest)

Add this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.abrp_telemetry: debug
```

Find logs at:
- **Web UI**: Settings → System → Logs
- **Docker**: `docker logs homeassistant -f`
- **SSH**: `tail -f /config/home-assistant.log`

### Method 2: VS Code Remote Debugging

For full step-by-step debugging with breakpoints:

**1. Install debugpy on Home Assistant:**
```bash
# In HA Terminal or SSH:
pip install debugpy
```

**2. Enable debug mode:**

Change in `custom_components/abrp_telemetry/const.py`:
```python
DEBUG_MODE = True  # Default is False
```

**3. Restart Home Assistant**

**4. Configure VS Code:**

The project includes a `.vscode/launch.json`. Open the project in VS Code:
- Press `Ctrl+Shift+D` (Run and Debug)
- Select **"HA: Remote Attach"**
- Adjust host as needed (e.g., `homeassistant.local` or IP address)
- Press `F5`

**5. Set breakpoints:**

Click next to the line number in:
- `telemetry.py` - For data transmission
- `switch.py` - For on/off switch
- `config_flow.py` - For setup wizard

### Method 3: Local Test Installation

For quick testing without your production HA:

```powershell
# Windows PowerShell
python -m venv ha_test
.\ha_test\Scripts\Activate.ps1
pip install homeassistant

# Prepare config folder
mkdir ha_config\custom_components
Copy-Item -Recurse .\custom_components\abrp_telemetry ha_config\custom_components\

# Start Home Assistant
hass -c .\ha_config --debug
```

Then open http://localhost:8123 in your browser.

### Check Debug Status

The switch `switch.abrp_telemetry_upload` shows these attributes:
- `is_paused` - Paused due to errors?
- `consecutive_errors` - Errors in a row
- `total_sends` - Successfully sent
- `total_errors` - Total errors
- `last_successful_send` - Last successful upload (Unix timestamp)

View these under **Developer Tools → States**.

---

## Uninstallation

1. Go to: **Settings** → **Devices & Services**
2. Find the ABRP Telemetry Integration
3. Click the three-dot menu (⋮) → **Delete**
4. Optional: Delete the folder `custom_components/abrp_telemetry`

---

## License

MIT License - Free to use and modify.

---

## Development & AI Assistance

This integration was developed with the assistance of **GitHub Copilot** (powered by Claude AI). The entire codebase, including the architecture, error handling, configuration flow, and documentation, was created through an interactive conversation between the developer and the AI assistant.

This transparent approach to AI-assisted development demonstrates how modern AI tools can help accelerate software development while maintaining code quality and best practices. The developer provided the requirements, domain knowledge, and iterative feedback, while the AI assisted with implementation, code generation, and documentation.

**Tools used:**
- VS Code with GitHub Copilot
- Claude AI (Anthropic)

---

## Support & Contribution

- **Report issues**: [GitHub Issues](https://github.com/Riffer/abrp_telemetry/issues)
- **Improvements**: Pull requests welcome!

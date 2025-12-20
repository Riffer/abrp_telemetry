"""Constants for ABRP Telemetry Integration."""

DOMAIN = "abrp_telemetry"

# API Configuration
ABRP_API_URL = "https://api.iternio.com/1/tlm/send"

# Debug Mode - Setze auf True für erweiterte Logs und optional Remote Debugging
# ACHTUNG: Nicht in Produktion aktivieren!
DEBUG_MODE = False
DEBUG_REMOTE_PORT = 5678  # Port für debugpy (VS Code Remote Attach)

# Configuration Keys
CONF_API_KEY = "api_key"
CONF_USER_TOKEN = "user_token"
CONF_CAR_MODEL = "car_model"
CONF_UPDATE_INTERVAL = "update_interval"

# Entity IDs für Mercedes mb2020 Integration
# Diese müssen an deine tatsächlichen Entity-IDs angepasst werden!
CONF_SOC_ENTITY = "soc_entity"
CONF_SPEED_ENTITY = "speed_entity"
CONF_LATITUDE_ENTITY = "latitude_entity"
CONF_LONGITUDE_ENTITY = "longitude_entity"
CONF_POWER_ENTITY = "power_entity"
CONF_CHARGING_ENTITY = "charging_entity"
CONF_EXT_TEMP_ENTITY = "ext_temp_entity"
CONF_BATT_TEMP_ENTITY = "batt_temp_entity"
CONF_ODOMETER_ENTITY = "odometer_entity"
CONF_RANGE_ENTITY = "range_entity"
CONF_SOH_ENTITY = "soh_entity"
CONF_VOLTAGE_ENTITY = "voltage_entity"
CONF_CURRENT_ENTITY = "current_entity"

# Default Values
DEFAULT_UPDATE_INTERVAL = 5  # Sekunden - ABRP empfiehlt 5 Sekunden
DEFAULT_CAR_MODEL = "mercedes:eqa:22:67:other"  # Mercedes EQA 250 (66.5 kWh nutzbar)

# Mercedes EQA 250 Spezifikationen (für Referenz)
# Batteriekapazität: 66.5 kWh (nutzbar)
# Brutto-Kapazität: ~70 kWh

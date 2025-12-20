"""Constants for ABRP Telemetry Integration."""

DOMAIN = "abrp_telemetry"

# API Configuration
ABRP_API_URL = "https://api.iternio.com/1/tlm/send"

# Debug Mode - Set to True for extended logs and optional remote debugging
# WARNING: Do not enable in production!
DEBUG_MODE = False
DEBUG_REMOTE_PORT = 5678  # Port for debugpy (VS Code Remote Attach)

# Configuration Keys
CONF_API_KEY = "api_key"
CONF_USER_TOKEN = "user_token"
CONF_CAR_MODEL = "car_model"
CONF_UPDATE_INTERVAL = "update_interval"

# Entity Configuration Keys
# Works with any Home Assistant vehicle integration (mb2020, PSA, Tesla, etc.)
CONF_SOC_ENTITY = "soc_entity"
CONF_SPEED_ENTITY = "speed_entity"
CONF_POSITION_ENTITY = "position_entity"  # device_tracker or sensor with lat/lon attributes
CONF_LATITUDE_ENTITY = "latitude_entity"  # Legacy - kept for backwards compatibility
CONF_LONGITUDE_ENTITY = "longitude_entity"  # Legacy - kept for backwards compatibility
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
DEFAULT_UPDATE_INTERVAL = 5  # Seconds - ABRP recommends 5 seconds
DEFAULT_CAR_MODEL = ""  # User must specify their car model from ABRP

# Find your car model at: https://api.iternio.com/1/tlm/get_carmodels_list
# Examples:
#   Mercedes EQA 250: mercedes:eqa:22:67:other
#   Peugeot e-208: peugeot:e208:20:50:other
#   Tesla Model 3 LR: tesla:model3:19:75:lr
#   Hyundai Ioniq 5: hyundai:ioniq5:21:77:awd

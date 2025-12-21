"""ABRP Telemetry Service - Sends vehicle telemetry data to ABRP."""
import logging
import time
import json
from urllib.parse import urlencode
import aiohttp
import asyncio
from typing import Any, Optional

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta

from .const import (
    ABRP_API_URL,
    CONF_API_KEY,
    CONF_USER_TOKEN,
    CONF_CAR_MODEL,
    DEFAULT_CAR_MODEL,
    CONF_UPDATE_INTERVAL,
    CONF_SOC_ENTITY,
    CONF_SPEED_ENTITY,
    CONF_POSITION_ENTITY,
    CONF_LATITUDE_ENTITY,
    CONF_LONGITUDE_ENTITY,
    CONF_POWER_ENTITY,
    CONF_CHARGING_ENTITY,
    CONF_EXT_TEMP_ENTITY,
    CONF_BATT_TEMP_ENTITY,
    CONF_ODOMETER_ENTITY,
    CONF_RANGE_ENTITY,
    CONF_SOH_ENTITY,
    CONF_VOLTAGE_ENTITY,
    CONF_CURRENT_ENTITY,
    CONF_SOH_FIXED,
    CONF_CAPACITY_FIXED,
    DEFAULT_UPDATE_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

# Error handling constants
MAX_CONSECUTIVE_ERRORS = 10  # Pause after X errors
ERROR_BACKOFF_MULTIPLIER = 2  # Exponential backoff
MAX_BACKOFF_SECONDS = 300  # Maximum 5 minutes pause
INITIAL_BACKOFF_SECONDS = 10  # Start with 10 seconds


class ABRPTelemetryService:
    """Service for sending telemetry data to ABRP."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]):
        """Initialize the telemetry service."""
        self.hass = hass
        self.config = config
        self._unsub_timer = None
        self._session: Optional[aiohttp.ClientSession] = None
        
        # Ein/Aus-Schalter Status
        self._is_enabled = True  # Standardmäßig aktiviert
        
        # Fehlerbehandlungs-Status
        self._consecutive_errors = 0
        self._is_paused = False
        self._current_backoff = INITIAL_BACKOFF_SECONDS
        self._last_successful_send = None
        self._total_sends = 0
        self._total_errors = 0
        self._last_payload = None  # Last telemetry data sent to ABRP
        
        # Konfiguration auslesen
        self.api_key = config.get(CONF_API_KEY)
        self.user_token = config.get(CONF_USER_TOKEN)
        self.car_model = config.get(CONF_CAR_MODEL, DEFAULT_CAR_MODEL)
        self.update_interval = config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        
        # Entity Mappings
        self.entity_map = {
            "soc": config.get(CONF_SOC_ENTITY),
            "speed": config.get(CONF_SPEED_ENTITY),
            "position": config.get(CONF_POSITION_ENTITY),  # New: single position entity
            "lat": config.get(CONF_LATITUDE_ENTITY),  # Legacy support
            "lon": config.get(CONF_LONGITUDE_ENTITY),  # Legacy support
            "power": config.get(CONF_POWER_ENTITY),
            "is_charging": config.get(CONF_CHARGING_ENTITY),
            "ext_temp": config.get(CONF_EXT_TEMP_ENTITY),
            "batt_temp": config.get(CONF_BATT_TEMP_ENTITY),
            "odometer": config.get(CONF_ODOMETER_ENTITY),
            "est_battery_range": config.get(CONF_RANGE_ENTITY),
            "soh": config.get(CONF_SOH_ENTITY),
            "voltage": config.get(CONF_VOLTAGE_ENTITY),
            "current": config.get(CONF_CURRENT_ENTITY),
        }
        
        # Fixed values (manually entered by user)
        self.fixed_values = {
            "soh": config.get(CONF_SOH_FIXED, 0),  # State of Health in %
            "capacity": config.get(CONF_CAPACITY_FIXED, 0),  # Usable battery capacity in kWh
        }

    async def async_start(self):
        """Start the telemetry service."""
        _LOGGER.debug("ABRP Telemetry: async_start() called")
        
        # Validate configuration before starting
        if not self._validate_configuration():
            _LOGGER.error("ABRP Telemetry: Configuration incomplete - service not started")
            return False
        
        _LOGGER.info(f"ABRP Telemetry: Starting service with {self.update_interval}s interval")
        _LOGGER.debug(f"ABRP Telemetry: Car model: {self.car_model}")
        _LOGGER.debug(f"ABRP Telemetry: Entity mappings: {self.entity_map}")
        
        # Create HTTP session
        self._session = aiohttp.ClientSession()
        
        # Start timer for regular updates
        self._unsub_timer = async_track_time_interval(
            self.hass,
            self._async_send_telemetry,
            timedelta(seconds=self.update_interval)
        )
        
        _LOGGER.debug("ABRP Telemetry: Timer registered, sending first telemetry...")
        
        # Send first telemetry immediately
        await self._async_send_telemetry()
        _LOGGER.info("ABRP Telemetry: Service started successfully")
        return True
    
    @property
    def is_enabled(self) -> bool:
        """Return whether the service is enabled."""
        return self._is_enabled
    
    def enable(self):
        """Enable telemetry upload."""
        self._is_enabled = True
        # Reset error state when manually enabled
        self._consecutive_errors = 0
        self._is_paused = False
        self._current_backoff = INITIAL_BACKOFF_SECONDS
        _LOGGER.info("ABRP Telemetry upload enabled")
    
    def disable(self):
        """Disable telemetry upload."""
        self._is_enabled = False
        _LOGGER.info("ABRP Telemetry upload disabled")
    
    def _validate_configuration(self) -> bool:
        """Check if configuration is complete."""
        errors = []
        
        if not self.api_key:
            errors.append("API Key missing")
        
        if not self.user_token:
            errors.append("User Token missing")
        
        if not self.entity_map.get("soc"):
            errors.append("SOC Entity not configured")
        
        if errors:
            for error in errors:
                _LOGGER.error(f"ABRP Telemetry configuration error: {error}")
            return False
        
        return True

    async def async_stop(self):
        """Stop the telemetry service."""
        _LOGGER.info("Stopping ABRP Telemetry Service")
        
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None
        
        if self._session:
            await self._session.close()
            self._session = None

    def _get_entity_value(self, entity_id: Optional[str], default=None) -> Any:
        """Get current value of an entity."""
        if not entity_id:
            return default
        
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", None):
            return default
        
        try:
            # Try to parse numeric value
            value = float(state.state)
            return value
        except (ValueError, TypeError):
            # For boolean/string values
            return state.state

    def _get_position(self) -> tuple[Optional[float], Optional[float]]:
        """Get latitude and longitude from configured entities.
        
        Supports:
        - New: Single position entity (device_tracker with lat/lon attributes)
        - Legacy: Separate lat/lon sensor entities
        - Any entity with latitude/longitude attributes
        """
        lat = None
        lon = None
        
        # New: Check position_entity first (preferred)
        position_entity = self.entity_map.get("position")
        if position_entity:
            state = self.hass.states.get(position_entity)
            if state and state.attributes:
                lat = state.attributes.get("latitude")
                lon = state.attributes.get("longitude")
                if lat is not None and lon is not None:
                    return (float(lat), float(lon))
        
        # Legacy support: separate lat/lon entities
        lat_entity = self.entity_map.get("lat")
        lon_entity = self.entity_map.get("lon")
        
        # Case 1: Same entity for both (device_tracker)
        if lat_entity and lat_entity == lon_entity:
            state = self.hass.states.get(lat_entity)
            if state and state.attributes:
                lat = state.attributes.get("latitude")
                lon = state.attributes.get("longitude")
                if lat is not None and lon is not None:
                    return (float(lat), float(lon))
        
        # Case 2: Only lat entity provided - check if it's a device_tracker with both values
        if lat_entity and not lon_entity:
            state = self.hass.states.get(lat_entity)
            if state and state.attributes:
                lat = state.attributes.get("latitude")
                lon = state.attributes.get("longitude")
                if lat is not None and lon is not None:
                    return (float(lat), float(lon))
        
        # Case 3: Separate entities for lat and lon
        if lat_entity:
            state = self.hass.states.get(lat_entity)
            if state:
                # First check attributes (for device_tracker)
                if "latitude" in (state.attributes or {}):
                    lat = state.attributes.get("latitude")
                # Then try state value (for sensor)
                elif state.state not in ("unknown", "unavailable", None):
                    try:
                        lat = float(state.state)
                    except (ValueError, TypeError):
                        pass
        
        if lon_entity:
            state = self.hass.states.get(lon_entity)
            if state:
                # First check attributes (for device_tracker)
                if "longitude" in (state.attributes or {}):
                    lon = state.attributes.get("longitude")
                # Then try state value (for sensor)
                elif state.state not in ("unknown", "unavailable", None):
                    try:
                        lon = float(state.state)
                    except (ValueError, TypeError):
                        pass
        
        if lat is not None and lon is not None:
            return (float(lat), float(lon))
        
        return (None, None)

    def _get_charging_state(self, entity_id: Optional[str]) -> Optional[int]:
        """Determine charging state (0 or 1)."""
        if not entity_id:
            return None
        
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", None):
            return None
        
        # Support various formats
        state_value = state.state.lower()
        
        if state_value in ("on", "true", "1", "charging", "yes"):
            return 1
        elif state_value in ("off", "false", "0", "not_charging", "no", "idle"):
            return 0
        
        # Try numeric
        try:
            return 1 if float(state.state) > 0 else 0
        except (ValueError, TypeError):
            return None

    def _build_telemetry_data(self) -> dict:
        """Build the telemetry data object for ABRP."""
        telemetry = {
            "utc": int(time.time()),
            "car_model": self.car_model,
        }
        
        # SOC (State of Charge) - Required field
        soc = self._get_entity_value(self.entity_map["soc"])
        if soc is not None:
            telemetry["soc"] = soc
        
        # Speed
        speed = self._get_entity_value(self.entity_map["speed"])
        if speed is not None:
            telemetry["speed"] = speed
        
        # Position - supports both separate lat/lon sensors and device_tracker entities
        lat, lon = self._get_position()
        if lat is not None and lon is not None:
            telemetry["lat"] = lat
            telemetry["lon"] = lon
        
        # Power (kW)
        power = self._get_entity_value(self.entity_map["power"])
        if power is not None:
            telemetry["power"] = power
        
        # Charging state
        is_charging = self._get_charging_state(self.entity_map["is_charging"])
        if is_charging is not None:
            telemetry["is_charging"] = is_charging
        
        # Outside temperature
        ext_temp = self._get_entity_value(self.entity_map["ext_temp"])
        if ext_temp is not None:
            telemetry["ext_temp"] = ext_temp
        
        # Battery temperature
        batt_temp = self._get_entity_value(self.entity_map["batt_temp"])
        if batt_temp is not None:
            telemetry["batt_temp"] = batt_temp
        
        # Odometer
        odometer = self._get_entity_value(self.entity_map["odometer"])
        if odometer is not None:
            telemetry["odometer"] = odometer
        
        # Estimated range
        est_range = self._get_entity_value(self.entity_map["est_battery_range"])
        if est_range is not None:
            telemetry["est_battery_range"] = est_range
        
        # State of Health (Battery health) - prefer sensor, fallback to fixed value
        soh = self._get_entity_value(self.entity_map["soh"])
        if soh is not None:
            telemetry["soh"] = soh
        elif self.fixed_values.get("soh", 0) > 0:
            telemetry["soh"] = self.fixed_values["soh"]
        
        # Usable Battery Capacity (fixed value only - usually not from sensor)
        capacity = self.fixed_values.get("capacity", 0)
        if capacity and capacity > 0:
            telemetry["capacity"] = capacity
        
        # Voltage
        voltage = self._get_entity_value(self.entity_map["voltage"])
        if voltage is not None:
            telemetry["voltage"] = voltage
        
        # Current
        current = self._get_entity_value(self.entity_map["current"])
        if current is not None:
            telemetry["current"] = current
        
        return telemetry

    async def _async_send_telemetry(self, now=None):
        """Send telemetry data to ABRP."""
        # Check if service is disabled by user
        if not self._is_enabled:
            _LOGGER.debug("ABRP Telemetry is disabled (switch off)")
            return
        
        # Check if service is paused (after too many errors)
        if self._is_paused:
            _LOGGER.debug("ABRP Telemetry is paused due to previous errors")
            return
        
        if not self._session:
            _LOGGER.warning("HTTP session not available")
            return
        
        telemetry = self._build_telemetry_data()
        
        # Store the payload for status display (even if not sent)
        self._last_payload = telemetry
        
        # At minimum, SOC must be present
        if "soc" not in telemetry:
            _LOGGER.warning("SOC value not available, skipping telemetry transmission")
            self._handle_soft_error("SOC not available")
            return
        
        # Log telemetry values at info level for visibility
        _LOGGER.info(f"ABRP Telemetry sending: SOC={telemetry.get('soc')}%, "
                     f"Speed={telemetry.get('speed', 'N/A')} km/h, "
                     f"Power={telemetry.get('power', 'N/A')} kW, "
                     f"Charging={telemetry.get('is_charging', 'N/A')}")
        _LOGGER.debug(f"ABRP Telemetry full data: {telemetry}")
        
        try:
            # Build URL with parameters
            params = {
                "token": self.user_token,
                "tlm": json.dumps(telemetry)
            }
            
            headers = {
                "Authorization": f"APIKEY {self.api_key}"
            }
            
            url = f"{ABRP_API_URL}?{urlencode(params)}"
            
            async with self._session.post(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("status") == "ok":
                        self._total_sends += 1
                        _LOGGER.info(f"ABRP Telemetry: Successfully sent (total: {self._total_sends})")
                        self._handle_success()
                    else:
                        _LOGGER.warning(f"ABRP response: {result}")
                        self._handle_api_error(f"ABRP response not OK: {result}")
                elif response.status == 401:
                    _LOGGER.error("ABRP authentication error (401): Check API key and user token")
                    self._handle_critical_error("Authentication failed")
                elif response.status == 400:
                    error_text = await response.text()
                    _LOGGER.error(f"ABRP Bad Request (400): {error_text}")
                    self._handle_api_error(f"Invalid request: {error_text}")
                elif response.status == 429:
                    _LOGGER.warning("ABRP rate limit reached (429) - pausing temporarily")
                    self._handle_rate_limit()
                else:
                    _LOGGER.error(f"ABRP HTTP error: {response.status}")
                    self._handle_api_error(f"HTTP {response.status}")
                    
        except asyncio.TimeoutError:
            _LOGGER.warning("Timeout sending to ABRP - server unreachable?")
            self._handle_network_error("Timeout")
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Network error sending to ABRP: {e}")
            self._handle_network_error(str(e))
        except Exception as e:
            _LOGGER.error(f"Unexpected error sending telemetry: {e}")
            self._handle_api_error(str(e))

    def _handle_success(self):
        """Handle successful transmission."""
        self._consecutive_errors = 0
        self._current_backoff = INITIAL_BACKOFF_SECONDS
        self._last_successful_send = time.time()
        # Note: _total_sends is incremented before calling this method
        
        # If paused, re-enable
        if self._is_paused:
            _LOGGER.info("ABRP Telemetry: Transmission restored")
            self._is_paused = False

    def _handle_soft_error(self, reason: str):
        """Handle soft error (e.g., missing data)."""
        # Soft errors don't increase error counter as much
        _LOGGER.debug(f"Soft error: {reason}")

    def _handle_network_error(self, reason: str):
        """Handle network error with backoff."""
        self._consecutive_errors += 1
        self._total_errors += 1
        
        if self._consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            self._pause_with_backoff(f"Network error: {reason}")

    def _handle_api_error(self, reason: str):
        """Handle API error."""
        self._consecutive_errors += 1
        self._total_errors += 1
        
        if self._consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            self._pause_with_backoff(f"API error: {reason}")

    def _handle_critical_error(self, reason: str):
        """Handle critical error (e.g., auth error) - pause immediately."""
        _LOGGER.error(f"Critical error: {reason} - service paused")
        self._is_paused = True
        self._total_errors += 1
        # Longer pause for auth errors
        self._schedule_resume(600)  # 10 minutes

    def _handle_rate_limit(self):
        """Handle rate limiting."""
        self._pause_with_backoff("Rate limit reached")

    def _pause_with_backoff(self, reason: str):
        """Pause service with exponential backoff."""
        self._is_paused = True
        
        _LOGGER.warning(
            f"ABRP Telemetry paused for {self._current_backoff}s "
            f"after {self._consecutive_errors} consecutive errors. "
            f"Reason: {reason}"
        )
        
        # Schedule resume after backoff time
        self._schedule_resume(self._current_backoff)
        
        # Increase backoff for next time
        self._current_backoff = min(
            self._current_backoff * ERROR_BACKOFF_MULTIPLIER,
            MAX_BACKOFF_SECONDS
        )

    def _schedule_resume(self, seconds: int):
        """Schedule resume after pause."""
        async def resume():
            await asyncio.sleep(seconds)
            if self._is_paused:
                _LOGGER.info(f"ABRP Telemetry: Attempting resume after {seconds}s pause")
                self._is_paused = False
        
        asyncio.create_task(resume())

    def get_status(self) -> dict:
        """Return current service status."""
        return {
            "is_enabled": self._is_enabled,
            "is_running": self._is_enabled and not self._is_paused and self._session is not None,
            "is_paused": self._is_paused,
            "consecutive_errors": self._consecutive_errors,
            "total_sends": self._total_sends,
            "total_errors": self._total_errors,
            "last_successful_send": self._last_successful_send,
            "current_backoff_seconds": self._current_backoff,
            "last_payload": self._last_payload,
        }

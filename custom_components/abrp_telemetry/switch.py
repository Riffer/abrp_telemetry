"""Switch platform for ABRP Telemetry - Enable/Disable Upload."""
import logging
import json
from datetime import datetime

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ABRP Telemetry switch from a config entry."""
    data = hass.data[DOMAIN][config_entry.entry_id]
    service = data.get("service")
    
    if service:
        async_add_entities([ABRPTelemetrySwitch(config_entry, service)], True)


class ABRPTelemetrySwitch(SwitchEntity):
    """Switch to enable/disable ABRP Telemetry upload."""

    def __init__(self, config_entry: ConfigEntry, service) -> None:
        """Initialize the switch."""
        self._config_entry = config_entry
        self._service = service
        self._attr_unique_id = f"{config_entry.entry_id}_upload_enabled"
        self._attr_name = "ABRP Telemetry Upload"
        self._attr_icon = "mdi:cloud-upload"
        self._attr_has_entity_name = True

    @property
    def device_info(self):
        """Return device info."""
        return {
            "identifiers": {(DOMAIN, self._config_entry.entry_id)},
            "name": "ABRP Telemetry",
            "manufacturer": "Iternio",
            "model": "Telemetry API",
            "sw_version": "1.0.0",
        }

    @property
    def is_on(self) -> bool:
        """Return true if upload is enabled."""
        return self._service.is_enabled if self._service else False

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._service is not None

    @property
    def extra_state_attributes(self):
        """Return additional state attributes."""
        if not self._service:
            return {}
        
        status = self._service.get_status()
        
        # Convert Unix timestamp to readable datetime
        last_send = status.get("last_successful_send")
        if last_send:
            try:
                last_send_dt = datetime.fromtimestamp(last_send)
                last_send_formatted = last_send_dt.isoformat()
            except (ValueError, TypeError, OSError):
                last_send_formatted = None
        else:
            last_send_formatted = None
        
        # Format last payload as JSON string for display
        last_payload = status.get("last_payload")
        if last_payload:
            # Remove sensitive/redundant fields for display
            display_payload = {k: v for k, v in last_payload.items() if k != "car_model"}
            payload_json = json.dumps(display_payload, indent=2)
        else:
            payload_json = None
        
        return {
            "is_paused": status.get("is_paused", False),
            "consecutive_errors": status.get("consecutive_errors", 0),
            "total_sends": status.get("total_sends", 0),
            "total_errors": status.get("total_errors", 0),
            "last_successful_send": last_send_formatted,
            "last_payload": payload_json,
        }

    async def async_turn_on(self, **kwargs) -> None:
        """Enable telemetry upload."""
        if self._service:
            self._service.enable()
            _LOGGER.info("ABRP Telemetry Upload aktiviert")

    async def async_turn_off(self, **kwargs) -> None:
        """Disable telemetry upload."""
        if self._service:
            self._service.disable()
            _LOGGER.info("ABRP Telemetry Upload deaktiviert")

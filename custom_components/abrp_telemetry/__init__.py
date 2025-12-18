"""ABRP (A Better Route Planner) Telemetry Integration für Home Assistant."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = []


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ABRP Telemetry from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Starte den Telemetry Service
    from .telemetry import ABRPTelemetryService
    
    service = ABRPTelemetryService(hass, entry.data)
    await service.async_start()
    
    hass.data[DOMAIN][entry.entry_id] = {
        "service": service,
        "config": entry.data
    }
    
    _LOGGER.info("ABRP Telemetry Integration erfolgreich gestartet")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if entry.entry_id in hass.data[DOMAIN]:
        service = hass.data[DOMAIN][entry.entry_id].get("service")
        if service:
            await service.async_stop()
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return True

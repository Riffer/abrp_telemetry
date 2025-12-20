"""ABRP (A Better Route Planner) Telemetry Integration für Home Assistant."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["switch"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ABRP Telemetry from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Starte den Telemetry Service
    from .telemetry import ABRPTelemetryService
    
    service = ABRPTelemetryService(hass, entry.data)
    started = await service.async_start()
    
    if not started:
        _LOGGER.error("ABRP Telemetry Service konnte nicht gestartet werden - Konfiguration prüfen")
        return False
    
    hass.data[DOMAIN][entry.entry_id] = {
        "service": service,
        "config": entry.data
    }
    
    # Plattformen laden (Switch)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info("ABRP Telemetry Integration erfolgreich gestartet")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Plattformen entladen
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if entry.entry_id in hass.data[DOMAIN]:
        service = hass.data[DOMAIN][entry.entry_id].get("service")
        if service:
            await service.async_stop()
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok

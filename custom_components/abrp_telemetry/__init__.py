"""ABRP (A Better Route Planner) Telemetry Integration for Home Assistant."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, DEBUG_MODE, DEBUG_REMOTE_PORT

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["switch"]

# Initialize debug mode
if DEBUG_MODE:
    _LOGGER.warning("ABRP Telemetry DEBUG MODE is enabled!")
    try:
        import debugpy
        debugpy.listen(("0.0.0.0", DEBUG_REMOTE_PORT))
        _LOGGER.info(f"debugpy waiting for connection on port {DEBUG_REMOTE_PORT}")
        # Uncomment to wait for debugger:
        # debugpy.wait_for_client()
    except ImportError:
        _LOGGER.warning("debugpy not installed - remote debugging not available")
    except Exception as e:
        _LOGGER.warning(f"debugpy could not be started: {e}")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ABRP Telemetry from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data
    
    # Start telemetry service
    from .telemetry import ABRPTelemetryService
    
    service = ABRPTelemetryService(hass, entry.data)
    started = await service.async_start()
    
    if not started:
        _LOGGER.error("ABRP Telemetry Service could not be started - check configuration")
        return False
    
    hass.data[DOMAIN][entry.entry_id] = {
        "service": service,
        "config": entry.data
    }
    
    # Load platforms (Switch)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info("ABRP Telemetry Integration started successfully")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if entry.entry_id in hass.data[DOMAIN]:
        service = hass.data[DOMAIN][entry.entry_id].get("service")
        if service:
            await service.async_stop()
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok

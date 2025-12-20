"""ABRP Telemetry Service - Sendet Fahrzeugdaten an ABRP."""
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
    CONF_UPDATE_INTERVAL,
    CONF_SOC_ENTITY,
    CONF_SPEED_ENTITY,
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
    DEFAULT_UPDATE_INTERVAL,
    DEFAULT_CAR_MODEL,
)

_LOGGER = logging.getLogger(__name__)

# Fehlerbehandlungs-Konstanten
MAX_CONSECUTIVE_ERRORS = 10  # Nach X Fehlern pausieren
ERROR_BACKOFF_MULTIPLIER = 2  # Exponentielles Backoff
MAX_BACKOFF_SECONDS = 300  # Maximal 5 Minuten Pause
INITIAL_BACKOFF_SECONDS = 10  # Start mit 10 Sekunden


class ABRPTelemetryService:
    """Service zum Senden von Telemetriedaten an ABRP."""

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
        
        # Konfiguration auslesen
        self.api_key = config.get(CONF_API_KEY)
        self.user_token = config.get(CONF_USER_TOKEN)
        self.car_model = config.get(CONF_CAR_MODEL, DEFAULT_CAR_MODEL)
        self.update_interval = config.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        
        # Entity Mappings
        self.entity_map = {
            "soc": config.get(CONF_SOC_ENTITY),
            "speed": config.get(CONF_SPEED_ENTITY),
            "lat": config.get(CONF_LATITUDE_ENTITY),
            "lon": config.get(CONF_LONGITUDE_ENTITY),
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

    async def async_start(self):
        """Start the telemetry service."""
        # Validiere Konfiguration vor dem Start
        if not self._validate_configuration():
            _LOGGER.error("ABRP Telemetry: Konfiguration unvollständig - Service wird nicht gestartet")
            return False
        
        _LOGGER.info(f"Starte ABRP Telemetry Service mit Interval von {self.update_interval} Sekunden")
        
        # HTTP Session erstellen
        self._session = aiohttp.ClientSession()
        
        # Timer für regelmäßige Updates starten
        self._unsub_timer = async_track_time_interval(
            self.hass,
            self._async_send_telemetry,
            timedelta(seconds=self.update_interval)
        )
        
        # Sofort erste Telemetrie senden
        await self._async_send_telemetry()
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
        _LOGGER.info("ABRP Telemetry Upload wurde aktiviert")
    
    def disable(self):
        """Disable telemetry upload."""
        self._is_enabled = False
        _LOGGER.info("ABRP Telemetry Upload wurde deaktiviert")
    
    def _validate_configuration(self) -> bool:
        """Prüfe ob die Konfiguration vollständig ist."""
        errors = []
        
        if not self.api_key:
            errors.append("API Key fehlt")
        
        if not self.user_token:
            errors.append("User Token fehlt")
        
        if not self.entity_map.get("soc"):
            errors.append("SOC Entity nicht konfiguriert")
        
        if errors:
            for error in errors:
                _LOGGER.error(f"ABRP Telemetry Konfigurationsfehler: {error}")
            return False
        
        return True

    async def async_stop(self):
        """Stop the telemetry service."""
        _LOGGER.info("Stoppe ABRP Telemetry Service")
        
        if self._unsub_timer:
            self._unsub_timer()
            self._unsub_timer = None
        
        if self._session:
            await self._session.close()
            self._session = None

    def _get_entity_value(self, entity_id: Optional[str], default=None) -> Any:
        """Hole den aktuellen Wert einer Entity."""
        if not entity_id:
            return default
        
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", None):
            return default
        
        try:
            # Versuche numerischen Wert zu parsen
            value = float(state.state)
            return value
        except (ValueError, TypeError):
            # Für Boolean/String Werte
            return state.state

    def _get_charging_state(self, entity_id: Optional[str]) -> Optional[int]:
        """Ermittle den Ladezustand (0 oder 1)."""
        if not entity_id:
            return None
        
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable", None):
            return None
        
        # Verschiedene Formate unterstützen
        state_value = state.state.lower()
        
        if state_value in ("on", "true", "1", "charging", "yes"):
            return 1
        elif state_value in ("off", "false", "0", "not_charging", "no", "idle"):
            return 0
        
        # Versuche numerisch
        try:
            return 1 if float(state.state) > 0 else 0
        except (ValueError, TypeError):
            return None

    def _build_telemetry_data(self) -> dict:
        """Erstelle das Telemetrie-Datenobjekt für ABRP."""
        telemetry = {
            "utc": int(time.time()),
            "car_model": self.car_model,
        }
        
        # SOC (State of Charge) - Pflichtfeld
        soc = self._get_entity_value(self.entity_map["soc"])
        if soc is not None:
            telemetry["soc"] = soc
        
        # Geschwindigkeit
        speed = self._get_entity_value(self.entity_map["speed"])
        if speed is not None:
            telemetry["speed"] = speed
        
        # Position
        lat = self._get_entity_value(self.entity_map["lat"])
        lon = self._get_entity_value(self.entity_map["lon"])
        if lat is not None and lon is not None:
            telemetry["lat"] = lat
            telemetry["lon"] = lon
        
        # Leistung (kW)
        power = self._get_entity_value(self.entity_map["power"])
        if power is not None:
            telemetry["power"] = power
        
        # Ladezustand
        is_charging = self._get_charging_state(self.entity_map["is_charging"])
        if is_charging is not None:
            telemetry["is_charging"] = is_charging
        
        # Außentemperatur
        ext_temp = self._get_entity_value(self.entity_map["ext_temp"])
        if ext_temp is not None:
            telemetry["ext_temp"] = ext_temp
        
        # Batterietemperatur
        batt_temp = self._get_entity_value(self.entity_map["batt_temp"])
        if batt_temp is not None:
            telemetry["batt_temp"] = batt_temp
        
        # Kilometerstand
        odometer = self._get_entity_value(self.entity_map["odometer"])
        if odometer is not None:
            telemetry["odometer"] = odometer
        
        # Geschätzte Reichweite
        est_range = self._get_entity_value(self.entity_map["est_battery_range"])
        if est_range is not None:
            telemetry["est_battery_range"] = est_range
        
        # State of Health (Batteriegesundheit)
        soh = self._get_entity_value(self.entity_map["soh"])
        if soh is not None:
            telemetry["soh"] = soh
        
        # Spannung
        voltage = self._get_entity_value(self.entity_map["voltage"])
        if voltage is not None:
            telemetry["voltage"] = voltage
        
        # Stromstärke
        current = self._get_entity_value(self.entity_map["current"])
        if current is not None:
            telemetry["current"] = current
        
        return telemetry

    async def _async_send_telemetry(self, now=None):
        """Sende Telemetriedaten an ABRP."""
        # Prüfe ob Service vom Benutzer deaktiviert wurde
        if not self._is_enabled:
            _LOGGER.debug("ABRP Telemetry ist deaktiviert (Schalter aus)")
            return
        
        # Prüfe ob Service pausiert ist (nach zu vielen Fehlern)
        if self._is_paused:
            _LOGGER.debug("ABRP Telemetry ist pausiert wegen vorheriger Fehler")
            return
        
        if not self._session:
            _LOGGER.warning("HTTP Session nicht verfügbar")
            return
        
        telemetry = self._build_telemetry_data()
        
        # Mindestens SOC muss vorhanden sein
        if "soc" not in telemetry:
            _LOGGER.warning("SOC-Wert nicht verfügbar, überspringe Telemetrie-Übertragung")
            self._handle_soft_error("SOC nicht verfügbar")
            return
        
        try:
            # URL mit Parametern aufbauen
            params = {
                "token": self.user_token,
                "tlm": json.dumps(telemetry)
            }
            
            headers = {
                "Authorization": f"APIKEY {self.api_key}"
            }
            
            url = f"{ABRP_API_URL}?{urlencode(params)}"
            
            _LOGGER.debug(f"Sende Telemetrie an ABRP: {telemetry}")
            
            async with self._session.post(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("status") == "ok":
                        _LOGGER.debug("Telemetrie erfolgreich an ABRP gesendet")
                        self._handle_success()
                    else:
                        _LOGGER.warning(f"ABRP Antwort: {result}")
                        self._handle_api_error(f"ABRP Antwort nicht OK: {result}")
                elif response.status == 401:
                    _LOGGER.error("ABRP Authentifizierungsfehler (401): Prüfe API-Key und User Token")
                    self._handle_critical_error("Authentifizierung fehlgeschlagen")
                elif response.status == 400:
                    error_text = await response.text()
                    _LOGGER.error(f"ABRP Bad Request (400): {error_text}")
                    self._handle_api_error(f"Ungültige Anfrage: {error_text}")
                elif response.status == 429:
                    _LOGGER.warning("ABRP Rate Limit erreicht (429) - pausiere vorübergehend")
                    self._handle_rate_limit()
                else:
                    _LOGGER.error(f"ABRP HTTP Fehler: {response.status}")
                    self._handle_api_error(f"HTTP {response.status}")
                    
        except asyncio.TimeoutError:
            _LOGGER.warning("Timeout beim Senden an ABRP - Server nicht erreichbar?")
            self._handle_network_error("Timeout")
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Netzwerkfehler beim Senden an ABRP: {e}")
            self._handle_network_error(str(e))
        except Exception as e:
            _LOGGER.error(f"Unerwarteter Fehler beim Senden der Telemetrie: {e}")
            self._handle_api_error(str(e))

    def _handle_success(self):
        """Behandle erfolgreiche Übertragung."""
        self._consecutive_errors = 0
        self._current_backoff = INITIAL_BACKOFF_SECONDS
        self._last_successful_send = time.time()
        self._total_sends += 1
        
        # Falls pausiert war, wieder aktivieren
        if self._is_paused:
            _LOGGER.info("ABRP Telemetry: Übertragung wiederhergestellt")
            self._is_paused = False

    def _handle_soft_error(self, reason: str):
        """Behandle weichen Fehler (z.B. fehlende Daten)."""
        # Soft Errors erhöhen den Fehlerzähler nicht so stark
        _LOGGER.debug(f"Soft Error: {reason}")

    def _handle_network_error(self, reason: str):
        """Behandle Netzwerkfehler mit Backoff."""
        self._consecutive_errors += 1
        self._total_errors += 1
        
        if self._consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            self._pause_with_backoff(f"Netzwerkfehler: {reason}")

    def _handle_api_error(self, reason: str):
        """Behandle API-Fehler."""
        self._consecutive_errors += 1
        self._total_errors += 1
        
        if self._consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
            self._pause_with_backoff(f"API-Fehler: {reason}")

    def _handle_critical_error(self, reason: str):
        """Behandle kritische Fehler (z.B. Auth-Fehler) - sofort pausieren."""
        _LOGGER.error(f"Kritischer Fehler: {reason} - Service wird pausiert")
        self._is_paused = True
        self._total_errors += 1
        # Bei Auth-Fehlern längere Pause
        self._schedule_resume(600)  # 10 Minuten

    def _handle_rate_limit(self):
        """Behandle Rate Limiting."""
        self._pause_with_backoff("Rate Limit erreicht")

    def _pause_with_backoff(self, reason: str):
        """Pausiere Service mit exponentiellem Backoff."""
        self._is_paused = True
        
        _LOGGER.warning(
            f"ABRP Telemetry pausiert für {self._current_backoff}s "
            f"nach {self._consecutive_errors} aufeinanderfolgenden Fehlern. "
            f"Grund: {reason}"
        )
        
        # Resume nach Backoff-Zeit planen
        self._schedule_resume(self._current_backoff)
        
        # Backoff erhöhen für nächstes Mal
        self._current_backoff = min(
            self._current_backoff * ERROR_BACKOFF_MULTIPLIER,
            MAX_BACKOFF_SECONDS
        )

    def _schedule_resume(self, seconds: int):
        """Plane Wiederaufnahme nach Pause."""
        async def resume():
            await asyncio.sleep(seconds)
            if self._is_paused:
                _LOGGER.info(f"ABRP Telemetry: Versuche Wiederaufnahme nach {seconds}s Pause")
                self._is_paused = False
        
        asyncio.create_task(resume())

    def get_status(self) -> dict:
        """Gibt den aktuellen Status des Services zurück."""
        return {
            "is_enabled": self._is_enabled,
            "is_running": self._is_enabled and not self._is_paused and self._session is not None,
            "is_paused": self._is_paused,
            "consecutive_errors": self._consecutive_errors,
            "total_sends": self._total_sends,
            "total_errors": self._total_errors,
            "last_successful_send": self._last_successful_send,
            "current_backoff_seconds": self._current_backoff,
        }

"""Config flow for ABRP Telemetry integration."""
import logging
from typing import Any
import aiohttp
import async_timeout

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_USER_TOKEN,
    CONF_CAR_MODEL,
    CONF_UPDATE_INTERVAL,
    CONF_SOC_ENTITY,
    CONF_SPEED_ENTITY,
    CONF_POSITION_ENTITY,
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

CARMODELS_API_URL = "https://api.iternio.com/1/tlm/get_carmodels_list"


class ABRPTelemetryConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ABRP Telemetry."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._data = {}
        self._car_models = {}  # {display_name: car_model_id}
        self._manufacturers = {}  # {manufacturer: {model_display: model_id}}

    async def _fetch_car_models(self) -> dict[str, str]:
        """Fetch car models from ABRP API."""
        try:
            async with async_timeout.timeout(30):
                async with aiohttp.ClientSession() as session:
                    async with session.get(CARMODELS_API_URL) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get("status") == "ok" and "result" in data:
                                # Convert list of {name: id} dicts to single dict
                                car_models = {}
                                for item in data["result"]:
                                    for name, model_id in item.items():
                                        car_models[name] = model_id
                                return car_models
        except Exception as e:
            _LOGGER.warning("Failed to fetch car models from ABRP API: %s", e)
        return {}

    def _parse_manufacturers(self, car_models: dict[str, str]) -> dict[str, dict[str, str]]:
        """Parse car models into manufacturer -> models structure.
        
        Input format: {"Mercedes-Benz;EQA;250 (alpha)": "mercedes:eqa:21:67"}
        Output: {"Mercedes-Benz": {"EQA 250 (alpha)": "mercedes:eqa:21:67"}}
        """
        manufacturers = {}
        
        for display_name, model_id in car_models.items():
            parts = display_name.split(";")
            if len(parts) >= 2:
                manufacturer = parts[0].strip()
                # Combine remaining parts as model name
                model_name = " ".join(parts[1:]).strip()
            else:
                # Fallback for entries without semicolon
                manufacturer = "Other"
                model_name = display_name
            
            if manufacturer not in manufacturers:
                manufacturers[manufacturer] = {}
            manufacturers[manufacturer][model_name] = model_id
        
        return manufacturers

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        """Step 1: API credentials and update interval."""
        errors = {}

        if user_input is not None:
            if not user_input.get(CONF_API_KEY):
                errors[CONF_API_KEY] = "api_key_required"
            elif not user_input.get(CONF_USER_TOKEN):
                errors[CONF_USER_TOKEN] = "user_token_required"
            
            if not errors:
                self._data.update(user_input)
                # Fetch car models for next step
                self._car_models = await self._fetch_car_models()
                self._manufacturers = self._parse_manufacturers(self._car_models)
                return await self.async_step_manufacturer()

        data_schema = vol.Schema({
            vol.Required(CONF_API_KEY): str,
            vol.Required(CONF_USER_TOKEN): str,
            vol.Required(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5,
                    max=60,
                    step=1,
                    unit_of_measurement="s",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_manufacturer(self, user_input: dict[str, Any] | None = None):
        """Step 2: Select manufacturer."""
        errors = {}

        if user_input is not None:
            selected = user_input.get("manufacturer")
            if not selected:
                errors["manufacturer"] = "manufacturer_required"
            else:
                self._data["_selected_manufacturer"] = selected
                return await self.async_step_car_model()

        # Build manufacturer selector (sorted alphabetically)
        if self._manufacturers:
            sorted_manufacturers = sorted(self._manufacturers.keys())
            data_schema = vol.Schema({
                vol.Required("manufacturer"): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=sorted_manufacturers,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        sort=False,  # Already sorted
                    )
                ),
            })
        else:
            # Fallback to text input if API failed
            data_schema = vol.Schema({
                vol.Required("manufacturer"): str,
            })

        return self.async_show_form(
            step_id="manufacturer",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_car_model(self, user_input: dict[str, Any] | None = None):
        """Step 3: Select car model."""
        errors = {}
        selected_manufacturer = self._data.get("_selected_manufacturer", "")

        if user_input is not None:
            selected = user_input.get(CONF_CAR_MODEL)
            if not selected:
                errors[CONF_CAR_MODEL] = "car_model_required"
            else:
                # Get the model ID from manufacturer's models
                if selected_manufacturer in self._manufacturers:
                    models = self._manufacturers[selected_manufacturer]
                    if selected in models:
                        self._data[CONF_CAR_MODEL] = models[selected]
                    else:
                        # Manual input - use as-is
                        self._data[CONF_CAR_MODEL] = selected
                else:
                    self._data[CONF_CAR_MODEL] = selected
                
                # Clean up temporary data
                self._data.pop("_selected_manufacturer", None)
                return await self.async_step_entities_basic()

        # Build model selector for selected manufacturer (sorted alphabetically)
        if selected_manufacturer in self._manufacturers:
            models = self._manufacturers[selected_manufacturer]
            sorted_models = sorted(models.keys())
            data_schema = vol.Schema({
                vol.Required(CONF_CAR_MODEL): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=sorted_models,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        custom_value=True,  # Allow manual entry
                        sort=False,  # Already sorted
                    )
                ),
            })
        else:
            # Fallback to text input
            data_schema = vol.Schema({
                vol.Required(CONF_CAR_MODEL): str,
            })

        return self.async_show_form(
            step_id="car_model",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "manufacturer": selected_manufacturer,
                "car_models_url": "https://api.iternio.com/1/tlm/get_carmodels_list"
            }
        )

    async def async_step_entities_basic(self, user_input: dict[str, Any] | None = None):
        """Step 3: Basic entity mappings."""
        errors = {}

        if user_input is not None:
            if not user_input.get(CONF_SOC_ENTITY):
                errors[CONF_SOC_ENTITY] = "soc_entity_required"
            
            if not errors:
                self._data.update(user_input)
                return await self.async_step_entities_advanced()

        data_schema = vol.Schema({
            # Required
            vol.Required(CONF_SOC_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            # Optional basic entities
            vol.Optional(CONF_SPEED_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_POSITION_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["device_tracker", "sensor"])
            ),
            vol.Optional(CONF_POWER_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_CHARGING_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "binary_sensor"])
            ),
            vol.Optional(CONF_RANGE_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_ODOMETER_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
        })

        return self.async_show_form(
            step_id="entities_basic",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_entities_advanced(self, user_input: dict[str, Any] | None = None):
        """Step 4: Advanced entity mappings (optional)."""
        if user_input is not None:
            self._data.update(user_input)
            # Continue to fixed values step
            return await self.async_step_fixed_values()

        data_schema = vol.Schema({
            vol.Optional(CONF_SOH_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_VOLTAGE_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_CURRENT_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_BATT_TEMP_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
            vol.Optional(CONF_EXT_TEMP_ENTITY): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
        })

        return self.async_show_form(
            step_id="entities_advanced",
            data_schema=data_schema,
        )

    async def async_step_fixed_values(self, user_input: dict[str, Any] | None = None):
        """Step 5: Fixed values for parameters without sensors."""
        if user_input is not None:
            # Only store non-zero values
            if user_input.get(CONF_SOH_FIXED, 0) > 0:
                self._data[CONF_SOH_FIXED] = user_input[CONF_SOH_FIXED]
            if user_input.get(CONF_CAPACITY_FIXED, 0) > 0:
                self._data[CONF_CAPACITY_FIXED] = user_input[CONF_CAPACITY_FIXED]
            
            # Create entry with all collected data
            car_model = self._data.get(CONF_CAR_MODEL, "EV")
            # Find display name for title if possible
            display_name = car_model
            for name, model_id in self._car_models.items():
                if model_id == car_model:
                    # Shorten the display name for the title
                    parts = name.split(";")
                    display_name = f"{parts[0]} {parts[1]}" if len(parts) > 1 else parts[0]
                    break
            
            return self.async_create_entry(
                title=f"ABRP ({display_name})",
                data=self._data
            )

        data_schema = vol.Schema({
            vol.Optional(CONF_SOH_FIXED, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(CONF_CAPACITY_FIXED, default=0): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=200,
                    step=0.1,
                    unit_of_measurement="kWh",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        })

        return self.async_show_form(
            step_id="fixed_values",
            data_schema=data_schema,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return ABRPTelemetryOptionsFlow()


class ABRPTelemetryOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for ABRP Telemetry."""

    def __init__(self):
        """Initialize options flow."""
        self._data = {}

    def _get_entity_value(self, entity_id: str) -> str:
        """Get the current value of an entity."""
        if not entity_id:
            return "—"
        state = self.hass.states.get(entity_id)
        if state is None:
            return "nicht gefunden"
        if state.state in ("unknown", "unavailable"):
            return state.state
        # Include unit if available
        unit = state.attributes.get("unit_of_measurement", "")
        return f"{state.state} {unit}".strip()

    def _build_current_values_text(self, entities: list[tuple[str, str]]) -> str:
        """Build a formatted text showing current entity values."""
        lines = []
        for label, entity_key in entities:
            entity_id = self.config_entry.data.get(entity_key, "")
            if entity_id:
                value = self._get_entity_value(entity_id)
                lines.append(f"• {label}: **{value}**")
        return "\n".join(lines) if lines else "Keine Entitäten konfiguriert"

    async def async_step_init(self, user_input=None):
        """Step 1: Basic settings and required entities."""
        errors = {}
        
        # Initialize _data from config_entry on first call
        if not self._data:
            self._data = dict(self.config_entry.data)
        
        if user_input is not None:
            if not user_input.get(CONF_SOC_ENTITY):
                errors[CONF_SOC_ENTITY] = "soc_entity_required"
            
            if not errors:
                self._data.update(user_input)
                return await self.async_step_options_advanced()

        # Get current values from config
        current = self.config_entry.data
        
        # Build current values display
        current_values = self._build_current_values_text([
            ("SOC", CONF_SOC_ENTITY),
            ("Speed", CONF_SPEED_ENTITY),
            ("Position", CONF_POSITION_ENTITY),
            ("Power", CONF_POWER_ENTITY),
            ("Charging", CONF_CHARGING_ENTITY),
            ("Range", CONF_RANGE_ENTITY),
            ("Odometer", CONF_ODOMETER_ENTITY),
        ])

        # Build schema dynamically - only set default for entities that have values
        schema_dict = {
            vol.Required(
                CONF_UPDATE_INTERVAL,
                default=current.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=5,
                    max=60,
                    step=1,
                    unit_of_measurement="s",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Required(
                CONF_SOC_ENTITY,
                default=current.get(CONF_SOC_ENTITY, "")
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor")
            ),
        }
        
        # Optional entities - only set default if value exists (empty string causes validation error)
        optional_entities = [
            (CONF_SPEED_ENTITY, "sensor"),
            (CONF_POSITION_ENTITY, ["device_tracker", "sensor"]),
            (CONF_POWER_ENTITY, "sensor"),
            (CONF_CHARGING_ENTITY, ["sensor", "binary_sensor"]),
            (CONF_RANGE_ENTITY, "sensor"),
            (CONF_ODOMETER_ENTITY, "sensor"),
        ]
        
        for key, domain in optional_entities:
            entity_id = current.get(key)
            if entity_id:
                schema_dict[vol.Optional(key, default=entity_id)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=domain)
                )
            else:
                schema_dict[vol.Optional(key)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=domain)
                )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_dict),
            errors=errors,
            description_placeholders={"current_values": current_values},
        )

    async def async_step_options_advanced(self, user_input=None):
        """Step 2: Advanced entity mappings."""
        if user_input is not None:
            self._data.update(user_input)
            # Continue to fixed values step
            return await self.async_step_options_fixed()

        # Get current values from config
        current = self.config_entry.data
        
        # Build current values display for advanced entities
        current_values = self._build_current_values_text([
            ("SOH", CONF_SOH_ENTITY),
            ("Voltage", CONF_VOLTAGE_ENTITY),
            ("Current", CONF_CURRENT_ENTITY),
            ("Battery Temp", CONF_BATT_TEMP_ENTITY),
            ("Ext Temp", CONF_EXT_TEMP_ENTITY),
        ])

        # Build schema dynamically - only set default for entities that have values
        schema_dict = {}
        optional_entities = [
            (CONF_SOH_ENTITY, "sensor"),
            (CONF_VOLTAGE_ENTITY, "sensor"),
            (CONF_CURRENT_ENTITY, "sensor"),
            (CONF_BATT_TEMP_ENTITY, "sensor"),
            (CONF_EXT_TEMP_ENTITY, "sensor"),
        ]
        
        for key, domain in optional_entities:
            entity_id = current.get(key)
            if entity_id:
                schema_dict[vol.Optional(key, default=entity_id)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=domain)
                )
            else:
                schema_dict[vol.Optional(key)] = selector.EntitySelector(
                    selector.EntitySelectorConfig(domain=domain)
                )

        return self.async_show_form(
            step_id="options_advanced",
            data_schema=vol.Schema(schema_dict),
            description_placeholders={"current_values": current_values},
        )

    async def async_step_options_fixed(self, user_input=None):
        """Step 3: Fixed values for parameters without sensors."""
        if user_input is not None:
            # Only store non-zero values, remove zero values
            if user_input.get(CONF_SOH_FIXED, 0) > 0:
                self._data[CONF_SOH_FIXED] = user_input[CONF_SOH_FIXED]
            else:
                self._data.pop(CONF_SOH_FIXED, None)
            
            if user_input.get(CONF_CAPACITY_FIXED, 0) > 0:
                self._data[CONF_CAPACITY_FIXED] = user_input[CONF_CAPACITY_FIXED]
            else:
                self._data.pop(CONF_CAPACITY_FIXED, None)
            
            # Update the config entry with new data
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=self._data
            )
            return self.async_create_entry(title="", data={})

        # Get current values from config
        current = self.config_entry.data
        
        # Build current values display
        lines = []
        soh_val = current.get(CONF_SOH_FIXED, 0)
        if soh_val and soh_val > 0:
            lines.append(f"• SOH (fixed): **{soh_val}%**")
        cap_val = current.get(CONF_CAPACITY_FIXED, 0)
        if cap_val and cap_val > 0:
            lines.append(f"• Capacity (fixed): **{cap_val} kWh**")
        current_values = "\n".join(lines) if lines else "No fixed values configured"

        data_schema = vol.Schema({
            vol.Optional(
                CONF_SOH_FIXED,
                default=current.get(CONF_SOH_FIXED, 0)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Optional(
                CONF_CAPACITY_FIXED,
                default=current.get(CONF_CAPACITY_FIXED, 0)
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=200,
                    step=0.1,
                    unit_of_measurement="kWh",
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        })

        return self.async_show_form(
            step_id="options_fixed",
            data_schema=data_schema,
            description_placeholders={"current_values": current_values},
        )

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
                return await self.async_step_car_model()

        data_schema = vol.Schema({
            vol.Required(CONF_API_KEY): str,
            vol.Required(CONF_USER_TOKEN): str,
            vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): vol.All(
                vol.Coerce(int), vol.Range(min=5, max=60)
            ),
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_car_model(self, user_input: dict[str, Any] | None = None):
        """Step 2: Select car model."""
        errors = {}

        if user_input is not None:
            selected = user_input.get(CONF_CAR_MODEL)
            if not selected:
                errors[CONF_CAR_MODEL] = "car_model_required"
            else:
                # Store the car model ID (not the display name)
                if selected in self._car_models:
                    self._data[CONF_CAR_MODEL] = self._car_models[selected]
                else:
                    # Manual input - use as-is
                    self._data[CONF_CAR_MODEL] = selected
                return await self.async_step_entities_basic()

        # Build car model selector
        if self._car_models:
            # Create sorted list of display names
            sorted_models = sorted(self._car_models.keys())
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
            # Fallback to text input if API failed
            data_schema = vol.Schema({
                vol.Required(CONF_CAR_MODEL): str,
            })

        return self.async_show_form(
            step_id="car_model",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
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

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return ABRPTelemetryOptionsFlow(config_entry)


class ABRPTelemetryOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for ABRP Telemetry."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=60)),
            })
        )

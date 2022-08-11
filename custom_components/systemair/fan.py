"""Support for the Systemair ventilation unit fan."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from math import ceil, floor
from typing import Any, Callable, NamedTuple

from homeassistant.components.climate.const import FAN_OFF
from homeassistant.components.fan import (FanEntity, FanEntityFeature,
                                          NotValidPresetModeError)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from systemair.saveconnect.const import Airflow

from . import SaveConnectDevice
from .const import (DOMAIN, SAVECONNECT_AIRFLOW_TO_STR_SETTABLE,
                    SAVECONNECT_DEVICES, SAVECONNECT_FAN_MODES,
                    SAVECONNECT_MODE_TO_STR_SETTABLE, SAVECONNECT_NAME,
                    STR_TO_SAVECONNECT_PROFILE_SETTABLE)

_LOGGER = logging.getLogger(__name__)


class ExtraStateAttributeDetails(NamedTuple):
    """Extra state attribute details."""

    description: str
    data_fn: Callable


EXTRA_STATE_ATTRIBUTES = (
    ExtraStateAttributeDetails(
        description="fan_speed", data_fn=lambda device: device.state.airflow_level
    ),
)


def _convert_fan_speed_value(value: StateType) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    return None


async def async_setup_entry(
        hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the fan device."""
    entry_config = hass.data[DOMAIN][entry.entry_id]

    sc_devices = entry_config.get(SAVECONNECT_DEVICES)

    devices = [SaveConnectDeviceFan(device=x) for x in sc_devices]

    async_add_entities(devices)


class SaveConnectDeviceFan(CoordinatorEntity, FanEntity):
    """Representation of the fan."""

    def __init__(
            self,
            device: SaveConnectDevice
    ) -> None:
        """Initialize the fan."""
        super().__init__(device.coordinator)

        self._device = device

        self._attr_name = "Ventilation"
        self._attr_unique_id = f"{SAVECONNECT_NAME}-{device.device_id}-fan"
        self._attr_supported_features = FanEntityFeature.PRESET_MODE | FanEntityFeature.SET_SPEED
        self._attr_has_entity_name = True

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed of the fan, as a percentage."""
        step_size = 100 / self.speed_count
        option = ceil(percentage / step_size)

        value = SAVECONNECT_FAN_MODES[option]

        success = await self._device.async_set_fan_mode(value)
        if not success:
            _LOGGER.error("Error setting fan level to: %s", value)

        await self.coordinator.async_request_refresh()

    @property
    def percentage(self) -> int | None:
        """Return the current speed as a percentage."""
        fan_speed = self.airflow_state
        index = SAVECONNECT_FAN_MODES.index(fan_speed)

        percentage = int(index * self.percentage_step)

        return percentage

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return len(SAVECONNECT_FAN_MODES) - 1

    @property
    def preset_modes(self) -> list[str]:
        """Return a list of available preset modes."""
        # Use the Vallox profile names for the preset names.
        return list(STR_TO_SAVECONNECT_PROFILE_SETTABLE.keys())

    @property
    def is_on(self) -> bool:
        """Return if device is on."""
        return self.airflow_state != FAN_OFF

    @property
    def airflow_state(self):
        airflow_level_value = self._device.state.airflow_level

        if airflow_level_value is None:
            self._attr_available = False
            return None

        self._attr_available = True
        return SAVECONNECT_AIRFLOW_TO_STR_SETTABLE[airflow_level_value]

    @property
    def preset_state(self):
        return self._device.state.user_mode

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""

        user_mode = self.preset_state

        return SAVECONNECT_MODE_TO_STR_SETTABLE.get(user_mode)

    @property
    def extra_state_attributes(self) -> Mapping[str, int | None]:
        """Return device specific state attributes."""
        # data = self.coordinator.data

        return {
            attr.description: attr.data_fn(self._device)
            for attr in EXTRA_STATE_ATTRIBUTES
        }

    async def _async_set_preset_mode_internal(self, preset_mode: str) -> bool:
        """
        Set new preset mode.
        Returns true if the mode has been changed, false otherwise.
        """
        try:
            self._valid_preset_mode_or_raise(preset_mode)

        except NotValidPresetModeError as err:
            _LOGGER.error(err)
            return False

        if preset_mode == self.preset_mode:
            return False

        success = await self._device.async_set_mode(STR_TO_SAVECONNECT_PROFILE_SETTABLE[preset_mode])
        if not success:
            _LOGGER.error("Error setting preset to: %s", preset_mode)
            return False

        return True

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        update_needed = await self._async_set_preset_mode_internal(preset_mode)

        if update_needed:
            # This state change affects other entities like sensors. Force an immediate update that
            # can be observed by all parties involved.
            await self.coordinator.async_request_refresh()

    async def async_turn_on(
            self,
            percentage: int | None = None,
            preset_mode: str | None = None,
            **kwargs: Any,
    ) -> None:
        """Turn the device on."""
        _LOGGER.debug("Turn on")

        if not self.is_on:
            success = await self._device.async_set_fan_mode(Airflow.LOW)
            if not success:
                _LOGGER.error("Error turning on device.")
                return

            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        if not self.is_on:
            return

        success = await self._device.async_set_fan_mode(Airflow.OFF)
        if not success:
            _LOGGER.error("Error turning off device.")
            return

        await self.coordinator.async_request_refresh()

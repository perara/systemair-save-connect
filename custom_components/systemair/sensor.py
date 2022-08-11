"""Platform for Systemair sensor integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (SensorDeviceClass, SensorEntity,
                                             SensorEntityDescription,
                                             SensorStateClass)
from homeassistant.const import PERCENTAGE, TEMP_CELSIUS, TEMP_FAHRENHEIT
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN, SAVECONNECT_DEVICES, SaveConnectDevice
from .const import (SAVECONNECT_NAME, SAVECONNECT_UNITS_CELSIUS,
                    SAVECONNECT_UNITS_FAHRENHEIT)


@dataclass
class SaveConnectRequiredKeysMixin:
    """Mixin for required keys."""
    value_fn: Callable[[Any], float]
    enabled: Callable[[Any], bool]


@dataclass
class SaveConnectSensorEntityDescription(
    SensorEntityDescription, SaveConnectRequiredKeysMixin
):
    """Describes SaveConnect sensor entities."""


SENSORS: tuple[SaveConnectSensorEntityDescription, ...] = (

    SaveConnectSensorEntityDescription(
        key="internal_relative_humidity",
        name="Internal Relative Humidity",
        icon="mdi:temperature-celsius",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.HUMIDITY,
        value_fn=lambda device: float(device.registry.REG_SENSOR_RHS_PDM.value),
        enabled=lambda device: True,
        entity_registry_enabled_default=True,
    ),

    SaveConnectSensorEntityDescription(
        key="internal_extract_temperature",
        name="Internal Extract Temperature",
        icon="mdi:temperature-celsius",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: int(device.registry.REG_SENSOR_PDM_EAT_VALUE.value) / 10.0,
        enabled=lambda device: True,
        entity_registry_enabled_default=True,
    ),

    SaveConnectSensorEntityDescription(
        key="outdoor_temperature",
        name="Outdoor Temperature",
        icon="mdi:temperature-celsius",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: int(device.registry.REG_SENSOR_OAT.value) / 10.0,
        enabled=lambda device: True,
        entity_registry_enabled_default=True,
    ),

    SaveConnectSensorEntityDescription(
        key="overheating_temperature",
        name="Overheating Temperature",
        icon="mdi:temperature-celsius",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: int(device.registry.REG_SENSOR_OHT.value) / 10.0,
        enabled=lambda device: True,
        entity_registry_enabled_default=True,
    ),

    SaveConnectSensorEntityDescription(
        key="supply_temperature",
        name="Supply Temperature",
        icon="mdi:temperature-celsius",
        native_unit_of_measurement=TEMP_CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        value_fn=lambda device: int(device.registry.REG_SENSOR_SAT.value) / 10.0,
        enabled=lambda device: True,
        entity_registry_enabled_default=True,
    ),
)


async def async_setup_entry(hass, entry, async_add_entities: AddEntitiesCallback):
    """Add sensors for passed config_entry in HA."""
    entry_config = hass.data[DOMAIN][entry.entry_id]

    sc_devices = entry_config.get(SAVECONNECT_DEVICES)
    entities = []
    entities.extend([
        SaveConnectDeviceSensor(sc_device, description)
        for description in SENSORS
        for sc_device in sc_devices
        if description.enabled(sc_device)
    ])

    async_add_entities(entities)


class SaveConnectDeviceSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Sensor."""

    entity_description: SaveConnectSensorEntityDescription

    def __init__(
            self,
            device: SaveConnectDevice,
            description: SaveConnectSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(device.coordinator)
        self._device: SaveConnectDevice = device

        self._attr_name = f"{description.name}"
        self._attr_unique_id = f"{SAVECONNECT_NAME}-{device.device_id}-{description.key}"

        """Determine which unit metric to use on the sensor in the case of temperature."""
        if description.device_class == SensorDeviceClass.TEMPERATURE:
            sc_temp_units = self._device.device.units.temperature

            if sc_temp_units == SAVECONNECT_UNITS_CELSIUS:
                description.native_unit_of_measurement = TEMP_CELSIUS
                description.icon = "mdi:temperature-celsius"
            elif sc_temp_units == SAVECONNECT_UNITS_FAHRENHEIT:
                description.native_unit_of_measurement = TEMP_FAHRENHEIT
                description.icon = "mdi:temperature-fahrenheit"

        self.entity_description = description

    @property
    def native_value(self):
        """Return the state of the sensor."""
        try:
            value = self.entity_description.value_fn(self._device)
            self._attr_available = True
            return value
        except AttributeError:
            self._attr_available = False
            return None

    @property
    def device_info(self):
        """Return a device description for device registry."""
        return self._device.device_info

    @property
    def extra_state_attributes(self):
        """Return the optional state attributes."""
        return self._device.extra_attributes


def try_parse(value, t):
    try:
        return t(value)
    except Exception:
        return t()

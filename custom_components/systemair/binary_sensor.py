"""Platform for binary_sensor in the Systemair SAVE Connect integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from custom_components.systemair import SaveConnectDevice
from custom_components.systemair.const import (DOMAIN,
                                                           SAVECONNECT_DEVICES,
                                                           SAVECONNECT_NAME)
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity


@dataclass
class SaveConnectRequiredKeysMixin:
    """Mixin for required keys."""
    value_fn: Callable


@dataclass
class SaveConnectBinaryEntityDescription(
    SensorEntityDescription, SaveConnectRequiredKeysMixin
):
    """Describes SaveConnect sensor entities."""


async def async_setup_entry(hass, entry, async_add_entities: AddEntitiesCallback):
    """Add sensors for passed config_entry in HA."""
    entry_config = hass.data[DOMAIN][entry.entry_id]

    sc_devices = entry_config.get(SAVECONNECT_DEVICES)

    binary_sensor_descriptions: list[SaveConnectBinaryEntityDescription, ...] = []
    for device in sc_devices:
        """Retrieve all alarm_ prefixed sensor names."""
        sensor_names = [x for x in dir(device.state) if x.startswith("alarm_")]

        for sensor_key in sensor_names:
            def wrap(dev, key):
                return lambda: getattr(dev.state, key) == 'active'

            binary_sensor_descriptions.append(SaveConnectBinaryEntityDescription(
                key=sensor_key,
                name=' '.join([x.capitalize() for x in sensor_key.split("_")]),
                value_fn=wrap(device, sensor_key),
                entity_registry_enabled_default=True,
            )
            )

    entities = [
        SaveConnectDeviceSensor(sc_device, description)
        for description in binary_sensor_descriptions
        for sc_device in sc_devices
    ]

    async_add_entities(entities)


class SaveConnectDeviceSensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a BinarySensor."""

    entity_description: SaveConnectBinaryEntityDescription

    def __init__(
            self,
            device: SaveConnectDevice,
            description: SaveConnectBinaryEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(device.coordinator)
        self._device: SaveConnectDevice = device

        self._attr_has_entity_name = True
        self._attr_name = f"{description.name}"
        self._attr_unique_id = f"{SAVECONNECT_NAME}-{device.device_id}-{description.key}"
        self.entity_description = description

    @property
    def is_on(self):
        return self.entity_description.value_fn()

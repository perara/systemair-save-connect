"""The Systemair Save Connect integration."""
from __future__ import annotations


import dataclasses
import logging
from datetime import timedelta
from typing import Iterable, Optional

from homeassistant.auth.providers.homeassistant import InvalidAuth
from homeassistant.components.air_quality import SCAN_INTERVAL
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_EMAIL, Platform, ATTR_MODEL, ATTR_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from systemair.saveconnect import SaveConnect
from systemair.saveconnect.const import UserModes, Airflow
from systemair.saveconnect.models import SaveConnectDevice as ExtSaveConnectDevice
from systemair.saveconnect.register import Register
from .config_flow import CannotConnect
from .const import DOMAIN, HA_SC_AUTHENTICATION_INTERVAL, HA_SC_CLOUD_PUSH, SAVECONNECT_DEVICES


from .util import is_min_ha_version

_LOGGER = logging.getLogger(__name__)

MANUFACTURER = "Systemair"
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

PLATFORMS: list[str] = [Platform.SENSOR, Platform.FAN, Platform.BINARY_SENSOR]


async def async_setup_entity_platforms(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        platforms: Iterable[Platform | str],
) -> None:
    """Set up entity platforms using new method from HA version 2022.8."""
    if is_min_ha_version(2022, 8):
        await hass.config_entries.async_forward_entry_setups(config_entry, platforms)
    else:
        hass.config_entries.async_setup_platforms(config_entry, platforms)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Establish connection with SaveConnect API."""
    api = SaveConnect(
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
        ws_enabled=entry.data[HA_SC_CLOUD_PUSH],
        refresh_token_interval=0,
        loop=hass.loop
    )

    """Authenticate to the SaveConnect API"""
    try:
        await async_auth_login(api)
    except (InvalidAuth, CannotConnect) as e:
        _LOGGER.error("Could not authenticate to SaveConnect. Got exception: %s", e)
        return False

    """Retrieve Device data."""
    sc_devices = await save_connect_device_setup(hass, api)

    hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {}).update(
        {
            SAVECONNECT_DEVICES: sc_devices,
        }
    )
    await async_setup_entity_platforms(hass, entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok


async def async_auth_login(api: SaveConnect):
    """Authenticate towards the SaveConnect API."""
    auth_result = await api.login()
    if not auth_result:
        raise InvalidAuth


async def save_connect_device_setup(hass: HomeAssistant, api: SaveConnect):
    sc_devices = await api.get_devices(update=True, fetch_device_info=False)
    for device in sc_devices:
        await api.update_device_info([device])

    devices = [SaveConnectDevice(
        device=device,
        api=api
    ) for device in sc_devices]

    for device in devices:
        await device.async_create_coordinator(hass)

    return devices


@dataclasses.dataclass
class SaveConnectDeviceData:
    device_model: str = None

    user_mode: str = None
    airflow_level: str = None

    main_board_version_major: int = None
    main_board_version_minor: int = None
    main_board_version_build: int = None

    iam_version_major: int = None
    iam_version_minor: int = None
    iam_version_build: int = None

    alarm_supply_air_fan_control: bool = False
    alarm_extract_air_fan_control: bool = False
    alarm_frost_protection: bool = False
    alarm_defrosting_malfunction: bool = False
    alarm_supply_air_fan_rpm: bool = False
    alarm_extract_air_fan_rpm: bool = False
    alarm_frost_protection_sensor: bool = False
    alarm_outdoor_air_temperature_sensor: bool = False
    alarm_supply_air_temperature_sensor: bool = False
    alarm_room_air_temperature_sensor: bool = False
    alarm_extract_air_temperature_sensor: bool = False
    alarm_extra_controller_temperature: bool = False
    alarm_efficiency_temperature: bool = False
    alarm_overheat_temperature: bool = False
    alarm_emergency_thermostat: bool = False
    alarm_rotor_guard_sensor: bool = False
    alarm_bypass_damper_malfunction: bool = False
    alarm_secondary_air_damper_position: bool = False
    alarm_filter_change: bool = False
    alarm_extra_controller_malfunction: bool = False
    alarm_external_stop: bool = False
    alarm_relative_humidity_sensor: bool = False
    alarm_co2_sensor: bool = False
    alarm_supply_air_temperature_low: bool = False
    alarm_bypass_damper_feedback: bool = False
    alarm_builtin_relative_humidity_sensor: bool = False
    alarm_builtin_extract_air_temperature: bool = False
    alarm_manual_stop: bool = False
    alarm_overheat_temperature2: bool = False
    alarm_fire_alarm: bool = False
    alarm_filter_warning: bool = False


    @property
    def iam_version(self):
        return f"{self.iam_version_major}.{self.iam_version_minor}.{self.iam_version_build}"

    @property
    def main_board_version(self):
        return f"{self.main_board_version_major}.{self.main_board_version_minor}.{self.main_board_version_build}"


class SaveConnectDevice:
    """SaveConnect Device instance."""

    def __init__(self, device: ExtSaveConnectDevice, api: SaveConnect):
        self.state = SaveConnectDeviceData()
        self.device = device

        """Add sensor callback."""
        self.device.add_update_callback(self.set_update_callback)

        """Populate state data."""
        self.populate_state_data(device)

        """Set name attribute."""
        self.name: Optional[str] = f"{MANUFACTURER} {self.device_model}"

        """Set SaveConnect attribute."""
        self.api: SaveConnect = api

        """counter to indicate if the device is available."""
        self._available = 0

        """Number of errors before device is unavailable."""
        self._available_threshold = 30

        """The coordinator object."""
        self._coordinator: DataUpdateCoordinator | None = None

        """Extra attributes for the device."""
        self._extra_attributes = {}

    def populate_state_data(self, device):
        for attr in device.registry.dict().keys():
            register = getattr(device.registry, attr)
            if not register:
                continue
            self.set_update_callback(register.register_, register.value, register)

    def set_update_callback(self, register, value, metadata):
        """When API returns data, the register values are sent to this callback."""
        if register in [Register.REG_USERMODE_MODE_HMI, Register.REG_USERMODE_HMI_CHANGE_REQUEST]:
            self.state.user_mode = value
        elif register in [Register.REG_USERMODE_MANUAL_AIRFLOW_LEVEL_SAF, Register.REG_SPEED_INDICATION_APP]:
            self.state.airflow_level = value
        elif register == Register.REG_SYSTEM_UNIT_MODEL1:
            self.state.device_model = value
        elif register == Register.REG_PU_RUNNING_VERSION_MAJOR:
            if metadata.internalDeviceType == 1:
                self.state.main_board_version_major = value
            elif metadata.internalDeviceType == 2:
                self.state.iam_version_major = value
        elif register == Register.REG_PU_RUNNING_VERSION_MINOR:
            if metadata.internalDeviceType == 1:
                self.state.main_board_version_minor = value
            elif metadata.internalDeviceType == 2:
                self.state.iam_version_minor = value
        elif register == Register.REG_PU_RUNNING_VERSION_BUILD:
            if metadata.internalDeviceType == 1:
                self.state.main_board_version_build = value
            elif metadata.internalDeviceType == 2:
                self.state.iam_version_build = value
        elif register == Register.REG_ALARM_SAF_CTRL_ALARM:
            self.state.alarm_supply_air_fan_control = value
        elif register == Register.REG_ALARM_EAF_CTRL_ALARM:
            self.state.alarm_extract_air_fan_control = value
        elif register == Register.REG_ALARM_FROST_PROT_ALARM:
            self.state.alarm_frost_protection = value
        elif register == Register.REG_ALARM_DEFROSTING_ALARM:
            self.state.alarm_defrosting_malfunction = value
        elif register == Register.REG_ALARM_SAF_RPM_ALARM:
            self.state.alarm_supply_air_fan_rpm = value
        elif register == Register.REG_ALARM_EAF_RPM_ALARM:
            self.state.alarm_extract_air_fan_rpm = value
        elif register == Register.REG_ALARM_FPT_ALARM:
            self.state.alarm_frost_protection_sensor = value
        elif register == Register.REG_ALARM_OAT_ALARM:
            self.state.alarm_outdoor_air_temperature_sensor = value
        elif register == Register.REG_ALARM_SAT_ALARM:
            self.state.alarm_supply_air_temperature_sensor = value
        elif register == Register.REG_ALARM_RAT_ALARM:
            self.state.alarm_room_air_temperature_sensor = value
        elif register == Register.REG_ALARM_EAT_ALARM:
            self.state.alarm_extract_air_temperature_sensor = value
        elif register == Register.REG_ALARM_ECT_ALARM:
            self.state.alarm_extra_controller_temperature = value
        elif register == Register.REG_ALARM_EFT_ALARM:
            self.state.alarm_efficiency_temperature = value
        elif register == Register.REG_ALARM_OHT_ALARM:
            self.state.alarm_overheat_temperature = value
        elif register == Register.REG_ALARM_EMT_ALARM:
            self.state.alarm_emergency_thermostat = value
        elif register == Register.REG_ALARM_RGS_ALARM:
            self.state.alarm_rotor_guard_sensor = value
        elif register == Register.REG_ALARM_BYS_ALARM:
            self.state.alarm_bypass_damper_malfunction = value
        elif register == Register.REG_ALARM_SECONDARY_AIR_ALARM:
            self.state.alarm_secondary_air_damper_position = value
        elif register == Register.REG_ALARM_FILTER_ALARM:
            self.state.alarm_filter_change = value
        elif register == Register.REG_ALARM_EXTRA_CONTROLLER_ALARM:
            self.state.alarm_extra_controller_malfunction = value
        elif register == Register.REG_ALARM_EXTERNAL_STOP_ALARM:
            self.state.alarm_external_stop = value
        elif register == Register.REG_ALARM_RH_ALARM:
            self.state.alarm_relative_humidity_sensor = value
        elif register == Register.REG_ALARM_CO2_ALARM:
            self.state.alarm_co2_sensor = value
        elif register == Register.REG_ALARM_LOW_SAT_ALARM:
            self.state.alarm_supply_air_temperature_low = value
        elif register == Register.REG_ALARM_BYF_ALARM:
            self.state.alarm_bypass_damper_feedback = value
        elif register == Register.REG_ALARM_PDM_RHS_ALARM:
            self.state.alarm_builtin_relative_humidity_sensor = value
        elif register == Register.REG_ALARM_PDM_EAT_ALARM:
            self.state.alarm_builtin_extract_air_temperature = value
        elif register == Register.REG_ALARM_MANUAL_FAN_STOP_ALARM:
            self.state.alarm_manual_stop = value
        elif register == Register.REG_ALARM_OVERHEAT_TEMPERATURE_ALARM:
            self.state.alarm_overheat_temperature2 = value
        elif register == Register.REG_ALARM_FIRE_ALARM_ALARM:
            self.state.alarm_fire_alarm = value
        elif register == Register.REG_ALARM_FILTER_WARNING_ALARM:
            self.state.alarm_filter_warning = value

    @property
    def registry(self):
        return self.device.registry

    @property
    def device_model(self):
        return self.state.device_model

    async def _async_update(self):
        """Pull the latest data from SaveConnect API."""
        success = await self.device.update(self.api)

        if success:
            self._available = 0
        else:
            _LOGGER.warning("Update failed for %s", self.name)
            self._available += 1

    async def async_create_coordinator(self, hass: HomeAssistant) -> None:
        """Get the coordinator for a specific device."""
        if self._coordinator:
            return

        coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=f"{DOMAIN}-{self.name or self.device_id}",
            update_method=self._async_update,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=SCAN_INTERVAL,
        )

        #
        await coordinator.async_refresh()

        self._coordinator = coordinator

    @property
    def coordinator(self) -> DataUpdateCoordinator | None:
        """Return coordinator associated."""
        return self._coordinator

    async def async_set_fan_mode(self, mode: Airflow):
        return await self.api.user_mode.set_airflow(self.device, mode)

    async def async_set_mode(self, mode: UserModes) -> bool:
        return await self.api.user_mode.set_mode(self.device, mode, duration=60)  # TODO duration

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        print(self._available, self._available <= self._available_threshold)
        return self._available <= self._available_threshold

    @property
    def device_id(self):
        """Return device ID."""
        return self.device.identifier

    @property
    def device_info(self) -> DeviceInfo:
        """Return a device description for device registry."""
        _device_info = DeviceInfo(
            identifiers={(DOMAIN, self.device_id)},
            manufacturer=MANUFACTURER,
            name=self.name
        )
        _device_info[ATTR_MODEL] = f"{MANUFACTURER} ({self.device.identifier})"
        _device_info[ATTR_DEVICE_ID] = self.device.identifier

        return _device_info

    @property
    def extra_attributes(self):
        return {
            "main_board_version": self.state.main_board_version,
            "iam_version": self.state.iam_version
        }

"""Constants for the Systemair integration."""

from homeassistant.components.climate.const import FAN_HIGH, FAN_LOW, FAN_OFF
from systemair.saveconnect.const import Airflow, UserModes

DOMAIN = "systemair"

HA_SC_AUTHENTICATION_INTERVAL = 300
HA_SC_CLOUD_PUSH = "cloud_push"

HA_SC_CLOUD_PUSH_DEFAULT = True

SAVECONNECT_DEVICES = "saveconnect_devices"
SAVECONNECT_NAME = "SAVE Connect"
SAVECONNECT_UNITS_FAHRENHEIT = "UNITS_FAHRENHEIT"
SAVECONNECT_UNITS_CELSIUS = "UNITS_CELSIUS"
SAVECONNECT_FAN_MINIMUM = "minimum"
SAVECONNECT_FAN_MAXIMUM = "maximum"
SAVECONNECT_FAN_MODES = [FAN_OFF, FAN_LOW, "normal", FAN_HIGH]


SAVECONNECT_AIRFLOW_TO_STR_SETTABLE = {
    Airflow.OFF: Airflow.OFF,
    Airflow.MINIMUM: Airflow.LOW,
    Airflow.NORMAL: Airflow.NORMAL,
    Airflow.HIGH: Airflow.HIGH,
    Airflow.MAXIMUM: Airflow.HIGH
}

SAVECONNECT_MODE_TO_STR_SETTABLE = {
    UserModes.AUTO: "Auto",
    UserModes.MANUAL: "Manual",
    UserModes.AWAY: "Away",
    UserModes.CROWDED: "Crowded",
    UserModes.FIREPLACE: "Fireplace",
    UserModes.HOLIDAY: "Holiday"
}

STR_TO_SAVECONNECT_PROFILE_SETTABLE = {
    value: key for (key, value) in SAVECONNECT_MODE_TO_STR_SETTABLE.items()
}

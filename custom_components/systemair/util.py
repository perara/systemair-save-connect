from homeassistant.const import MAJOR_VERSION, MINOR_VERSION


def is_min_ha_version(min_ha_major_ver: int, min_ha_minor_ver: int) -> bool:
    """Check if HA version at least a specific version."""
    return (
            MAJOR_VERSION > min_ha_major_ver or
            (MAJOR_VERSION == min_ha_major_ver and MINOR_VERSION >= min_ha_minor_ver)
    )


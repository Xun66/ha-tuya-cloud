"""Tuya sharing MQTT support for the currently supported meter device."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import CONF_TOKEN_INFO, DOMAIN, PLATFORMS
from .coordinator import TuyaCloudAuthError, TuyaCloudCoordinator, TuyaCloudHub


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Set up Tuya Cloud from a config entry."""
    if CONF_TOKEN_INFO not in entry.data:
        raise ConfigEntryAuthFailed("Tuya QR login is required")

    hass.data.setdefault(DOMAIN, {})
    hub = TuyaCloudHub(hass, entry)
    coordinator = TuyaCloudCoordinator(hass, hub)
    try:
        await coordinator.async_start()
    except TuyaCloudAuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: TuyaCloudCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.hub.async_unload()
    return unload_ok


async def async_remove_entry(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Remove a config entry."""
    coordinator: TuyaCloudCoordinator | None = hass.data.get(DOMAIN, {}).get(
        entry.entry_id
    )
    if coordinator is not None:
        await coordinator.hub.async_remove()


async def _async_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)

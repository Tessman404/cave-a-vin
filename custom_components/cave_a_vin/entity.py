"""Entité de base : toutes les entités sont rattachées à l'appareil « Tessvine »."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CaveCoordinator


class CaveEntity(CoordinatorEntity[CaveCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: CaveCoordinator, cle: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{cle}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Tessvine",
            model="Gestion de cave",
            sw_version=(coordinator.data or {}).get("version"),
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=coordinator.api.url,
        )

"""Rafraîchissement périodique des données de la cave."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CaveApi, CaveApiError, CaveAuthError
from .const import DOMAIN, INTERVALLE

_LOGGER = logging.getLogger(__name__)

type CaveConfigEntry = ConfigEntry[CaveCoordinator]


class CaveCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Récupère en un appel le résumé de la cave, plus la liste d'envies."""

    config_entry: CaveConfigEntry

    def __init__(self, hass: HomeAssistant, entry: CaveConfigEntry, api: CaveApi) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=INTERVALLE)
        self.api = api

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            resume = await self.api.resume()
            resume["liste_envies"] = await self.api.envies()
        except CaveAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except CaveApiError as err:
            raise UpdateFailed(str(err)) from err
        return resume

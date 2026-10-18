"""Ajout de la cave depuis l'interface de Home Assistant."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_URL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.hassio import HassioServiceInfo

from .api import CaveApi, CaveApiError, CaveAuthError
from .const import CONF_API_KEY, DOMAIN


def _normaliser(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    return url


class CaveConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._decouverte: dict[str, Any] = {}

    async def _tester(self, url: str, api_key: str | None) -> str | None:
        """Renvoie un code d'erreur, ou None si la cave répond."""
        api = CaveApi(async_get_clientsession(self.hass), url, api_key)
        try:
            await api.sante()
            await api.resume()  # vérifie aussi la clé d'API
        except CaveAuthError:
            return "invalid_auth"
        except CaveApiError:
            return "cannot_connect"
        return None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        erreurs: dict[str, str] = {}
        if user_input is not None:
            url = _normaliser(user_input[CONF_URL])
            await self.async_set_unique_id(url)
            self._abort_if_unique_id_configured()
            if not (erreur := await self._tester(url, user_input.get(CONF_API_KEY))):
                return self.async_create_entry(
                    title="Tessvine", data={CONF_URL: url, CONF_API_KEY: user_input.get(CONF_API_KEY, "")})
            erreurs["base"] = erreur
        schema = vol.Schema({
            vol.Required(CONF_URL, default=(user_input or {}).get(CONF_URL, "http://")): str,
            vol.Optional(CONF_API_KEY): str,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=erreurs)

    async def async_step_hassio(self, discovery_info: HassioServiceInfo) -> ConfigFlowResult:
        """Découverte automatique par le module complémentaire Tessvine."""
        config = discovery_info.config
        url = f"http://{config['host']}:{config['port']}"
        await self.async_set_unique_id(url)
        self._abort_if_unique_id_configured(updates={CONF_URL: url, CONF_API_KEY: config.get("api_key", "")})
        self._decouverte = {CONF_URL: url, CONF_API_KEY: config.get("api_key", "")}
        return await self.async_step_hassio_confirm()

    async def async_step_hassio_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        erreurs: dict[str, str] = {}
        if user_input is not None:
            if not (erreur := await self._tester(self._decouverte[CONF_URL], self._decouverte[CONF_API_KEY])):
                return self.async_create_entry(title="Tessvine", data=self._decouverte)
            erreurs["base"] = erreur
        return self.async_show_form(step_id="hassio_confirm", errors=erreurs)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entree = self._get_reauth_entry()
        erreurs: dict[str, str] = {}
        if user_input is not None:
            cle = user_input.get(CONF_API_KEY, "")
            if not (erreur := await self._tester(entree.data[CONF_URL], cle)):
                return self.async_update_reload_and_abort(entree, data_updates={CONF_API_KEY: cle})
            erreurs["base"] = erreur
        return self.async_show_form(step_id="reauth_confirm", errors=erreurs,
                                    data_schema=vol.Schema({vol.Optional(CONF_API_KEY): str}))

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entree = self._get_reconfigure_entry()
        erreurs: dict[str, str] = {}
        if user_input is not None:
            url = _normaliser(user_input[CONF_URL])
            cle = user_input.get(CONF_API_KEY, entree.data.get(CONF_API_KEY, ""))
            if not (erreur := await self._tester(url, cle)):
                return self.async_update_reload_and_abort(
                    entree, unique_id=url, data_updates={CONF_URL: url, CONF_API_KEY: cle})
            erreurs["base"] = erreur
        schema = vol.Schema({
            vol.Required(CONF_URL, default=entree.data[CONF_URL]): str,
            vol.Optional(CONF_API_KEY): str,
        })
        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=erreurs)

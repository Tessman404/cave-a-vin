"""Intégration Home Assistant pour l'application Cave à vin."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_URL, Platform
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import CaveApi, CaveApiError
from .const import CONF_API_KEY, COULEURS, DOMAIN, PLATS, RAISONS_ENTREE, RAISONS_SORTIE
from .coordinator import CaveConfigEntry, CaveCoordinator

PLATFORMS = [Platform.SENSOR, Platform.TODO]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

ATTR_ENTRY = "config_entry_id"

SCHEMA_SORTIE = vol.Schema({
    vol.Optional(ATTR_ENTRY): cv.string,
    vol.Required("vin_id"): vol.Coerce(int),
    vol.Optional("quantite", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
    vol.Optional("raison", default="bue"): vol.In(RAISONS_SORTIE),
    vol.Optional("note"): vol.All(vol.Coerce(float), vol.Range(min=0, max=5)),
    vol.Optional("commentaire", default=""): cv.string,
})
SCHEMA_ENTREE = vol.Schema({
    vol.Optional(ATTR_ENTRY): cv.string,
    vol.Required("vin_id"): vol.Coerce(int),
    vol.Optional("quantite", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=500)),
    vol.Optional("raison", default="achat"): vol.In(RAISONS_ENTREE),
})
SCHEMA_SUGGESTION = vol.Schema({
    vol.Optional(ATTR_ENTRY): cv.string,
    vol.Optional("plat"): vol.In(PLATS),
    vol.Optional("couleur"): vol.In(COULEURS),
    vol.Optional("nombre", default=3): vol.All(vol.Coerce(int), vol.Range(min=1, max=20)),
})
SCHEMA_RECHERCHE = vol.Schema({
    vol.Optional(ATTR_ENTRY): cv.string,
    vol.Required("recherche"): cv.string,
    vol.Optional("inclure_epuises", default=False): cv.boolean,
})


def _resume_vin(vin: dict[str, Any]) -> dict[str, Any]:
    return {
        "vin_id": vin["id"],
        "nom": vin["nom"],
        "millesime": vin.get("millesime"),
        "domaine": vin.get("domaine") or None,
        "appellation": vin.get("appellation") or None,
        "region": vin.get("region") or None,
        "couleur": vin.get("couleur"),
        "bouteilles": vin.get("stock"),
        "garde": vin.get("statut_label"),
        "a_boire_avant": vin.get("garde_fin"),
    }


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Déclare les actions (services) de la cave."""

    def coordinateur(call: ServiceCall) -> CaveCoordinator:
        entry_id = call.data.get(ATTR_ENTRY)
        entrees = [
            e for e in hass.config_entries.async_entries(DOMAIN)
            if e.state is ConfigEntryState.LOADED and (not entry_id or e.entry_id == entry_id)
        ]
        if not entrees:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="pas_de_cave",
            )
        return entrees[0].runtime_data

    async def appeler(coro):
        try:
            return await coro
        except CaveApiError as err:
            raise HomeAssistantError(str(err)) from err

    async def sortir_bouteille(call: ServiceCall) -> ServiceResponse:
        coord = coordinateur(call)
        champs = {k: call.data[k] for k in ("quantite", "raison", "note", "commentaire") if k in call.data}
        vin = await appeler(coord.api.sortir(call.data["vin_id"], **champs))
        await coord.async_refresh()
        return _resume_vin(vin)

    async def ajouter_bouteilles(call: ServiceCall) -> ServiceResponse:
        coord = coordinateur(call)
        vin = await appeler(coord.api.ajouter(call.data["vin_id"], quantite=call.data["quantite"],
                                              raison=call.data["raison"]))
        await coord.async_refresh()
        return _resume_vin(vin)

    async def suggerer_vin(call: ServiceCall) -> ServiceResponse:
        coord = coordinateur(call)
        res = await appeler(coord.api.suggestion(plat=call.data.get("plat"), couleur=call.data.get("couleur"),
                                                 limite=call.data["nombre"]))
        return {"suggestions": [{**_resume_vin(s["vin"]), "pourquoi": ", ".join(s["raisons"])} for s in res]}

    async def rechercher_vin(call: ServiceCall) -> ServiceResponse:
        coord = coordinateur(call)
        vins = await appeler(coord.api.vins(q=call.data["recherche"],
                                            stock="all" if call.data["inclure_epuises"] else "1"))
        return {"vins": [_resume_vin(v) for v in vins[:25]]}

    hass.services.async_register(DOMAIN, "sortir_bouteille", sortir_bouteille, SCHEMA_SORTIE,
                                 supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, "ajouter_bouteilles", ajouter_bouteilles, SCHEMA_ENTREE,
                                 supports_response=SupportsResponse.OPTIONAL)
    hass.services.async_register(DOMAIN, "suggerer_vin", suggerer_vin, SCHEMA_SUGGESTION,
                                 supports_response=SupportsResponse.ONLY)
    hass.services.async_register(DOMAIN, "rechercher_vin", rechercher_vin, SCHEMA_RECHERCHE,
                                 supports_response=SupportsResponse.ONLY)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: CaveConfigEntry) -> bool:
    api = CaveApi(async_get_clientsession(hass), entry.data[CONF_URL], entry.data.get(CONF_API_KEY))
    coordinator = CaveCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CaveConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

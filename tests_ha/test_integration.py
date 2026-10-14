"""Tests de l'intégration Home Assistant, contre une vraie instance de l'application."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.components.todo import DOMAIN as TODO_DOMAIN
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.service_info.hassio import HassioServiceInfo

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.cave_a_vin.const import CONF_API_KEY, DOMAIN


async def _installer(hass: HomeAssistant, url: str) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="Cave à vin", unique_id=url, data={CONF_URL: url, CONF_API_KEY: ""})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _etat(hass: HomeAssistant, cle: str):
    reg = er.async_get(hass)
    entity_id = next(e.entity_id for e in reg.entities.values() if e.unique_id.endswith("_" + cle))
    return hass.states.get(entity_id)


async def test_ajout_manuel(hass: HomeAssistant, cave_url: str) -> None:
    res = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert res["type"] is FlowResultType.FORM
    res = await hass.config_entries.flow.async_configure(res["flow_id"], {CONF_URL: "http://127.0.0.1:1"})
    assert res["errors"] == {"base": "cannot_connect"}
    res = await hass.config_entries.flow.async_configure(res["flow_id"], {CONF_URL: cave_url.replace("http://", "")})
    assert res["type"] is FlowResultType.CREATE_ENTRY
    assert res["data"][CONF_URL] == cave_url
    await hass.async_block_till_done()


async def test_decouverte_par_le_module(hass: HomeAssistant, cave_url: str) -> None:
    hote, port = cave_url.removeprefix("http://").split(":")
    info = HassioServiceInfo(config={"host": hote, "port": int(port), "api_key": ""}, name="Cave à vin",
                             slug="cave_a_vin", uuid="1234")
    res = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_HASSIO}, data=info)
    assert res["step_id"] == "hassio_confirm"
    res = await hass.config_entries.flow.async_configure(res["flow_id"], {})
    assert res["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()


async def test_capteurs_actions_et_envies(hass: HomeAssistant, cave_url: str) -> None:
    await _installer(hass, cave_url)
    assert _etat(hass, "bouteilles").state == "5"
    assert _etat(hass, "valeur").state == "130.0"
    assert _etat(hass, "references").state == "2"
    assert _etat(hass, "rangement_1").state == "3"
    assert _etat(hass, "rangement_1").attributes["places_libres"] == 17
    assert _etat(hass, "rangement_aucun").state == "2"
    assert _etat(hass, "bouteilles").attributes["par_couleur"] == {"Rouge": 3, "Blanc": 2}

    rep = await hass.services.async_call(DOMAIN, "rechercher_vin", {"recherche": "chablis"},
                                         blocking=True, return_response=True)
    vin_id = rep["vins"][0]["vin_id"]
    rep = await hass.services.async_call(DOMAIN, "sortir_bouteille",
                                         {"vin_id": vin_id, "note": 4, "commentaire": "Iodé"},
                                         blocking=True, return_response=True)
    assert rep["bouteilles"] == 1
    await hass.async_block_till_done()
    assert _etat(hass, "bouteilles").state == "4"
    assert _etat(hass, "dernier_mouvement").state == "−1 Chablis"
    assert _etat(hass, "dernier_mouvement").attributes["note"] == 4

    rep = await hass.services.async_call(DOMAIN, "suggerer_vin", {"plat": "fruits_de_mer"},
                                         blocking=True, return_response=True)
    assert [s["nom"] for s in rep["suggestions"]] == ["Chablis"]

    await hass.services.async_call(DOMAIN, "ajouter_bouteilles", {"vin_id": vin_id, "quantite": 6}, blocking=True)
    await hass.async_block_till_done()
    assert _etat(hass, "bouteilles").state == "10"

    envies = _etat(hass, "envies")
    assert envies.state == "1"
    await hass.services.async_call(TODO_DOMAIN, "add_item", {"item": "Vin jaune"},
                                   target={"entity_id": envies.entity_id}, blocking=True)
    await hass.services.async_call(TODO_DOMAIN, "update_item", {"item": "Meursault", "status": "completed"},
                                   target={"entity_id": envies.entity_id}, blocking=True)
    await hass.async_block_till_done()
    assert _etat(hass, "envies").state == "1"  # « Vin jaune » à faire, « Meursault » fait
    rep = await hass.services.async_call(TODO_DOMAIN, "get_items", {}, target={"entity_id": envies.entity_id},
                                         blocking=True, return_response=True)
    assert sorted(i["summary"] for i in rep[envies.entity_id]["items"]) == ["Meursault", "Vin jaune"]


async def test_dechargement(hass: HomeAssistant, cave_url: str) -> None:
    entry = await _installer(hass, cave_url)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

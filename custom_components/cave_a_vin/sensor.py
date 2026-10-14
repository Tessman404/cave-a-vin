"""Capteurs de la cave : bouteilles, valeur, vins à boire…"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import CaveConfigEntry, CaveCoordinator
from .entity import CaveEntity

PARALLEL_UPDATES = 0
MAX_LISTE = 20


def _liste(vins: list[dict[str, Any]]) -> list[str]:
    return [
        f"{v['nom']}{' ' + str(v['millesime']) if v.get('millesime') else ''} (×{v['stock']}"
        f"{', avant ' + str(v['garde_fin']) if v.get('garde_fin') else ''})"
        for v in vins[:MAX_LISTE]
    ]


def _par(lignes: list[dict[str, Any]]) -> dict[str, int]:
    return {str(l["label"]): l["bouteilles"] for l in lignes}


def _dernier(d: dict[str, Any]) -> str | None:
    m = (d.get("derniers_mouvements") or [None])[0]
    if not m:
        return None
    signe = "+" if m["type"] == "entree" else "−"
    return f"{signe}{m['quantite']} {m['vin_nom']}{' ' + str(m['millesime']) if m.get('millesime') else ''}"[:255]


def _attr_dernier(d: dict[str, Any]) -> dict[str, Any]:
    m = (d.get("derniers_mouvements") or [None])[0]
    if not m:
        return {}
    return {k: m.get(k) for k in ("type", "vin_id", "vin_nom", "millesime", "quantite", "raison", "note",
                                  "commentaire", "date")}


@dataclass(frozen=True, kw_only=True)
class CaveSensorDescription(SensorEntityDescription):
    valeur: Callable[[dict[str, Any]], Any]
    attributs: Callable[[dict[str, Any]], dict[str, Any]] | None = None


CAPTEURS: tuple[CaveSensorDescription, ...] = (
    CaveSensorDescription(
        key="bouteilles", translation_key="bouteilles", native_unit_of_measurement="bouteilles",
        state_class=SensorStateClass.MEASUREMENT,
        valeur=lambda d: d["bouteilles"],
        attributs=lambda d: {"par_couleur": _par(d["par_couleur"]), "par_cave": {c["nom"]: c["bouteilles"] for c in d["par_cave"]},
                             "par_garde": {l["label"]: l["bouteilles"] for l in d["par_statut"] if l["bouteilles"]}},
    ),
    CaveSensorDescription(
        key="references", translation_key="references", native_unit_of_measurement="vins",
        state_class=SensorStateClass.MEASUREMENT, valeur=lambda d: d["references"],
    ),
    CaveSensorDescription(
        key="valeur", translation_key="valeur", device_class=SensorDeviceClass.MONETARY,
        native_unit_of_measurement="EUR", state_class=SensorStateClass.TOTAL, suggested_display_precision=0,
        valeur=lambda d: d["valeur"],
    ),
    CaveSensorDescription(
        key="a_boire", translation_key="a_boire", native_unit_of_measurement="bouteilles",
        state_class=SensorStateClass.MEASUREMENT,
        valeur=lambda d: sum(v["stock"] for v in d["a_boire"]),
        attributs=lambda d: {"vins": _liste(d["a_boire"])},
    ),
    CaveSensorDescription(
        key="a_boire_vite", translation_key="a_boire_vite", native_unit_of_measurement="bouteilles",
        state_class=SensorStateClass.MEASUREMENT,
        valeur=lambda d: sum(v["stock"] for v in d["urgents"]),
        attributs=lambda d: {"vins": _liste(d["urgents"]),
                             "ids": [v["id"] for v in d["urgents"][:MAX_LISTE]]},
    ),
    CaveSensorDescription(
        key="bues_annee", translation_key="bues_annee", native_unit_of_measurement="bouteilles",
        state_class=SensorStateClass.TOTAL, valeur=lambda d: d["bues_annee"],
        attributs=lambda d: {"annee": d["annee"], "sorties_ce_mois": d["sorties_mois"], "entrees_ce_mois": d["entrees_mois"]},
    ),
    CaveSensorDescription(
        key="dernier_mouvement", translation_key="dernier_mouvement",
        valeur=_dernier, attributs=_attr_dernier,
    ),
)


async def async_setup_entry(hass: HomeAssistant, entry: CaveConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    coordinator = entry.runtime_data
    async_add_entities(CaveSensor(coordinator, d) for d in CAPTEURS)

    # Un capteur par cave (casier, armoire…), y compris celles créées plus tard.
    connues: set[Any] = set()

    @callback
    def ajouter_caves() -> None:
        nouvelles = [c for c in (coordinator.data or {}).get("par_cave", []) if c["id"] not in connues]
        for c in nouvelles:
            connues.add(c["id"])
        if nouvelles:
            async_add_entities(CaveRangementSensor(coordinator, c["id"], c["nom"]) for c in nouvelles)

    ajouter_caves()
    entry.async_on_unload(coordinator.async_add_listener(ajouter_caves))


class CaveSensor(CaveEntity, SensorEntity):
    entity_description: CaveSensorDescription

    def __init__(self, coordinator: CaveCoordinator, description: CaveSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.valeur(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attributs is None:
            return None
        return self.entity_description.attributs(self.coordinator.data)


class CaveRangementSensor(CaveEntity, SensorEntity):
    """Nombre de bouteilles dans une cave donnée (ou « non rangées »)."""

    _attr_native_unit_of_measurement = "bouteilles"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:bottle-wine"

    def __init__(self, coordinator: CaveCoordinator, cave_id: int | None, nom: str) -> None:
        super().__init__(coordinator, f"rangement_{cave_id if cave_id is not None else 'aucun'}")
        self._cave_id = cave_id
        self._attr_name = nom

    def _cave(self) -> dict[str, Any] | None:
        return next((c for c in (self.coordinator.data or {}).get("par_cave", []) if c["id"] == self._cave_id), None)

    @property
    def available(self) -> bool:
        # Les bouteilles « non rangées » disparaissent du résumé quand il n'y en a plus : on affiche alors 0.
        return super().available and (self._cave() is not None or self._cave_id is None)

    @property
    def native_value(self) -> int:
        cave = self._cave()
        return cave["bouteilles"] if cave else 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        cave = self._cave()
        if not cave or not cave["capacite"]:
            return {}
        return {"capacite": cave["capacite"], "places_libres": cave["capacite"] - cave["bouteilles"],
                "taux_remplissage": round(100 * cave["bouteilles"] / cave["capacite"])}

"""Client de l'API HTTP de la cave."""

from __future__ import annotations

from typing import Any

import aiohttp


class CaveApiError(Exception):
    """Erreur renvoyée par la cave ou cave injoignable."""


class CaveAuthError(CaveApiError):
    """Clé d'API manquante ou invalide."""


class CaveApi:
    """Accès à l'application Cave à vin."""

    def __init__(self, session: aiohttp.ClientSession, url: str, api_key: str | None = None) -> None:
        self._session = session
        self.url = url.rstrip("/")
        self._api_key = api_key or ""

    async def _requete(self, methode: str, chemin: str, json: Any = None, params: dict | None = None) -> Any:
        entetes = {"X-API-Key": self._api_key} if self._api_key else {}
        try:
            async with self._session.request(
                methode, f"{self.url}/api/{chemin}", json=json, params=params, headers=entetes,
                timeout=aiohttp.ClientTimeout(total=15),
            ) as rep:
                if rep.status == 401:
                    raise CaveAuthError("Clé d'API invalide")
                data = await rep.json(content_type=None)
                if rep.status >= 400:
                    raise CaveApiError((data or {}).get("erreur") or f"Erreur HTTP {rep.status}")
                return data
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise CaveApiError(f"Cave injoignable : {err}") from err

    async def sante(self) -> dict:
        return await self._requete("GET", "health")

    async def resume(self) -> dict:
        return await self._requete("GET", "ha/resume")

    async def envies(self) -> list[dict]:
        return await self._requete("GET", "envies")

    async def creer_envie(self, nom: str, details: str = "") -> dict:
        return await self._requete("POST", "envies", {"nom": nom, "details": details})

    async def modifier_envie(self, envie_id: int, **champs: Any) -> dict:
        return await self._requete("PUT", f"envies/{envie_id}", champs)

    async def supprimer_envie(self, envie_id: int) -> None:
        await self._requete("DELETE", f"envies/{envie_id}")

    async def sortir(self, vin_id: int, **champs: Any) -> dict:
        return await self._requete("POST", f"vins/{vin_id}/sortie", champs)

    async def ajouter(self, vin_id: int, **champs: Any) -> dict:
        return await self._requete("POST", f"vins/{vin_id}/entree", champs)

    async def filtre_remplace(self, cave_id: int, date: str | None = None) -> dict:
        return await self._requete("POST", f"caves/{cave_id}/filtre", {"date": date} if date else {})

    async def suggestion(self, **params: Any) -> list[dict]:
        return await self._requete("GET", "suggestion", params={k: v for k, v in params.items() if v is not None})

    async def vins(self, **params: Any) -> list[dict]:
        return await self._requete("GET", "vins", params={k: v for k, v in params.items() if v is not None})

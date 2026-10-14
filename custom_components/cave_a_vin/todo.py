"""Liste « Envies » de la cave, sous forme de liste de tâches Home Assistant (compatible Assist)."""

from __future__ import annotations

from homeassistant.components.todo import TodoItem, TodoItemStatus, TodoListEntity, TodoListEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import CaveApiError
from .coordinator import CaveConfigEntry, CaveCoordinator
from .entity import CaveEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass: HomeAssistant, entry: CaveConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    async_add_entities([CaveEnvies(entry.runtime_data)])


class CaveEnvies(CaveEntity, TodoListEntity):
    _attr_translation_key = "envies"
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(self, coordinator: CaveCoordinator) -> None:
        super().__init__(coordinator, "envies")

    @property
    def todo_items(self) -> list[TodoItem]:
        return [
            TodoItem(
                uid=str(e["id"]),
                summary=e["nom"],
                description=e["details"] or None,
                status=TodoItemStatus.COMPLETED if e["fait"] else TodoItemStatus.NEEDS_ACTION,
            )
            for e in self.coordinator.data.get("liste_envies", [])
        ]

    async def _executer(self, coro) -> None:
        try:
            await coro
        except CaveApiError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_refresh()

    async def async_create_todo_item(self, item: TodoItem) -> None:
        await self._executer(self.coordinator.api.creer_envie(item.summary or "", item.description or ""))

    async def async_update_todo_item(self, item: TodoItem) -> None:
        await self._executer(self.coordinator.api.modifier_envie(
            int(item.uid), nom=item.summary, details=item.description or "",
            fait=item.status == TodoItemStatus.COMPLETED,
        ))

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        for uid in uids:
            await self._executer(self.coordinator.api.supprimer_envie(int(uid)))

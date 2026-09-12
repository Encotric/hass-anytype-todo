# Copyright (c) 2026 Sebastian Wilke
"""Todo platform for Anytype ToDo."""

from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn, cast

from homeassistant.components.todo import (
    TodoItem,
    TodoListEntity,
)
from homeassistant.components.todo.const import TodoItemStatus, TodoListEntityFeature
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError

from .anytype import AnytypeMarkdownTodoItem, AnytypeMarkdownToDoPage
from .entity import AnytypeEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import AnytypeDataUpdateCoordinator
    from .data import AnytypeConfigEntry


def _raise_todo_error(message: str) -> NoReturn:
    raise HomeAssistantError(message)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: AnytypeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Anytype ToDo platform."""
    client = entry.runtime_data.client

    at_object = await client.async_get_object(
        space_id=entry.runtime_data.space_id, object_id=entry.runtime_data.object_id
    )

    page = AnytypeMarkdownToDoPage(at_object["object"]["markdown"])

    entities: list[AnytypeTodoListEntity] = [
        AnytypeTodoListEntity(
            coordinator=entry.runtime_data.coordinator,
            space_id=entry.runtime_data.space_id,
            object_id=entry.runtime_data.object_id,
            name=list_name.name,
        )
        for list_name in page.lists
    ]

    async_add_entities(entities)


class AnytypeTodoListEntity(AnytypeEntity, TodoListEntity):
    """Todo list entity backed by an Anytype object section."""

    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    markdown_page: AnytypeMarkdownToDoPage

    def __init__(
        self,
        coordinator: AnytypeDataUpdateCoordinator,
        space_id: str,
        object_id: str,
        name: str,
    ) -> None:
        """Initialize the todo list entity."""
        super().__init__(coordinator)
        self._attr_name = name
        self._attr_has_entity_name = True
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{space_id}_{name}_list"
        )
        self._space_id = space_id
        self._object_id = object_id

        self._todos: list[TodoItem] = []

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        page: AnytypeMarkdownToDoPage = self.coordinator.data["page"]
        todo_list = (
            page.get_list(self._attr_name) if self._attr_name is not None else None
        )

        if todo_list is None:
            message = f"Error fetching todos: list {self._attr_name} not found."
            _raise_todo_error(message)

        self._todos = []
        for item in todo_list.items:
            self._todos.append(item.convert_to_hass())

        self.markdown_page = page
        self.async_update_listeners()

    @property
    def todo_items(self) -> list[TodoItem]:
        """Return the todo items."""
        return self._todos

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Create a new todo item and persist it to Anytype."""
        if item.summary is None:
            return

        idx = len(self._todos)
        item.uid = str(hash((item.summary, item.completed is not None, idx)))
        self._todos.append(item)

        todo_list = self.markdown_page.get_list(cast("str", self._attr_name))
        if todo_list is None:
            return

        todo_list.add_item(
            AnytypeMarkdownTodoItem(
                summary=item.summary, completed=item.completed is not None, idx=idx
            )
        )
        try:
            await self.coordinator.config_entry.runtime_data.client.async_update_object(
                space_id=self._space_id,
                object_id=self._object_id,
                body=self.markdown_page.to_markdown(),
            )
        except Exception as err:
            message = f"Error creating todo: {err}"
            raise HomeAssistantError(message) from err

        self.async_update_listeners()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update an existing todo item and persist it to Anytype."""
        if not item.uid:
            message = "Todo item must have a UID to be updated"
            raise HomeAssistantError(message)

        try:
            todo_list = self.markdown_page.get_list(cast("str", self._attr_name))
            if todo_list is None:
                message = f"Error updating todo: list {self._attr_name} not found."
                _raise_todo_error(message)

            updated_summary = item.summary
            if updated_summary is None:
                existing_item = todo_list.get_item(item.uid)
                if existing_item is None:
                    message = "Todo item not found"
                    _raise_todo_error(message)
                updated_summary = existing_item.summary

            completed: bool | None = None
            if item.status is not None:
                completed = item.status == TodoItemStatus.COMPLETED
            elif item.completed is not None:
                completed = True

            todo_list.update_item(
                item.uid,
                summary=updated_summary,
                completed=completed,
            )

            await self.coordinator.config_entry.runtime_data.client.async_update_object(
                space_id=self._space_id,
                object_id=self._object_id,
                body=self.markdown_page.to_markdown(),
            )
            await self.coordinator.async_request_refresh()
        except Exception as err:
            message = f"Error updating todo: {err}"
            raise HomeAssistantError(message) from err
        self.async_update_listeners()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete todo items and persist the updated markdown."""
        try:
            todo_list = self.markdown_page.get_list(cast("str", self._attr_name))
            if todo_list is None:
                message = f"Error deleting todos: list {self._attr_name} not found."
                _raise_todo_error(message)

            for uid in uids:
                todo_list.remove_item(uid)

            self._todos = [todo for todo in self._todos if todo.uid not in uids]

            await self.coordinator.config_entry.runtime_data.client.async_update_object(
                space_id=self._space_id,
                object_id=self._object_id,
                body=self.markdown_page.to_markdown(),
            )
            await self.coordinator.async_request_refresh()
        except Exception as err:
            message = f"Error deleting todos: {err}"
            raise HomeAssistantError(message) from err
        self.async_update_listeners()

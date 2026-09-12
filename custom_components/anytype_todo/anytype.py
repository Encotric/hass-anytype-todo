# Copyright (c) 2026 Sebastian Wilke
"""Parse and render Anytype markdown pages with to-do lists."""

from typing import Any

import marko
from homeassistant.components.todo import (
    TodoItem,
)
from homeassistant.components.todo.const import TodoItemStatus
from homeassistant.exceptions import HomeAssistantError
from marko.block import Document
from marko.inline import InlineElement
from marko.md_renderer import MarkdownRenderer


class ToDoListItemMarkdown(InlineElement):
    """Represent a markdown checkbox item."""

    pattern = r"\[([ xX])\]\s+(.*)"
    parse_children = False

    def __init__(self, match: Any) -> None:
        """Initialize a checkbox item from a regex match."""
        self.completed = match.group(1) != " "
        self.summary = match.group(2)


class TodoListItemMarkdownRenderer:
    """Render checkbox items back to markdown."""

    def render_to_do_list_item_markdown(self, element: ToDoListItemMarkdown) -> str:
        """Render one checkbox item."""
        return f"[{'x' if element.completed else ' '}] {element.summary}"


todo_extension = marko.MarkoExtension(
    elements=[ToDoListItemMarkdown], renderer_mixins=[TodoListItemMarkdownRenderer]
)


class AnytypeMarkdownTodoItem:
    """Represent one Anytype markdown todo item."""

    summary: str
    completed: bool
    uid: str

    def __init__(self, *, summary: str, completed: bool, idx: int) -> None:
        """Initialize a todo item."""
        self.summary = summary
        self.completed = completed
        self.uid = str(hash((summary, completed, idx)))

    def convert_to_hass(self) -> TodoItem:
        """Convert this item to Home Assistant's todo representation."""
        return TodoItem(
            uid=self.uid,
            summary=self.summary,
            status=TodoItemStatus.COMPLETED
            if self.completed
            else TodoItemStatus.NEEDS_ACTION,
            description=None,
        )


class AnytypeMarkdownTodoList:
    """Represent a named list of Anytype markdown todo items."""

    name: str
    ast_index: int
    items: list[AnytypeMarkdownTodoItem]
    length: int

    def __init__(
        self, name: str, ast_index: int, items: list[AnytypeMarkdownTodoItem]
    ) -> None:
        """Initialize a todo list."""
        self.name = name
        self.ast_index = ast_index
        self.items = items
        self.length = len(items)

    def __len__(self) -> int:
        """Return the number of items in the list."""
        return self.length

    def get_item(self, uid: str) -> AnytypeMarkdownTodoItem | None:
        """Return the item with the given UID, if present."""
        for item in self.items:
            if item.uid == uid:
                return item

        return None

    def remove_item(self, uid: str) -> None:
        """Remove the item with the given UID."""
        item = self.get_item(uid)
        if item is None:
            message = "Todo item not found"
            raise HomeAssistantError(message)
        self.items.remove(item)
        self.length -= 1

    def update_item(
        self,
        uid: str,
        *,
        summary: str | None = None,
        completed: bool | None = None,
    ) -> None:
        """Update an item in place and keep its generated UID in sync."""
        item = self.get_item(uid)
        if item is None:
            message = "Todo item not found"
            raise HomeAssistantError(message)

        idx = self.items.index(item)
        if summary is not None:
            item.summary = summary
        if completed is not None:
            item.completed = completed
        item.uid = str(hash((item.summary, item.completed, idx)))

    def add_item(self, item: AnytypeMarkdownTodoItem) -> None:
        """Append an item to the list."""
        self.items.append(item)
        self.length += 1

    def to_markdown(self) -> str:
        """Render the list as markdown."""
        result = ""
        for item in self.items:
            result += f"- [{'x' if item.completed else ' '}] {item.summary}\n"

        result += "- [ ] \n"
        return result


marko_instance = marko.Markdown(extensions=[todo_extension], renderer=MarkdownRenderer)


class AnytypeMarkdownToDoPage:
    """Represent a parsed Anytype markdown page."""

    lists: list[AnytypeMarkdownTodoList]
    ast: Document

    def __init__(self, markdown: str) -> None:
        """Parse a markdown page and collect its todo lists."""
        self.ast = marko_instance.parse(markdown)
        self.lists = []

        current_list_name: str | None = None
        current_list_index: int | None = None
        current_list_items: list[AnytypeMarkdownTodoItem] = []

        for i, child in enumerate(self.ast.children):
            if child.get_type(snake_case=True) == "heading":
                heading = child.children[0]
                if (
                    heading.get_type(snake_case=True) == "emphasis"
                    or heading.get_type(snake_case=True) == "strong_emphasis"
                ):
                    heading = heading.children[0]

                list_title = heading.children
                if current_list_name is not None and current_list_index is not None:
                    self.lists.append(
                        AnytypeMarkdownTodoList(
                            name=current_list_name,
                            ast_index=current_list_index,
                            items=current_list_items,
                        )
                    )
                    current_list_items = []

                current_list_name = list_title
            if child.get_type(snake_case=True) == "list":
                current_list_index = i
                for idx, item in enumerate(child.children):
                    paragraph = item.children[0]
                    todo_item = paragraph.children[0]
                    summary = todo_item.summary.strip()
                    completed = todo_item.completed
                    if summary != "":
                        current_list_items.append(
                            AnytypeMarkdownTodoItem(
                                summary=summary, completed=completed, idx=idx
                            )
                        )

        if current_list_name is not None and current_list_index is not None:
            self.lists.append(
                AnytypeMarkdownTodoList(
                    name=current_list_name,
                    ast_index=current_list_index,
                    items=current_list_items,
                )
            )

    def get_list(self, name: str) -> AnytypeMarkdownTodoList | None:
        """Return the list with the given name, if present."""
        for todo_list in self.lists:
            if todo_list.name == name:
                return todo_list
        return None

    def to_markdown(self) -> str:
        """Render the page back to markdown."""
        result = ""
        last_ast_index = 0
        for todo_list in self.lists:
            doc = Document()
            doc.children = self.ast.children[last_ast_index : todo_list.ast_index]
            result += marko_instance.render(doc)
            result += todo_list.to_markdown()
            last_ast_index = todo_list.ast_index + 1

        if len(self.ast.children) - 1 > last_ast_index:
            doc = Document()
            doc.children = self.ast.children[last_ast_index:]
            result += marko_instance.render(doc)

        return result

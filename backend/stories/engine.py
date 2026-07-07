"""Story Engine — manages presentation stories from dashboard states."""
from __future__ import annotations
import json
import uuid
from datetime import datetime
from typing import Any


class StoryPoint:
    """A single slide/state in a story."""

    def __init__(
        self,
        title: str,
        description: str = "",
        chart_configs: list[dict[str, Any]] | None = None,
        filter_state: list[dict[str, Any]] | None = None,
        parameter_values: dict[str, Any] | None = None,
    ):
        self.title = title
        self.description = description
        self.chart_configs = chart_configs or []
        self.filter_state = filter_state or []
        self.parameter_values = parameter_values or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "chart_configs": self.chart_configs,
            "filter_state": self.filter_state,
            "parameter_values": self.parameter_values,
        }


class Story:
    """A story containing multiple story points."""

    def __init__(self, title: str, dataset_id: str):
        self.id = uuid.uuid4().hex[:12]
        self.title = title
        self.dataset_id = dataset_id
        self.points: list[StoryPoint] = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

    def add_point(
        self,
        title: str,
        description: str = "",
        chart_configs: list[dict[str, Any]] | None = None,
        filter_state: list[dict[str, Any]] | None = None,
        parameter_values: dict[str, Any] | None = None,
    ) -> StoryPoint:
        point = StoryPoint(title, description, chart_configs, filter_state, parameter_values)
        self.points.append(point)
        self.updated_at = datetime.now().isoformat()
        return point

    def remove_point(self, index: int) -> bool:
        if 0 <= index < len(self.points):
            self.points.pop(index)
            self.updated_at = datetime.now().isoformat()
            return True
        return False

    def reorder_points(self, new_order: list[int]) -> bool:
        """Reorder points by their indices."""
        try:
            self.points = [self.points[i] for i in new_order]
            self.updated_at = datetime.now().isoformat()
            return True
        except (IndexError, TypeError):
            return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "dataset_id": self.dataset_id,
            "points": [p.to_dict() for p in self.points],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class StoryManager:
    """Manages stories — create, read, update, delete."""

    def __init__(self, persist_path: str | None = None):
        self._stories: dict[str, Story] = {}
        self._persist_path = persist_path
        self._load()

    def create(self, title: str, dataset_id: str) -> Story:
        story = Story(title, dataset_id)
        self._stories[story.id] = story
        self._save()
        return story

    def get(self, story_id: str) -> Story | None:
        return self._stories.get(story_id)

    def list_all(self) -> list[dict[str, Any]]:
        return [
            {
                "id": s.id,
                "title": s.title,
                "dataset_id": s.dataset_id,
                "point_count": len(s.points),
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in self._stories.values()
        ]

    def update(self, story_id: str, title: str | None = None) -> Story | None:
        story = self._stories.get(story_id)
        if story and title:
            story.title = title
            story.updated_at = datetime.now().isoformat()
            self._save()
        return story

    def delete(self, story_id: str) -> bool:
        if story_id in self._stories:
            del self._stories[story_id]
            self._save()
            return True
        return False

    def _load(self) -> None:
        if not self._persist_path:
            return
        try:
            with open(self._persist_path) as f:
                data = json.load(f)
                for item in data:
                    story = Story(item["title"], item["dataset_id"])
                    story.id = item["id"]
                    story.created_at = item["created_at"]
                    story.updated_at = item.get("updated_at", item["created_at"])
                    for p in item.get("points", []):
                        story.points.append(StoryPoint(**p))
                    self._stories[story.id] = story
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass

    def _save(self) -> None:
        if not self._persist_path:
            return
        try:
            with open(self._persist_path, "w") as f:
                json.dump(
                    [s.to_dict() for s in self._stories.values()],
                    f,
                    indent=2,
                )
        except Exception:
            pass

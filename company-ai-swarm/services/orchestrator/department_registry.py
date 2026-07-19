"""Department Registry: loads departments/*/definition.yaml.

Source: Specifications/1 - enterprise-architecture/Department Operating Model Specification
(DOMS).md sec.5 (Department Object). Mirrors agent_runtime/registry.py's structure and role
for departments rather than agents.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class DepartmentDefinition(BaseModel):
    id: str
    name: str
    purpose: str = ""
    mission: str = ""
    leader: str = ""
    capabilities: list[str] = Field(default_factory=list)
    agents: list[str] = Field(default_factory=list)
    lifecycle_state: str = "proposed"
    extra: dict[str, Any] = Field(default_factory=dict)


def load_department_definition(path: str | Path) -> DepartmentDefinition:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    data = raw["department"]
    known_fields = {"id", "name", "purpose", "mission", "leader", "capabilities", "agents", "lifecycle_state"}
    extra = {k: v for k, v in data.items() if k not in known_fields}
    return DepartmentDefinition(**{k: v for k, v in data.items() if k in known_fields}, extra=extra)


class DepartmentRegistry:
    def __init__(self, departments_dir: str | Path) -> None:
        self._departments_dir = Path(departments_dir)
        self._departments: dict[str, DepartmentDefinition] = {}

    def load_all(self) -> None:
        for dept_dir in sorted(self._departments_dir.iterdir()):
            definition_file = dept_dir / "definition.yaml"
            if definition_file.exists():
                definition = load_department_definition(definition_file)
                self._departments[definition.id] = definition

    def get(self, department_id: str) -> DepartmentDefinition | None:
        return self._departments.get(department_id)

    def all(self) -> list[DepartmentDefinition]:
        return list(self._departments.values())

    def __len__(self) -> int:
        return len(self._departments)

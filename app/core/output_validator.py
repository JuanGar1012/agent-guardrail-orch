from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


class OutputValidator:
    def __init__(self, schema_path: str = "config/output_schema.json") -> None:
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(schema)

    def validate(self, payload: dict[str, Any]) -> list[str]:
        errors = sorted(self.validator.iter_errors(payload), key=lambda item: item.path)
        return [error.message for error in errors]

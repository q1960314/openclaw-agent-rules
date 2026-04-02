#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lightweight JSON-schema-style validator for worker result payloads.

Current scope intentionally small:
- object / array / string / integer / boolean / number
- required fields
- nested object properties
- array item type checks
- enum checks

This is not a full JSON Schema implementation; it is a deterministic runtime guard
for our worker result envelopes and expert result payloads.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path('/home/admin/.openclaw/workspace/master')
PROTOCOLS = ROOT / 'protocols'


class SimpleSchemaValidator:
    def __init__(self, schema: dict[str, Any]):
        self.schema = schema

    def validate(self, payload: Any) -> list[str]:
        errors: list[str] = []
        self._validate_node(payload, self.schema, '$', errors)
        return errors

    def _validate_node(self, payload: Any, schema: dict[str, Any], path: str, errors: list[str]) -> None:
        if not isinstance(schema, dict):
            return

        ref = schema.get('$ref')
        if isinstance(ref, str):
            resolved = load_schema_ref(ref)
            if resolved:
                self._validate_node(payload, resolved, path, errors)
            return

        expected_type = schema.get('type')
        if expected_type:
            if not self._match_type(payload, expected_type):
                errors.append(f'{path}: expected type {expected_type}, got {type(payload).__name__}')
                return

        enum_values = schema.get('enum')
        if isinstance(enum_values, list) and payload not in enum_values:
            errors.append(f'{path}: value {payload!r} not in enum {enum_values!r}')
            return

        if expected_type == 'object' and isinstance(payload, dict):
            required = schema.get('required', []) or []
            for field in required:
                if field not in payload:
                    errors.append(f'{path}: missing required field {field}')

            properties = schema.get('properties', {}) or {}
            for key, sub_schema in properties.items():
                if key in payload:
                    self._validate_node(payload[key], sub_schema, f'{path}.{key}', errors)
            return

        if expected_type == 'array' and isinstance(payload, list):
            item_schema = schema.get('items')
            if item_schema:
                for idx, item in enumerate(payload):
                    self._validate_node(item, item_schema, f'{path}[{idx}]', errors)
            return

    def _match_type(self, payload: Any, expected_type: str) -> bool:
        if expected_type == 'object':
            return isinstance(payload, dict)
        if expected_type == 'array':
            return isinstance(payload, list)
        if expected_type == 'string':
            return isinstance(payload, str)
        if expected_type == 'integer':
            return isinstance(payload, int) and not isinstance(payload, bool)
        if expected_type == 'boolean':
            return isinstance(payload, bool)
        if expected_type == 'number':
            return (isinstance(payload, int) or isinstance(payload, float)) and not isinstance(payload, bool)
        return True


def load_schema(schema_path: str | Path) -> dict[str, Any]:
    path = Path(schema_path)
    if not path.is_absolute():
        path = PROTOCOLS / path
    return json.loads(path.read_text(encoding='utf-8'))


def load_schema_ref(ref: str) -> dict[str, Any] | None:
    if not ref.startswith('./'):
        return None
    try:
        return load_schema(ref[2:])
    except Exception:
        return None


def validate_payload_against_schema(payload: Any, schema_path: str | Path) -> list[str]:
    schema = load_schema(schema_path)
    validator = SimpleSchemaValidator(schema)
    return validator.validate(payload)

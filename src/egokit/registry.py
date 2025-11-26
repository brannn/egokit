"""Policy registry loader with schema validation and scope merging."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import yaml
from pydantic import ValidationError

from .exceptions import PolicyValidationError, RegistryError, ScopeError
from .models import EgoCharter, EgoConfig, PolicyCharter, PolicyRule


class PolicyRegistry:
    """Loads, validates, and manages policy and ego configurations."""

    def __init__(self, registry_root: Path) -> None:
        """Initialize registry with root path.

        Args:
            registry_root: Path to .egokit/policy-registry directory
        """
        self.root = Path(registry_root)
        self._schema_cache: dict[str, dict[str, Any]] = {}

    def _load_schema(self, schema_name: str) -> dict[str, Any]:
        """Load and cache JSON schema."""
        if schema_name not in self._schema_cache:
            schema_path = self.root / "schemas" / f"{schema_name}.schema.json"
            if not schema_path.exists():
                msg = f"Schema file not found: {schema_path}"
                raise RegistryError(msg)

            try:
                with schema_path.open(encoding="utf-8") as f:
                    self._schema_cache[schema_name] = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                msg = f"Failed to load schema {schema_name}: {e}"
                raise RegistryError(msg) from e

        return self._schema_cache[schema_name]

    def _validate_yaml_against_schema(
        self,
        data: dict[str, Any],
        schema_name: str,
    ) -> None:
        """Validate YAML data against JSON schema."""
        schema = self._load_schema(schema_name)

        try:
            jsonschema.validate(data, schema)
        except jsonschema.ValidationError as e:
            msg = f"Schema validation failed: {e.message}"
            raise PolicyValidationError(
                msg,
                details={"path": list(e.absolute_path), "schema": schema_name},
            ) from e

    def load_charter(self, validate: bool = True) -> PolicyCharter:
        """Load and validate policy charter.

        Args:
            validate: Whether to perform schema validation

        Returns:
            Validated policy charter

        Raises:
            RegistryError: If charter file cannot be loaded
            PolicyValidationError: If validation fails
        """
        charter_path = self.root / "charter.yaml"
        if not charter_path.exists():
            msg = f"Charter file not found: {charter_path}"
            raise RegistryError(msg)

        try:
            with charter_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            msg = f"Failed to parse charter YAML: {e}"
            raise RegistryError(msg) from e
        except OSError as e:
            msg = f"Failed to read charter file: {e}"
            raise RegistryError(msg) from e

        if validate:
            self._validate_yaml_against_schema(data, "charter")

        try:
            return PolicyCharter.model_validate(data)
        except ValidationError as e:
            msg = f"Charter validation failed: {e}"
            raise PolicyValidationError(msg) from e

    def load_ego_config(
        self,
        scope_path: str = "global",
        validate: bool = True,
    ) -> EgoConfig:
        """Load ego configuration for specified scope.

        Args:
            scope_path: Scope path (e.g., 'global', 'teams/backend')
            validate: Whether to perform schema validation

        Returns:
            Validated ego configuration

        Raises:
            RegistryError: If ego file cannot be loaded
            PolicyValidationError: If validation fails
        """
        ego_path = self.root / "ego" / f"{scope_path}.yaml"
        if not ego_path.exists():
            msg = f"Ego config not found: {ego_path}"
            raise RegistryError(msg)

        try:
            with ego_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            msg = f"Failed to parse ego YAML: {e}"
            raise RegistryError(msg) from e
        except OSError as e:
            msg = f"Failed to read ego file: {e}"
            raise RegistryError(msg) from e

        if validate:
            self._validate_yaml_against_schema(data, "ego")

        try:
            charter = EgoCharter.model_validate(data)
        except ValidationError as e:
            msg = f"Ego validation failed: {e}"
            raise PolicyValidationError(msg) from e
        else:
            return charter.ego

    def discover_ego_scopes(self) -> list[str]:
        """Discover all available ego scope configurations.

        Returns:
            List of scope paths (e.g., ['global', 'teams/backend'])
        """
        ego_dir = self.root / "ego"
        if not ego_dir.exists():
            return []

        scopes = []
        for yaml_file in ego_dir.rglob("*.yaml"):
            relative_path = yaml_file.relative_to(ego_dir)
            scope_path = str(relative_path.with_suffix(""))
            scopes.append(scope_path)

        return sorted(scopes)

    def merge_scope_rules(
        self,
        charter: PolicyCharter,
        scope_precedence: list[str],
    ) -> list[PolicyRule]:
        """Merge rules across scopes according to precedence order.

        Args:
            charter: Policy charter containing all scopes
            scope_precedence: Ordered list of scope names (lowest to highest precedence)

        Returns:
            Merged list of policy rules with conflicts resolved

        Raises:
            ScopeError: If specified scope doesn't exist
        """
        merged_rules: dict[str, PolicyRule] = {}

        for scope_name in scope_precedence:
            if scope_name not in charter.scopes:
                msg = f"Scope '{scope_name}' not found in charter"
                raise ScopeError(msg)

            scope_data = charter.scopes[scope_name]

            # Extract rules from YAML structure
            if isinstance(scope_data, dict):
                for _category_name, category_rules in scope_data.items():
                    if isinstance(category_rules, list):
                        for rule_dict in category_rules:
                            try:
                                rule = PolicyRule.model_validate(rule_dict)
                                merged_rules[rule.id] = rule
                            except ValidationError:
                                # Skip invalid rules
                                continue

        return list(merged_rules.values())

    def merge_ego_configs(
        self,
        scope_precedence: list[str],
        validate: bool = True,
    ) -> EgoConfig:
        """Merge ego configurations across scopes.

        Args:
            scope_precedence: Ordered list of scope paths (lowest to highest precedence)
            validate: Whether to perform schema validation

        Returns:
            Merged ego configuration

        Raises:
            ScopeError: If required scopes cannot be loaded
        """
        base_config = None

        for scope_path in scope_precedence:
            try:
                config = self.load_ego_config(scope_path, validate=validate)
                if base_config is None:
                    base_config = config
                else:
                    # Merge configurations (later scopes override earlier ones)
                    base_config = self._merge_ego_instances(base_config, config)
            except RegistryError:
                # Skip missing scope files
                continue

        if base_config is None:
            msg = "No valid ego configurations found in scope precedence"
            raise ScopeError(msg)

        return base_config

    def _merge_ego_instances(
        self,
        base: EgoConfig,
        override: EgoConfig,
    ) -> EgoConfig:
        """Merge two ego configurations with override precedence."""
        merged_data = base.model_dump()
        override_data = override.model_dump(exclude_defaults=True)

        # Deep merge dictionaries
        for key, value in override_data.items():
            if (
                key in merged_data
                and isinstance(merged_data[key], dict)
                and isinstance(value, dict)
            ):
                merged_data[key] = {**merged_data[key], **value}
            else:
                merged_data[key] = value

        return EgoConfig.model_validate(merged_data)

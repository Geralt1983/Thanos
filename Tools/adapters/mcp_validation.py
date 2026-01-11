"""
MCP Schema Validation.

Provides JSON Schema validation for MCP tool arguments and responses,
ensuring data integrity and providing clear error messages for validation failures.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import jsonschema
from jsonschema import Draft7Validator, validators
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from .mcp_errors import MCPError

logger = logging.getLogger(__name__)


class ValidationMode(str, Enum):
    """
    Validation strictness modes.

    - STRICT: Fail on any validation error
    - LENIENT: Log warnings but allow invalid data to pass
    """

    STRICT = "strict"
    LENIENT = "lenient"


class ValidationError(MCPError):
    """
    Error raised when schema validation fails.

    Contains detailed information about validation failures
    including the path to the invalid field and the validation rule that failed.
    """

    def __init__(
        self,
        message: str,
        validation_errors: list[dict[str, Any]],
        tool_name: Optional[str] = None,
        validation_type: str = "unknown",
    ):
        """
        Initialize validation error.

        Args:
            message: High-level error description
            validation_errors: List of detailed validation errors
            tool_name: Name of the tool being validated
            validation_type: Type of validation (arguments/response)
        """
        super().__init__(
            message=message,
            context={
                "validation_errors": validation_errors,
                "tool_name": tool_name,
                "validation_type": validation_type,
            },
            retryable=False,
        )
        self.validation_errors = validation_errors
        self.tool_name = tool_name
        self.validation_type = validation_type

    def get_error_summary(self) -> str:
        """
        Get a human-readable summary of validation errors.

        Returns:
            Formatted string with all validation errors
        """
        lines = [f"{self.validation_type.capitalize()} validation failed"]
        if self.tool_name:
            lines.append(f"Tool: {self.tool_name}")

        lines.append("\nErrors:")
        for i, error in enumerate(self.validation_errors, 1):
            path = error.get("path", "root")
            message = error.get("message", "Unknown error")
            lines.append(f"  {i}. {path}: {message}")

        return "\n".join(lines)


@dataclass
class ValidationConfig:
    """
    Configuration for schema validation behavior.

    Controls validation strictness, error handling, and optional features.
    """

    mode: ValidationMode = ValidationMode.STRICT
    """Validation strictness mode"""

    validate_arguments: bool = True
    """Whether to validate tool arguments"""

    validate_responses: bool = False
    """Whether to validate tool responses (disabled by default for performance)"""

    coerce_types: bool = True
    """Attempt to coerce values to expected types (e.g., "123" -> 123)"""

    allow_additional_properties: bool = True
    """Allow additional properties not defined in schema"""

    max_error_detail: int = 10
    """Maximum number of validation errors to include in detail"""


@dataclass
class ValidationResult:
    """
    Result of a validation operation.

    Contains validation status, errors, and warnings.
    """

    valid: bool
    """Whether validation passed"""

    errors: list[dict[str, Any]] = field(default_factory=list)
    """List of validation errors"""

    warnings: list[dict[str, Any]] = field(default_factory=list)
    """List of validation warnings (in lenient mode)"""

    coerced_data: Optional[Any] = None
    """Data after type coercion (if applicable)"""

    def __bool__(self) -> bool:
        """Allow using ValidationResult in boolean context."""
        return self.valid

    def get_error_messages(self) -> list[str]:
        """Get list of error messages."""
        return [e.get("message", "Unknown error") for e in self.errors]

    def get_warning_messages(self) -> list[str]:
        """Get list of warning messages."""
        return [w.get("message", "Unknown warning") for w in self.warnings]


class SchemaValidator:
    """
    JSON Schema validator for MCP tool arguments and responses.

    Provides validation with configurable strictness, clear error messages,
    and optional type coercion.

    Example:
        >>> validator = SchemaValidator()
        >>> result = validator.validate_arguments(
        ...     tool_name="get_tasks",
        ...     arguments={"status": "active"},
        ...     schema={"type": "object", "properties": {"status": {"type": "string"}}}
        ... )
        >>> if not result.valid:
        ...     print(result.get_error_messages())
    """

    def __init__(self, config: Optional[ValidationConfig] = None):
        """
        Initialize schema validator.

        Args:
            config: Validation configuration (uses defaults if not provided)
        """
        self.config = config or ValidationConfig()

    def _create_validator(self, schema: dict[str, Any]) -> Draft7Validator:
        """
        Create a JSON Schema validator with custom error handling.

        Args:
            schema: JSON Schema to validate against

        Returns:
            Configured validator instance
        """
        # Create validator class with appropriate settings
        ValidatorClass = validators.create(
            meta_schema=Draft7Validator.META_SCHEMA,
            validators=Draft7Validator.VALIDATORS,
        )

        # Create and return validator instance
        return ValidatorClass(schema)

    def _normalize_validation_errors(
        self, errors: list[JsonSchemaValidationError]
    ) -> list[dict[str, Any]]:
        """
        Convert jsonschema validation errors to normalized format.

        Args:
            errors: List of jsonschema ValidationError objects

        Returns:
            List of error dictionaries with path, message, and details
        """
        normalized = []

        for error in errors[: self.config.max_error_detail]:
            # Build path string from error path
            path = "/" + "/".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"

            # Extract relevant error information
            normalized.append(
                {
                    "path": path,
                    "message": error.message,
                    "validator": error.validator,
                    "validator_value": error.validator_value,
                    "schema_path": list(error.schema_path),
                }
            )

        return normalized

    def _coerce_types(
        self, data: Any, schema: dict[str, Any]
    ) -> tuple[Any, list[str]]:
        """
        Attempt to coerce data to match schema types.

        Args:
            data: Data to coerce
            schema: Schema defining expected types

        Returns:
            Tuple of (coerced_data, warnings)
        """
        warnings = []

        if not isinstance(data, dict) or "properties" not in schema:
            return data, warnings

        coerced = data.copy()
        properties = schema.get("properties", {})

        for key, value in data.items():
            if key not in properties:
                continue

            prop_schema = properties[key]
            expected_type = prop_schema.get("type")

            if expected_type == "integer" and isinstance(value, str):
                try:
                    coerced[key] = int(value)
                    warnings.append(f"Coerced '{key}' from string to integer")
                except ValueError:
                    pass

            elif expected_type == "number" and isinstance(value, str):
                try:
                    coerced[key] = float(value)
                    warnings.append(f"Coerced '{key}' from string to number")
                except ValueError:
                    pass

            elif expected_type == "boolean" and isinstance(value, str):
                if value.lower() in ("true", "1", "yes"):
                    coerced[key] = True
                    warnings.append(f"Coerced '{key}' from string to boolean")
                elif value.lower() in ("false", "0", "no"):
                    coerced[key] = False
                    warnings.append(f"Coerced '{key}' from string to boolean")

            elif expected_type == "array" and not isinstance(value, list):
                coerced[key] = [value]
                warnings.append(f"Coerced '{key}' to array")

        return coerced, warnings

    def validate_arguments(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        schema: dict[str, Any],
    ) -> ValidationResult:
        """
        Validate tool arguments against JSON Schema.

        Args:
            tool_name: Name of the tool being validated
            arguments: Arguments to validate
            schema: JSON Schema for the arguments

        Returns:
            ValidationResult with validation status and details

        Raises:
            ValidationError: If validation fails in STRICT mode
        """
        if not self.config.validate_arguments:
            return ValidationResult(valid=True)

        # Apply type coercion if enabled
        data = arguments
        warnings = []
        if self.config.coerce_types:
            data, warnings = self._coerce_types(arguments, schema)

        # Modify schema if additional properties are allowed
        validation_schema = schema.copy()
        if self.config.allow_additional_properties and "additionalProperties" not in validation_schema:
            validation_schema["additionalProperties"] = True

        # Perform validation
        try:
            validator = self._create_validator(validation_schema)
            errors = list(validator.iter_errors(data))

            if errors:
                normalized_errors = self._normalize_validation_errors(errors)

                if self.config.mode == ValidationMode.STRICT:
                    error = ValidationError(
                        message=f"Invalid arguments for tool '{tool_name}'",
                        validation_errors=normalized_errors,
                        tool_name=tool_name,
                        validation_type="arguments",
                    )
                    logger.error(error.get_error_summary())
                    raise error
                else:
                    # Lenient mode - log warnings but allow
                    logger.warning(
                        f"Validation warnings for tool '{tool_name}' arguments: "
                        f"{len(normalized_errors)} issues found (lenient mode)"
                    )
                    return ValidationResult(
                        valid=True,
                        warnings=normalized_errors,
                        coerced_data=data if self.config.coerce_types else None,
                    )

            # Validation passed
            logger.debug(f"Arguments validated successfully for tool '{tool_name}'")
            return ValidationResult(
                valid=True,
                warnings=[{"message": w} for w in warnings],
                coerced_data=data if self.config.coerce_types else None,
            )

        except JsonSchemaValidationError as e:
            # Single validation error
            normalized_errors = self._normalize_validation_errors([e])

            if self.config.mode == ValidationMode.STRICT:
                error = ValidationError(
                    message=f"Invalid arguments for tool '{tool_name}'",
                    validation_errors=normalized_errors,
                    tool_name=tool_name,
                    validation_type="arguments",
                )
                logger.error(error.get_error_summary())
                raise error
            else:
                logger.warning(
                    f"Validation warning for tool '{tool_name}' arguments (lenient mode)"
                )
                return ValidationResult(valid=True, warnings=normalized_errors)

        except Exception as e:
            # Unexpected error during validation
            logger.error(f"Unexpected error validating arguments for '{tool_name}': {e}")
            if self.config.mode == ValidationMode.STRICT:
                raise ValidationError(
                    message=f"Validation error for tool '{tool_name}': {e}",
                    validation_errors=[{"message": str(e), "path": "root"}],
                    tool_name=tool_name,
                    validation_type="arguments",
                )
            else:
                return ValidationResult(
                    valid=True,
                    warnings=[{"message": f"Validation error: {e}", "path": "root"}],
                )

    def validate_response(
        self,
        tool_name: str,
        response: Any,
        schema: dict[str, Any],
    ) -> ValidationResult:
        """
        Validate tool response against JSON Schema.

        Args:
            tool_name: Name of the tool
            response: Response data to validate
            schema: JSON Schema for the response

        Returns:
            ValidationResult with validation status and details

        Raises:
            ValidationError: If validation fails in STRICT mode
        """
        if not self.config.validate_responses:
            return ValidationResult(valid=True)

        # Perform validation
        try:
            validator = self._create_validator(schema)
            errors = list(validator.iter_errors(response))

            if errors:
                normalized_errors = self._normalize_validation_errors(errors)

                if self.config.mode == ValidationMode.STRICT:
                    error = ValidationError(
                        message=f"Invalid response from tool '{tool_name}'",
                        validation_errors=normalized_errors,
                        tool_name=tool_name,
                        validation_type="response",
                    )
                    logger.error(error.get_error_summary())
                    raise error
                else:
                    # Lenient mode - log warnings but allow
                    logger.warning(
                        f"Validation warnings for tool '{tool_name}' response: "
                        f"{len(normalized_errors)} issues found (lenient mode)"
                    )
                    return ValidationResult(valid=True, warnings=normalized_errors)

            # Validation passed
            logger.debug(f"Response validated successfully for tool '{tool_name}'")
            return ValidationResult(valid=True)

        except JsonSchemaValidationError as e:
            # Single validation error
            normalized_errors = self._normalize_validation_errors([e])

            if self.config.mode == ValidationMode.STRICT:
                error = ValidationError(
                    message=f"Invalid response from tool '{tool_name}'",
                    validation_errors=normalized_errors,
                    tool_name=tool_name,
                    validation_type="response",
                )
                logger.error(error.get_error_summary())
                raise error
            else:
                logger.warning(
                    f"Validation warning for tool '{tool_name}' response (lenient mode)"
                )
                return ValidationResult(valid=True, warnings=normalized_errors)

        except Exception as e:
            # Unexpected error during validation
            logger.error(f"Unexpected error validating response for '{tool_name}': {e}")
            if self.config.mode == ValidationMode.STRICT:
                raise ValidationError(
                    message=f"Validation error for tool '{tool_name}': {e}",
                    validation_errors=[{"message": str(e), "path": "root"}],
                    tool_name=tool_name,
                    validation_type="response",
                )
            else:
                return ValidationResult(
                    valid=True,
                    warnings=[{"message": f"Validation error: {e}", "path": "root"}],
                )

    def validate_schema(self, schema: dict[str, Any]) -> ValidationResult:
        """
        Validate that a schema itself is valid JSON Schema.

        Args:
            schema: Schema to validate

        Returns:
            ValidationResult indicating if schema is valid

        Raises:
            ValidationError: If schema is invalid in STRICT mode
        """
        try:
            # Check if schema is valid according to Draft 7 spec
            Draft7Validator.check_schema(schema)
            logger.debug("Schema is valid")
            return ValidationResult(valid=True)

        except jsonschema.SchemaError as e:
            error_info = [
                {
                    "path": "/".join(str(p) for p in e.schema_path),
                    "message": e.message,
                }
            ]

            if self.config.mode == ValidationMode.STRICT:
                error = ValidationError(
                    message="Invalid JSON Schema",
                    validation_errors=error_info,
                    validation_type="schema",
                )
                logger.error(error.get_error_summary())
                raise error
            else:
                logger.warning(f"Schema validation warning: {e.message}")
                return ValidationResult(valid=True, warnings=error_info)

        except Exception as e:
            logger.error(f"Unexpected error validating schema: {e}")
            if self.config.mode == ValidationMode.STRICT:
                raise ValidationError(
                    message=f"Schema validation error: {e}",
                    validation_errors=[{"message": str(e), "path": "root"}],
                    validation_type="schema",
                )
            else:
                return ValidationResult(
                    valid=True,
                    warnings=[{"message": f"Schema error: {e}", "path": "root"}],
                )


# Convenience functions for common validation patterns


def create_strict_validator() -> SchemaValidator:
    """
    Create a validator with strict mode enabled.

    Returns:
        SchemaValidator configured for strict validation
    """
    return SchemaValidator(
        ValidationConfig(
            mode=ValidationMode.STRICT,
            validate_arguments=True,
            validate_responses=True,
        )
    )


def create_lenient_validator() -> SchemaValidator:
    """
    Create a validator with lenient mode enabled.

    Returns:
        SchemaValidator configured for lenient validation
    """
    return SchemaValidator(
        ValidationConfig(
            mode=ValidationMode.LENIENT,
            validate_arguments=True,
            validate_responses=False,
        )
    )


def validate_tool_arguments(
    tool_name: str,
    arguments: dict[str, Any],
    schema: dict[str, Any],
    strict: bool = True,
) -> ValidationResult:
    """
    Convenience function to validate tool arguments.

    Args:
        tool_name: Name of the tool
        arguments: Arguments to validate
        schema: JSON Schema for validation
        strict: Whether to use strict validation

    Returns:
        ValidationResult

    Raises:
        ValidationError: If validation fails in strict mode
    """
    validator = create_strict_validator() if strict else create_lenient_validator()
    return validator.validate_arguments(tool_name, arguments, schema)


def validate_tool_response(
    tool_name: str,
    response: Any,
    schema: dict[str, Any],
    strict: bool = True,
) -> ValidationResult:
    """
    Convenience function to validate tool response.

    Args:
        tool_name: Name of the tool
        response: Response to validate
        schema: JSON Schema for validation
        strict: Whether to use strict validation

    Returns:
        ValidationResult

    Raises:
        ValidationError: If validation fails in strict mode
    """
    config = ValidationConfig(
        mode=ValidationMode.STRICT if strict else ValidationMode.LENIENT,
        validate_responses=True,
    )
    validator = SchemaValidator(config)
    return validator.validate_response(tool_name, response, schema)

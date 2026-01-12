"""
Tests for MCP Schema Validation.

Verifies JSON Schema validation for tool arguments and responses.
"""

import pytest

from Tools.adapters.mcp_validation import (
    SchemaValidator,
    ValidationConfig,
    ValidationError,
    ValidationMode,
    ValidationResult,
    create_lenient_validator,
    create_strict_validator,
    validate_tool_arguments,
    validate_tool_response,
)


class TestValidationMode:
    """Test ValidationMode enum."""

    def test_validation_modes(self):
        """Test that validation modes are defined correctly."""
        assert ValidationMode.STRICT == "strict"
        assert ValidationMode.LENIENT == "lenient"


class TestValidationConfig:
    """Test ValidationConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ValidationConfig()

        assert config.mode == ValidationMode.STRICT
        assert config.validate_arguments is True
        assert config.validate_responses is False
        assert config.coerce_types is True
        assert config.allow_additional_properties is True
        assert config.max_error_detail == 10

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ValidationConfig(
            mode=ValidationMode.LENIENT,
            validate_arguments=False,
            validate_responses=True,
            coerce_types=False,
            allow_additional_properties=False,
            max_error_detail=5,
        )

        assert config.mode == ValidationMode.LENIENT
        assert config.validate_arguments is False
        assert config.validate_responses is True
        assert config.coerce_types is False
        assert config.allow_additional_properties is False
        assert config.max_error_detail == 5


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_valid_result(self):
        """Test creating a valid result."""
        result = ValidationResult(valid=True)

        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.coerced_data is None
        assert bool(result) is True

    def test_invalid_result(self):
        """Test creating an invalid result."""
        errors = [{"path": "/name", "message": "Required field missing"}]
        result = ValidationResult(valid=False, errors=errors)

        assert result.valid is False
        assert result.errors == errors
        assert bool(result) is False

    def test_get_error_messages(self):
        """Test extracting error messages."""
        errors = [
            {"path": "/name", "message": "Required field"},
            {"path": "/age", "message": "Must be integer"},
        ]
        result = ValidationResult(valid=False, errors=errors)

        messages = result.get_error_messages()
        assert messages == ["Required field", "Must be integer"]

    def test_get_warning_messages(self):
        """Test extracting warning messages."""
        warnings = [
            {"path": "/extra", "message": "Unknown field"},
        ]
        result = ValidationResult(valid=True, warnings=warnings)

        messages = result.get_warning_messages()
        assert messages == ["Unknown field"]


class TestValidationError:
    """Test ValidationError exception."""

    def test_validation_error_creation(self):
        """Test creating a validation error."""
        errors = [{"path": "/name", "message": "Required"}]
        error = ValidationError(
            message="Validation failed",
            validation_errors=errors,
            tool_name="test_tool",
            validation_type="arguments",
        )

        assert error.message == "Validation failed"
        assert error.validation_errors == errors
        assert error.tool_name == "test_tool"
        assert error.validation_type == "arguments"
        assert error.retryable is False

    def test_get_error_summary(self):
        """Test error summary generation."""
        errors = [
            {"path": "/name", "message": "Required field"},
            {"path": "/age", "message": "Must be integer"},
        ]
        error = ValidationError(
            message="Validation failed",
            validation_errors=errors,
            tool_name="test_tool",
            validation_type="arguments",
        )

        summary = error.get_error_summary()
        assert "Arguments validation failed" in summary
        assert "test_tool" in summary
        assert "/name: Required field" in summary
        assert "/age: Must be integer" in summary


class TestSchemaValidator:
    """Test SchemaValidator class."""

    def test_validator_creation(self):
        """Test creating a validator."""
        validator = SchemaValidator()

        assert validator.config.mode == ValidationMode.STRICT
        assert validator.config.validate_arguments is True

    def test_validator_with_custom_config(self):
        """Test creating a validator with custom config."""
        config = ValidationConfig(mode=ValidationMode.LENIENT)
        validator = SchemaValidator(config)

        assert validator.config.mode == ValidationMode.LENIENT

    def test_validate_arguments_success(self):
        """Test successful argument validation."""
        validator = SchemaValidator()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name"],
        }
        arguments = {"name": "Alice", "age": 30}

        result = validator.validate_arguments("test_tool", arguments, schema)

        assert result.valid is True
        assert result.errors == []

    def test_validate_arguments_missing_required(self):
        """Test validation failure for missing required field."""
        validator = SchemaValidator()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        }
        arguments = {}

        with pytest.raises(ValidationError) as exc_info:
            validator.validate_arguments("test_tool", arguments, schema)

        error = exc_info.value
        assert error.tool_name == "test_tool"
        assert error.validation_type == "arguments"
        assert len(error.validation_errors) > 0

    def test_validate_arguments_wrong_type(self):
        """Test validation failure for wrong type."""
        validator = SchemaValidator()
        schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer"},
            },
        }
        arguments = {"age": "not a number"}

        with pytest.raises(ValidationError) as exc_info:
            validator.validate_arguments("test_tool", arguments, schema)

        error = exc_info.value
        assert error.tool_name == "test_tool"

    def test_validate_arguments_lenient_mode(self):
        """Test lenient mode allows invalid data."""
        config = ValidationConfig(mode=ValidationMode.LENIENT)
        validator = SchemaValidator(config)
        schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer"},
            },
        }
        arguments = {"age": "not a number"}

        # Should not raise in lenient mode
        result = validator.validate_arguments("test_tool", arguments, schema)

        assert result.valid is True
        assert len(result.warnings) > 0

    def test_validate_arguments_type_coercion(self):
        """Test type coercion for arguments."""
        validator = SchemaValidator()
        schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer"},
                "score": {"type": "number"},
                "active": {"type": "boolean"},
            },
        }
        arguments = {"age": "30", "score": "95.5", "active": "true"}

        result = validator.validate_arguments("test_tool", arguments, schema)

        assert result.valid is True
        assert result.coerced_data is not None
        assert result.coerced_data["age"] == 30
        assert result.coerced_data["score"] == 95.5
        assert result.coerced_data["active"] is True

    def test_validate_arguments_no_coercion(self):
        """Test validation without type coercion."""
        config = ValidationConfig(coerce_types=False)
        validator = SchemaValidator(config)
        schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer"},
            },
        }
        arguments = {"age": "30"}

        with pytest.raises(ValidationError):
            validator.validate_arguments("test_tool", arguments, schema)

    def test_validate_arguments_additional_properties(self):
        """Test handling of additional properties."""
        validator = SchemaValidator()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
        }
        arguments = {"name": "Alice", "extra": "field"}

        # Should pass by default (allow_additional_properties=True)
        result = validator.validate_arguments("test_tool", arguments, schema)
        assert result.valid is True

    def test_validate_arguments_no_additional_properties(self):
        """Test strict additional properties handling."""
        config = ValidationConfig(allow_additional_properties=False)
        validator = SchemaValidator(config)
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "additionalProperties": False,
        }
        arguments = {"name": "Alice", "extra": "field"}

        with pytest.raises(ValidationError):
            validator.validate_arguments("test_tool", arguments, schema)

    def test_validate_arguments_disabled(self):
        """Test that validation can be disabled."""
        config = ValidationConfig(validate_arguments=False)
        validator = SchemaValidator(config)
        schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer"},
            },
        }
        # Invalid data, but validation is disabled
        arguments = {"age": "not a number"}

        result = validator.validate_arguments("test_tool", arguments, schema)

        assert result.valid is True

    def test_validate_response_success(self):
        """Test successful response validation."""
        config = ValidationConfig(validate_responses=True)
        validator = SchemaValidator(config)
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "data": {"type": "array"},
            },
        }
        response = {"status": "success", "data": [1, 2, 3]}

        result = validator.validate_response("test_tool", response, schema)

        assert result.valid is True

    def test_validate_response_failure(self):
        """Test response validation failure."""
        config = ValidationConfig(validate_responses=True)
        validator = SchemaValidator(config)
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
            },
            "required": ["status"],
        }
        response = {}

        with pytest.raises(ValidationError) as exc_info:
            validator.validate_response("test_tool", response, schema)

        error = exc_info.value
        assert error.validation_type == "response"

    def test_validate_response_disabled(self):
        """Test that response validation can be disabled."""
        validator = SchemaValidator()  # validate_responses=False by default
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
            },
            "required": ["status"],
        }
        response = {}  # Invalid

        result = validator.validate_response("test_tool", response, schema)

        assert result.valid is True

    def test_validate_schema_valid(self):
        """Test validating a valid schema."""
        validator = SchemaValidator()
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
        }

        result = validator.validate_schema(schema)

        assert result.valid is True

    def test_validate_schema_invalid(self):
        """Test validating an invalid schema."""
        validator = SchemaValidator()
        schema = {
            "type": "invalid_type",  # Not a valid JSON Schema type
        }

        with pytest.raises(ValidationError):
            validator.validate_schema(schema)


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_strict_validator(self):
        """Test creating a strict validator."""
        validator = create_strict_validator()

        assert validator.config.mode == ValidationMode.STRICT
        assert validator.config.validate_arguments is True
        assert validator.config.validate_responses is True

    def test_create_lenient_validator(self):
        """Test creating a lenient validator."""
        validator = create_lenient_validator()

        assert validator.config.mode == ValidationMode.LENIENT
        assert validator.config.validate_arguments is True
        assert validator.config.validate_responses is False

    def test_validate_tool_arguments_strict(self):
        """Test convenience function for strict argument validation."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
            "required": ["name"],
        }
        arguments = {"name": "Alice"}

        result = validate_tool_arguments("test_tool", arguments, schema, strict=True)

        assert result.valid is True

    def test_validate_tool_arguments_lenient(self):
        """Test convenience function for lenient argument validation."""
        schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer"},
            },
        }
        arguments = {"age": "not a number"}

        result = validate_tool_arguments("test_tool", arguments, schema, strict=False)

        assert result.valid is True
        assert len(result.warnings) > 0

    def test_validate_tool_response_strict(self):
        """Test convenience function for strict response validation."""
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
            },
        }
        response = {"status": "success"}

        result = validate_tool_response("test_tool", response, schema, strict=True)

        assert result.valid is True

    def test_validate_tool_response_lenient(self):
        """Test convenience function for lenient response validation."""
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
            },
            "required": ["status"],
        }
        response = {}

        result = validate_tool_response("test_tool", response, schema, strict=False)

        assert result.valid is True
        assert len(result.warnings) > 0


class TestComplexValidation:
    """Test complex validation scenarios."""

    def test_nested_object_validation(self):
        """Test validation of nested objects."""
        validator = SchemaValidator()
        schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                    },
                    "required": ["name", "email"],
                },
            },
            "required": ["user"],
        }
        arguments = {"user": {"name": "Alice", "email": "alice@example.com"}}

        result = validator.validate_arguments("test_tool", arguments, schema)

        assert result.valid is True

    def test_array_validation(self):
        """Test validation of arrays."""
        validator = SchemaValidator()
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        }
        arguments = {"tags": ["python", "mcp", "validation"]}

        result = validator.validate_arguments("test_tool", arguments, schema)

        assert result.valid is True

    def test_array_validation_wrong_item_type(self):
        """Test array validation with wrong item type."""
        validator = SchemaValidator()
        schema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        }
        arguments = {"tags": ["python", 123, "validation"]}

        with pytest.raises(ValidationError):
            validator.validate_arguments("test_tool", arguments, schema)

    def test_enum_validation(self):
        """Test validation with enum constraint."""
        validator = SchemaValidator()
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "inactive", "pending"]},
            },
        }
        arguments = {"status": "active"}

        result = validator.validate_arguments("test_tool", arguments, schema)

        assert result.valid is True

    def test_enum_validation_invalid_value(self):
        """Test enum validation with invalid value."""
        validator = SchemaValidator()
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "inactive", "pending"]},
            },
        }
        arguments = {"status": "invalid"}

        with pytest.raises(ValidationError):
            validator.validate_arguments("test_tool", arguments, schema)

    def test_min_max_validation(self):
        """Test validation with min/max constraints."""
        validator = SchemaValidator()
        schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "minimum": 0, "maximum": 150},
            },
        }
        arguments = {"age": 30}

        result = validator.validate_arguments("test_tool", arguments, schema)

        assert result.valid is True

    def test_min_max_validation_out_of_range(self):
        """Test min/max validation with out of range value."""
        validator = SchemaValidator()
        schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer", "minimum": 0, "maximum": 150},
            },
        }
        arguments = {"age": 200}

        with pytest.raises(ValidationError):
            validator.validate_arguments("test_tool", arguments, schema)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Variant Validation Helpers

Utilities for validating variant configurations and registry compliance.

Services can use these validators to ensure their variant definitions
meet the requirements of the unified variant registration system.

Version: 1.0.0
Created: 2025-11-29
"""

from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field, ValidationError
import re


class ValidationResult(BaseModel):
    """Result of variant validation"""
    valid: bool = Field(..., description="Whether validation passed")
    errors: List[str] = Field(default_factory=list, description="List of validation errors")
    warnings: List[str] = Field(default_factory=list, description="List of validation warnings")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions for improvement")

    def add_error(self, message: str) -> "ValidationResult":
        """Add an error message"""
        self.valid = False
        self.errors.append(message)
        return self

    def add_warning(self, message: str) -> "ValidationResult":
        """Add a warning message"""
        self.warnings.append(message)
        return self

    def add_suggestion(self, message: str) -> "ValidationResult":
        """Add a suggestion"""
        self.suggestions.append(message)
        return self

    def get_summary(self) -> str:
        """Get human-readable summary"""
        if self.valid:
            summary = "✅ Validation PASSED"
            if self.warnings:
                summary += f" (with {len(self.warnings)} warnings)"
        else:
            summary = f"❌ Validation FAILED ({len(self.errors)} errors)"

        parts = [summary]

        if self.errors:
            parts.append("\n\nErrors:")
            for i, error in enumerate(self.errors, 1):
                parts.append(f"  {i}. {error}")

        if self.warnings:
            parts.append("\n\nWarnings:")
            for i, warning in enumerate(self.warnings, 1):
                parts.append(f"  {i}. {warning}")

        if self.suggestions:
            parts.append("\n\nSuggestions:")
            for i, suggestion in enumerate(self.suggestions, 1):
                parts.append(f"  {i}. {suggestion}")

        return "".join(parts)


class VariantValidator:
    """
    Validator for variant configurations.

    Validates variant definitions against unified registry requirements.

    Usage:
        validator = VariantValidator()

        result = validator.validate_variant({
            "variant_id": "pie_chart",
            "display_name": "Pie Chart",
            "description": "Circular chart showing proportional data",
            "endpoint": "/v3/charts/pie",
            "classification": {
                "keywords": ["pie", "donut", "chart", "percentage", "proportion"],
                "priority": 2
            }
        })

        if result.valid:
            print("Variant is valid!")
        else:
            print(result.get_summary())
    """

    # Validation rules
    MIN_KEYWORDS = 5
    MAX_KEYWORDS = 50
    MIN_PRIORITY = 1
    MAX_PRIORITY = 10
    MIN_KEYWORD_LENGTH = 2
    MAX_KEYWORD_LENGTH = 50

    # Valid status values
    VALID_STATUSES = ["production", "beta", "deprecated", "experimental"]

    # Valid output formats
    VALID_OUTPUT_FORMATS = ["html", "json", "svg", "xml", "text"]

    def __init__(self, strict: bool = False):
        """
        Initialize validator.

        Args:
            strict: If True, warnings are treated as errors
        """
        self.strict = strict

    def validate_variant(self, variant_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a variant configuration.

        Args:
            variant_data: Variant configuration dict

        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult(valid=True)

        # Required fields
        self._validate_required_fields(variant_data, result)

        # Variant ID
        if "variant_id" in variant_data:
            self._validate_variant_id(variant_data["variant_id"], result)

        # Display name
        if "display_name" in variant_data:
            self._validate_display_name(variant_data["display_name"], result)

        # Description
        if "description" in variant_data:
            self._validate_description(variant_data["description"], result)

        # Endpoint
        if "endpoint" in variant_data:
            self._validate_endpoint(variant_data["endpoint"], result)

        # Classification
        if "classification" in variant_data:
            self._validate_classification(variant_data["classification"], result)

        # Status
        if "status" in variant_data:
            self._validate_status(variant_data["status"], result)

        # Parameters
        if "parameters" in variant_data:
            self._validate_parameters(variant_data["parameters"], result)

        # LLM Guidance
        if "llm_guidance" in variant_data:
            self._validate_llm_guidance(variant_data["llm_guidance"], result)

        # If strict mode, convert warnings to errors
        if self.strict and result.warnings:
            for warning in result.warnings:
                result.add_error(f"STRICT MODE: {warning}")
            result.warnings.clear()

        return result

    def validate_service(self, service_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate a complete service configuration.

        Args:
            service_data: Service configuration dict

        Returns:
            ValidationResult with validation status
        """
        result = ValidationResult(valid=True)

        # Service-level validation
        required_service_fields = ["service_name", "base_url", "variants"]
        for field in required_service_fields:
            if field not in service_data:
                result.add_error(f"Missing required service field: {field}")

        # Service name
        if "service_name" in service_data:
            self._validate_service_name(service_data["service_name"], result)

        # Base URL
        if "base_url" in service_data:
            self._validate_base_url(service_data["base_url"], result)

        # Endpoint pattern
        if "endpoint_pattern" in service_data:
            self._validate_endpoint_pattern(service_data["endpoint_pattern"], result)

        # Validate all variants
        if "variants" in service_data:
            variants = service_data["variants"]
            if not isinstance(variants, dict):
                result.add_error("Variants must be a dictionary")
            else:
                for variant_id, variant_data in variants.items():
                    # Validate each variant
                    variant_result = self.validate_variant(variant_data)

                    # Add variant-specific errors/warnings
                    for error in variant_result.errors:
                        result.add_error(f"Variant '{variant_id}': {error}")
                    for warning in variant_result.warnings:
                        result.add_warning(f"Variant '{variant_id}': {warning}")

                # Check for duplicate keywords across variants
                self._check_duplicate_keywords(variants, result)

        return result

    def _validate_required_fields(self, data: Dict[str, Any], result: ValidationResult):
        """Validate required fields are present"""
        required = ["variant_id", "display_name", "description", "endpoint"]

        for field in required:
            if field not in data:
                result.add_error(f"Missing required field: {field}")

    def _validate_variant_id(self, variant_id: str, result: ValidationResult):
        """Validate variant ID format"""
        if not isinstance(variant_id, str):
            result.add_error("variant_id must be a string")
            return

        if not variant_id:
            result.add_error("variant_id cannot be empty")
            return

        # Check format (snake_case)
        if not re.match(r'^[a-z][a-z0-9_]*$', variant_id):
            result.add_error(
                "variant_id must be snake_case (lowercase letters, numbers, underscores, "
                "starting with a letter)"
            )

        # Length check
        if len(variant_id) < 3:
            result.add_error("variant_id must be at least 3 characters")
        elif len(variant_id) > 50:
            result.add_error("variant_id must be at most 50 characters")

    def _validate_display_name(self, display_name: str, result: ValidationResult):
        """Validate display name"""
        if not isinstance(display_name, str):
            result.add_error("display_name must be a string")
            return

        if not display_name:
            result.add_error("display_name cannot be empty")
            return

        if len(display_name) < 3:
            result.add_warning("display_name is very short (< 3 characters)")
        elif len(display_name) > 100:
            result.add_error("display_name is too long (> 100 characters)")

    def _validate_description(self, description: str, result: ValidationResult):
        """Validate description"""
        if not isinstance(description, str):
            result.add_error("description must be a string")
            return

        if not description:
            result.add_error("description cannot be empty")
            return

        if len(description) < 10:
            result.add_warning("description is very short (< 10 characters)")
        elif len(description) > 500:
            result.add_warning("description is very long (> 500 characters)")

    def _validate_endpoint(self, endpoint: str, result: ValidationResult):
        """Validate endpoint format"""
        if not isinstance(endpoint, str):
            result.add_error("endpoint must be a string")
            return

        if not endpoint:
            result.add_error("endpoint cannot be empty")
            return

        if not endpoint.startswith('/'):
            result.add_error("endpoint must start with '/'")

        # Check for spaces
        if ' ' in endpoint:
            result.add_error("endpoint cannot contain spaces")

    def _validate_classification(self, classification: Dict[str, Any], result: ValidationResult):
        """Validate classification section"""
        if not isinstance(classification, dict):
            result.add_error("classification must be a dictionary")
            return

        # Keywords
        if "keywords" not in classification:
            result.add_error("classification.keywords is required")
        else:
            self._validate_keywords(classification["keywords"], result)

        # Priority
        if "priority" in classification:
            self._validate_priority(classification["priority"], result)

    def _validate_keywords(self, keywords: List[str], result: ValidationResult):
        """Validate keywords list"""
        if not isinstance(keywords, list):
            result.add_error("keywords must be a list")
            return

        # Minimum keywords
        if len(keywords) < self.MIN_KEYWORDS:
            result.add_error(
                f"keywords must have at least {self.MIN_KEYWORDS} items (has {len(keywords)})"
            )

        # Maximum keywords
        if len(keywords) > self.MAX_KEYWORDS:
            result.add_warning(
                f"keywords has many items ({len(keywords)}). Consider reducing for performance."
            )

        # Validate each keyword
        for i, keyword in enumerate(keywords):
            if not isinstance(keyword, str):
                result.add_error(f"keywords[{i}] must be a string")
                continue

            if not keyword:
                result.add_error(f"keywords[{i}] cannot be empty")
                continue

            # Length check
            if len(keyword) < self.MIN_KEYWORD_LENGTH:
                result.add_warning(
                    f"keywords[{i}] '{keyword}' is very short (< {self.MIN_KEYWORD_LENGTH} chars)"
                )
            elif len(keyword) > self.MAX_KEYWORD_LENGTH:
                result.add_error(
                    f"keywords[{i}] '{keyword}' is too long (> {self.MAX_KEYWORD_LENGTH} chars)"
                )

            # Check for special characters
            if not re.match(r'^[a-z0-9\s\-_]+$', keyword.lower()):
                result.add_warning(
                    f"keywords[{i}] '{keyword}' contains special characters"
                )

        # Check for duplicates
        if len(keywords) != len(set(keywords)):
            duplicates = [k for k in keywords if keywords.count(k) > 1]
            result.add_warning(f"keywords contains duplicates: {set(duplicates)}")

    def _validate_priority(self, priority: int, result: ValidationResult):
        """Validate priority value"""
        if not isinstance(priority, int):
            result.add_error("priority must be an integer")
            return

        if priority < self.MIN_PRIORITY or priority > self.MAX_PRIORITY:
            result.add_error(
                f"priority must be between {self.MIN_PRIORITY} and {self.MAX_PRIORITY} "
                f"(got {priority})"
            )

    def _validate_status(self, status: str, result: ValidationResult):
        """Validate status value"""
        if not isinstance(status, str):
            result.add_error("status must be a string")
            return

        if status not in self.VALID_STATUSES:
            result.add_error(
                f"status must be one of {self.VALID_STATUSES} (got '{status}')"
            )

    def _validate_parameters(self, parameters: Dict[str, Any], result: ValidationResult):
        """Validate parameters section"""
        if not isinstance(parameters, dict):
            result.add_error("parameters must be a dictionary")
            return

        # Output format
        if "output_format" in parameters:
            output_format = parameters["output_format"]
            if output_format not in self.VALID_OUTPUT_FORMATS:
                result.add_warning(
                    f"output_format '{output_format}' is not a standard format. "
                    f"Standard formats: {self.VALID_OUTPUT_FORMATS}"
                )

        # Required fields
        if "required_fields" in parameters:
            if not isinstance(parameters["required_fields"], list):
                result.add_error("parameters.required_fields must be a list")

        # Optional fields
        if "optional_fields" in parameters:
            if not isinstance(parameters["optional_fields"], list):
                result.add_error("parameters.optional_fields must be a list")

    def _validate_llm_guidance(self, llm_guidance: Dict[str, Any], result: ValidationResult):
        """Validate LLM guidance section"""
        if not isinstance(llm_guidance, dict):
            result.add_error("llm_guidance must be a dictionary")
            return

        # Use cases
        if "use_cases" in llm_guidance:
            use_cases = llm_guidance["use_cases"]
            if not isinstance(use_cases, list):
                result.add_error("llm_guidance.use_cases must be a list")
            elif len(use_cases) == 0:
                result.add_suggestion("Consider adding use_cases for better LLM guidance")

        # Best for / avoid when
        if "best_for" not in llm_guidance:
            result.add_suggestion("Consider adding 'best_for' field for LLM guidance")

        if "avoid_when" not in llm_guidance:
            result.add_suggestion("Consider adding 'avoid_when' field for LLM guidance")

    def _validate_service_name(self, service_name: str, result: ValidationResult):
        """Validate service name format"""
        if not isinstance(service_name, str):
            result.add_error("service_name must be a string")
            return

        if not re.match(r'^[a-z][a-z0-9_]*_v\d+(\.\d+)?$', service_name):
            result.add_warning(
                "service_name should follow pattern: name_v1.0 or name_v1"
            )

    def _validate_base_url(self, base_url: str, result: ValidationResult):
        """Validate base URL format"""
        if not isinstance(base_url, str):
            result.add_error("base_url must be a string")
            return

        if not base_url.startswith(('http://', 'https://')):
            result.add_error("base_url must start with http:// or https://")

    def _validate_endpoint_pattern(self, pattern: str, result: ValidationResult):
        """Validate endpoint pattern"""
        valid_patterns = ["single", "per_variant", "typed"]

        if pattern not in valid_patterns:
            result.add_error(
                f"endpoint_pattern must be one of {valid_patterns} (got '{pattern}')"
            )

    def _check_duplicate_keywords(self, variants: Dict[str, Any], result: ValidationResult):
        """Check for duplicate keywords across variants"""
        all_keywords = {}

        for variant_id, variant_data in variants.items():
            if "classification" in variant_data:
                keywords = variant_data["classification"].get("keywords", [])
                for keyword in keywords:
                    if keyword in all_keywords:
                        result.add_warning(
                            f"Keyword '{keyword}' appears in multiple variants: "
                            f"{variant_id} and {all_keywords[keyword]}"
                        )
                    else:
                        all_keywords[keyword] = variant_id


def validate_variant(variant_data: Dict[str, Any], strict: bool = False) -> ValidationResult:
    """
    Convenience function to validate a variant.

    Args:
        variant_data: Variant configuration dict
        strict: If True, warnings are treated as errors

    Returns:
        ValidationResult

    Example:
        result = validate_variant({
            "variant_id": "pie_chart",
            "display_name": "Pie Chart",
            ...
        })

        if not result.valid:
            print(result.get_summary())
    """
    validator = VariantValidator(strict=strict)
    return validator.validate_variant(variant_data)


def validate_service(service_data: Dict[str, Any], strict: bool = False) -> ValidationResult:
    """
    Convenience function to validate a service.

    Args:
        service_data: Service configuration dict
        strict: If True, warnings are treated as errors

    Returns:
        ValidationResult

    Example:
        result = validate_service({
            "service_name": "analytics_service_v3",
            "base_url": "https://...",
            "variants": { ... }
        })

        print(result.get_summary())
    """
    validator = VariantValidator(strict=strict)
    return validator.validate_service(service_data)

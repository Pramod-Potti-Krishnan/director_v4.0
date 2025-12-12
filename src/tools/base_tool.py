"""
Base Tool Interface for MCP-Style Tools

This module defines the base interface for all tools in the Director Agent v4.0.
Tools wrap external services (Text Service, Illustrator, Analytics, Deck Builder)
and internal functionality (conversation helpers) in a consistent interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CostTier(str, Enum):
    """Cost tiers for tool invocation."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ToolResult(BaseModel):
    """Standard result from tool execution."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    tool_id: str
    execution_time_ms: Optional[float] = None

    @property
    def html_content(self) -> Optional[str]:
        """Convenience accessor for HTML content."""
        if self.data:
            return self.data.get('html_content') or self.data.get('html')
        return None


class ToolCall(BaseModel):
    """A request to invoke a tool."""
    tool_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    slide_ids: Optional[List[str]] = None  # For batch operations
    context: Optional[Dict[str, Any]] = None  # Additional context


class ToolDefinition(BaseModel):
    """Definition of a tool for the registry."""
    tool_id: str
    display_name: str
    description: str
    cost_tier: CostTier
    requires_context: List[str] = Field(default_factory=list)
    requires_approval: bool = False
    input_schema: Dict[str, Any] = Field(default_factory=dict)
    output_schema: Dict[str, Any] = Field(default_factory=dict)


class BaseTool(ABC):
    """
    Abstract base class for all tools.

    Tools must implement:
    - get_definition(): Return tool metadata
    - execute(): Perform the tool's action
    - validate_parameters(): Validate input parameters
    """

    @abstractmethod
    def get_definition(self) -> ToolDefinition:
        """Return the tool definition with metadata."""
        pass

    @abstractmethod
    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        Execute the tool with given parameters.

        Args:
            parameters: Tool-specific parameters
            context: Session context for the tool

        Returns:
            ToolResult with success status and data/error
        """
        pass

    def validate_parameters(self, parameters: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate input parameters against schema.

        Args:
            parameters: Parameters to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        definition = self.get_definition()
        schema = definition.input_schema

        # Check required fields
        required = schema.get('required', [])
        for field in required:
            if field not in parameters:
                return False, f"Missing required field: {field}"

        # Basic type validation
        properties = schema.get('properties', {})
        for field, value in parameters.items():
            if field in properties:
                prop_schema = properties[field]
                expected_type = prop_schema.get('type')

                if expected_type == 'string' and not isinstance(value, str):
                    return False, f"Field '{field}' must be a string"
                elif expected_type == 'integer' and not isinstance(value, int):
                    return False, f"Field '{field}' must be an integer"
                elif expected_type == 'number' and not isinstance(value, (int, float)):
                    return False, f"Field '{field}' must be a number"
                elif expected_type == 'boolean' and not isinstance(value, bool):
                    return False, f"Field '{field}' must be a boolean"
                elif expected_type == 'array' and not isinstance(value, list):
                    return False, f"Field '{field}' must be an array"
                elif expected_type == 'object' and not isinstance(value, dict):
                    return False, f"Field '{field}' must be an object"

                # Check min/max for integers
                if expected_type == 'integer':
                    min_val = prop_schema.get('minimum')
                    max_val = prop_schema.get('maximum')
                    if min_val is not None and value < min_val:
                        return False, f"Field '{field}' must be >= {min_val}"
                    if max_val is not None and value > max_val:
                        return False, f"Field '{field}' must be <= {max_val}"

                # Check maxLength for strings
                if expected_type == 'string':
                    max_len = prop_schema.get('maxLength')
                    if max_len is not None and len(value) > max_len:
                        return False, f"Field '{field}' must be <= {max_len} characters"

                # Check enum values
                enum_values = prop_schema.get('enum')
                if enum_values and value not in enum_values:
                    return False, f"Field '{field}' must be one of: {enum_values}"

        return True, None

    def check_prerequisites(
        self,
        session_context: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Check if prerequisites are met for this tool.

        Args:
            session_context: Current session context with flags

        Returns:
            Tuple of (prerequisites_met, error_message)
        """
        definition = self.get_definition()
        required_context = definition.requires_context

        for ctx_key in required_context:
            # Check for context data
            if ctx_key not in session_context or not session_context.get(ctx_key):
                # Also check boolean flags
                flag_key = f"has_{ctx_key}"
                if not session_context.get(flag_key, False):
                    return False, f"Prerequisite not met: {ctx_key}"

        return True, None

    @property
    def tool_id(self) -> str:
        """Convenience property for tool ID."""
        return self.get_definition().tool_id

    @property
    def cost_tier(self) -> CostTier:
        """Convenience property for cost tier."""
        return self.get_definition().cost_tier

    @property
    def requires_approval(self) -> bool:
        """Convenience property for approval requirement."""
        return self.get_definition().requires_approval


class ToolExecutionError(Exception):
    """Exception raised when tool execution fails."""

    def __init__(self, tool_id: str, message: str, details: Optional[Dict] = None):
        self.tool_id = tool_id
        self.message = message
        self.details = details or {}
        super().__init__(f"Tool '{tool_id}' failed: {message}")


class ToolValidationError(Exception):
    """Exception raised when tool parameter validation fails."""

    def __init__(self, tool_id: str, message: str):
        self.tool_id = tool_id
        self.message = message
        super().__init__(f"Tool '{tool_id}' validation failed: {message}")


class ToolPrerequisiteError(Exception):
    """Exception raised when tool prerequisites are not met."""

    def __init__(self, tool_id: str, message: str):
        self.tool_id = tool_id
        self.message = message
        super().__init__(f"Tool '{tool_id}' prerequisites not met: {message}")

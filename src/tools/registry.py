"""
Tool Registry for MCP-Style Tools

Central registration and management system for all tools in Director Agent v4.0.
Handles tool registration, lookup, validation, and cost control enforcement.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from .base_tool import (
    BaseTool, ToolDefinition, ToolResult, ToolCall, CostTier,
    ToolExecutionError, ToolValidationError, ToolPrerequisiteError
)

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for all MCP-style tools.

    Responsibilities:
    - Register and store tool instances
    - Validate tool calls against schemas
    - Enforce cost control rules
    - Check prerequisites before execution
    - Execute tools and return results
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the tool registry.

        Args:
            config_path: Path to config directory (for loading schemas and costs)
        """
        self._tools: Dict[str, BaseTool] = {}
        self._definitions: Dict[str, ToolDefinition] = {}
        self._config_path = config_path or self._default_config_path()

        # Load configuration
        self._tool_schemas = self._load_tool_schemas()
        self._cost_config = self._load_cost_config()

        logger.info(f"ToolRegistry initialized with config from: {self._config_path}")

    def _default_config_path(self) -> str:
        """Get default config path relative to this file."""
        return str(Path(__file__).parent.parent.parent / "config" / "tools")

    def _load_tool_schemas(self) -> Dict[str, Any]:
        """Load tool schemas from JSON file."""
        try:
            schema_path = Path(self._config_path) / "tool_schemas.json"
            if schema_path.exists():
                with open(schema_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load tool schemas: {e}")
        return {"tools": {}}

    def _load_cost_config(self) -> Dict[str, Any]:
        """Load cost configuration from JSON file."""
        try:
            cost_path = Path(self._config_path) / "tool_costs.json"
            if cost_path.exists():
                with open(cost_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load cost config: {e}")
        return {"cost_tiers": {}, "guardrails": {}, "prerequisites": {}}

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool with the registry.

        Args:
            tool: Tool instance to register
        """
        definition = tool.get_definition()
        tool_id = definition.tool_id

        if tool_id in self._tools:
            logger.warning(f"Overwriting existing tool: {tool_id}")

        self._tools[tool_id] = tool
        self._definitions[tool_id] = definition

        logger.info(f"Registered tool: {tool_id} (cost_tier={definition.cost_tier.value})")

    def unregister(self, tool_id: str) -> bool:
        """
        Unregister a tool from the registry.

        Args:
            tool_id: ID of tool to unregister

        Returns:
            True if tool was unregistered, False if not found
        """
        if tool_id in self._tools:
            del self._tools[tool_id]
            del self._definitions[tool_id]
            logger.info(f"Unregistered tool: {tool_id}")
            return True
        return False

    def get_tool(self, tool_id: str) -> Optional[BaseTool]:
        """
        Get a tool by ID.

        Args:
            tool_id: Tool ID to lookup

        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(tool_id)

    def get_definition(self, tool_id: str) -> Optional[ToolDefinition]:
        """
        Get a tool definition by ID.

        Args:
            tool_id: Tool ID to lookup

        Returns:
            ToolDefinition or None if not found
        """
        return self._definitions.get(tool_id)

    def list_tools(self) -> List[ToolDefinition]:
        """
        List all registered tools.

        Returns:
            List of all tool definitions
        """
        return list(self._definitions.values())

    def list_tools_by_tier(self, tier: CostTier) -> List[ToolDefinition]:
        """
        List tools by cost tier.

        Args:
            tier: Cost tier to filter by

        Returns:
            List of tool definitions in that tier
        """
        return [d for d in self._definitions.values() if d.cost_tier == tier]

    def get_tool_ids(self) -> List[str]:
        """Get list of all registered tool IDs."""
        return list(self._tools.keys())

    async def execute(
        self,
        tool_call: ToolCall,
        session_context: Dict[str, Any],
        check_approval: bool = True
    ) -> ToolResult:
        """
        Execute a tool call with validation and cost control.

        Args:
            tool_call: The tool call to execute
            session_context: Current session context
            check_approval: Whether to enforce approval requirements

        Returns:
            ToolResult with execution outcome

        Raises:
            ToolExecutionError: If tool execution fails
            ToolValidationError: If parameters are invalid
            ToolPrerequisiteError: If prerequisites not met
        """
        import time
        start_time = time.time()

        tool_id = tool_call.tool_id

        # Get tool
        tool = self.get_tool(tool_id)
        if not tool:
            raise ToolExecutionError(tool_id, f"Tool not found: {tool_id}")

        # Validate parameters
        is_valid, error = tool.validate_parameters(tool_call.parameters)
        if not is_valid:
            raise ToolValidationError(tool_id, error)

        # Check prerequisites
        prereq_met, prereq_error = tool.check_prerequisites(session_context)
        if not prereq_met:
            raise ToolPrerequisiteError(tool_id, prereq_error)

        # Check approval requirement
        if check_approval and tool.requires_approval:
            has_approval = session_context.get('has_explicit_approval', False)
            if not has_approval:
                raise ToolPrerequisiteError(
                    tool_id,
                    "This tool requires explicit user approval"
                )

        # Execute tool
        try:
            result = await tool.execute(
                parameters=tool_call.parameters,
                context=tool_call.context or session_context
            )

            # Add execution time
            execution_time_ms = (time.time() - start_time) * 1000
            result.execution_time_ms = execution_time_ms

            logger.info(
                f"Tool '{tool_id}' executed successfully "
                f"(time={execution_time_ms:.1f}ms)"
            )

            return result

        except Exception as e:
            logger.error(f"Tool '{tool_id}' execution failed: {e}")
            raise ToolExecutionError(tool_id, str(e))

    async def execute_batch(
        self,
        tool_calls: List[ToolCall],
        session_context: Dict[str, Any],
        check_approval: bool = True,
        parallel: bool = True
    ) -> List[ToolResult]:
        """
        Execute multiple tool calls.

        Args:
            tool_calls: List of tool calls to execute
            session_context: Current session context
            check_approval: Whether to enforce approval requirements
            parallel: Whether to execute in parallel (if possible)

        Returns:
            List of ToolResults in same order as input
        """
        import asyncio

        if parallel:
            # Execute all tools in parallel
            tasks = [
                self.execute(call, session_context, check_approval)
                for call in tool_calls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Convert exceptions to error results
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append(ToolResult(
                        success=False,
                        error=str(result),
                        tool_id=tool_calls[i].tool_id
                    ))
                else:
                    processed_results.append(result)

            return processed_results
        else:
            # Execute sequentially
            results = []
            for call in tool_calls:
                try:
                    result = await self.execute(call, session_context, check_approval)
                    results.append(result)
                except Exception as e:
                    results.append(ToolResult(
                        success=False,
                        error=str(e),
                        tool_id=call.tool_id
                    ))
            return results

    def get_cost_tier(self, tool_id: str) -> Optional[CostTier]:
        """
        Get cost tier for a tool.

        Args:
            tool_id: Tool ID

        Returns:
            CostTier or None if tool not found
        """
        definition = self.get_definition(tool_id)
        return definition.cost_tier if definition else None

    def requires_approval(self, tool_id: str) -> bool:
        """
        Check if tool requires explicit user approval.

        Args:
            tool_id: Tool ID

        Returns:
            True if approval required, False otherwise
        """
        definition = self.get_definition(tool_id)
        if definition:
            return definition.requires_approval
        return True  # Default to requiring approval for unknown tools

    def get_approval_phrases(self) -> Dict[str, List[str]]:
        """Get approval and non-approval phrases from config."""
        return self._cost_config.get('approval_phrases', {
            'explicit_approval': ['generate', 'create it', 'proceed'],
            'not_approval': ['looks good', 'yes', 'ok']
        })

    def get_guardrails(self) -> Dict[str, Any]:
        """Get guardrail configuration."""
        return self._cost_config.get('guardrails', {})

    def get_tool_for_llm(self) -> List[Dict[str, Any]]:
        """
        Get tool definitions formatted for LLM consumption.

        Returns:
            List of tool definitions in a format suitable for LLM prompts
        """
        llm_tools = []

        for definition in self._definitions.values():
            llm_tools.append({
                "tool_id": definition.tool_id,
                "name": definition.display_name,
                "description": definition.description,
                "cost_tier": definition.cost_tier.value,
                "requires_approval": definition.requires_approval,
                "parameters": definition.input_schema.get('properties', {})
            })

        return llm_tools


# Global registry instance (lazy initialization)
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.

    Returns:
        ToolRegistry singleton instance
    """
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def register_all_tools(registry: Optional[ToolRegistry] = None) -> ToolRegistry:
    """
    Register all available tools with the registry.

    Args:
        registry: Registry to use (creates new if None)

    Returns:
        Registry with all tools registered
    """
    if registry is None:
        registry = get_registry()

    # Import and register all tool modules
    from .conversation_tools import (
        RespondTool, AskQuestionsTool, ProposePlanTool
    )
    from .text_tools import (
        GenerateContentTool, GenerateHeroTitleTool,
        GenerateHeroSectionTool, GenerateHeroClosingTool
    )
    from .illustrator_tools import (
        GeneratePyramidTool, GenerateFunnelTool, GenerateConcentricTool
    )
    from .analytics_tools import GenerateChartTool, GenerateTableTool
    from .deck_tools import CreatePresentationTool, GetPreviewUrlTool, UpdateSlideTool

    # Register conversation tools (LOW cost)
    registry.register(RespondTool())
    registry.register(AskQuestionsTool())
    registry.register(ProposePlanTool())

    # Register text tools (HIGH cost)
    registry.register(GenerateContentTool())
    registry.register(GenerateHeroTitleTool())
    registry.register(GenerateHeroSectionTool())
    registry.register(GenerateHeroClosingTool())

    # Register illustrator tools (MEDIUM cost)
    registry.register(GeneratePyramidTool())
    registry.register(GenerateFunnelTool())
    registry.register(GenerateConcentricTool())

    # Register analytics tools (HIGH cost)
    registry.register(GenerateChartTool())
    registry.register(GenerateTableTool())

    # Register deck tools (MEDIUM cost)
    registry.register(CreatePresentationTool())
    registry.register(GetPreviewUrlTool())
    registry.register(UpdateSlideTool())

    logger.info(f"Registered {len(registry.get_tool_ids())} tools")

    return registry

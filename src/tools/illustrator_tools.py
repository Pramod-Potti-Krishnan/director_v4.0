"""
Illustrator Service Tools for Director Agent v4.0

MEDIUM-cost tools that wrap Illustrator Service v1.0 for visualizations:
- GeneratePyramidTool: Generate pyramid diagrams
- GenerateFunnelTool: Generate funnel diagrams
- GenerateConcentricTool: Generate concentric circle diagrams

These tools require strawman context but not explicit user approval.
"""

from typing import Dict, Any, Optional

from .base_tool import BaseTool, ToolDefinition, ToolResult, CostTier
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class GeneratePyramidTool(BaseTool):
    """
    Tool for generating pyramid diagram visualizations.

    Wraps Illustrator Service v1.0 /v1.0/pyramid/generate endpoint.
    MEDIUM cost - requires strawman context.
    """

    def __init__(self, illustrator_client=None):
        """
        Initialize with optional illustrator client.

        Args:
            illustrator_client: Illustrator service client (injected at runtime)
        """
        self._client = illustrator_client

    def set_client(self, client):
        """Set the illustrator client (for dependency injection)."""
        self._client = client

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="illustrator.generate_pyramid",
            display_name="Generate Pyramid Diagram",
            description=(
                "Generate an AI-powered pyramid diagram visualization. "
                "Suitable for hierarchies, priorities, or layered concepts. "
                "MEDIUM COST: Requires strawman context."
            ),
            cost_tier=CostTier.MEDIUM,
            requires_context=["strawman"],
            requires_approval=False,
            input_schema={
                "type": "object",
                "required": ["topic"],
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic for the pyramid (e.g., 'Organizational Hierarchy')"
                    },
                    "num_levels": {
                        "type": "integer",
                        "minimum": 2,
                        "maximum": 6,
                        "default": 4,
                        "description": "Number of pyramid levels (2-6)"
                    },
                    "target_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific labels for each level (optional)"
                    },
                    "context": {
                        "type": "object",
                        "description": "Presentation context (title, previous slides, etc.)"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "html_content": {"type": "string"},
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "levels_generated": {"type": "integer"},
                            "topic": {"type": "string"}
                        }
                    }
                }
            }
        )

    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        Execute pyramid generation via Illustrator Service.

        Args:
            parameters: Generation parameters (topic, num_levels, target_points)
            context: Session context with presentation info

        Returns:
            ToolResult with generated SVG/HTML content
        """
        if not self._client:
            return ToolResult(
                success=False,
                error="Illustrator service client not configured",
                tool_id=self.tool_id
            )

        try:
            topic = parameters.get('topic')
            num_levels = parameters.get('num_levels', 4)

            logger.info(f"Generating pyramid: topic='{topic}', levels={num_levels}")

            # Build request
            request = {
                "topic": topic,
                "num_levels": num_levels
            }

            if parameters.get('target_points'):
                request['target_points'] = parameters['target_points']

            if parameters.get('context'):
                request['context'] = parameters['context']
            elif context:
                request['context'] = {
                    "presentation_title": context.get('presentation_title', ''),
                    "previous_slides": context.get('previous_slides', [])
                }

            # Call Illustrator Service
            response = await self._call_illustrator(
                endpoint="/v1.0/pyramid/generate",
                request=request
            )

            if not response or 'html_content' not in response:
                return ToolResult(
                    success=False,
                    error="Illustrator Service returned invalid response",
                    tool_id=self.tool_id
                )

            return ToolResult(
                success=True,
                data={
                    "html_content": response['html_content'],
                    "variant_id": "pyramid",
                    "service_type": "llm_generated",
                    "metadata": response.get('metadata', {
                        "levels_generated": num_levels,
                        "topic": topic
                    })
                },
                tool_id=self.tool_id
            )

        except Exception as e:
            logger.error(f"Pyramid generation failed: {e}")
            return ToolResult(
                success=False,
                error=f"Pyramid generation failed: {str(e)}",
                tool_id=self.tool_id
            )

    async def _call_illustrator(
        self,
        endpoint: str,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call Illustrator Service endpoint."""
        if hasattr(self._client, 'generate'):
            return await self._client.generate(endpoint, request)
        elif hasattr(self._client, 'post'):
            return await self._client.post(endpoint, request)
        raise NotImplementedError("Illustrator client not properly configured")


class GenerateFunnelTool(BaseTool):
    """
    Tool for generating funnel diagram visualizations.

    Wraps Illustrator Service v1.0 /v1.0/funnel/generate endpoint.
    MEDIUM cost - requires strawman context.
    """

    def __init__(self, illustrator_client=None):
        self._client = illustrator_client

    def set_client(self, client):
        self._client = client

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="illustrator.generate_funnel",
            display_name="Generate Funnel Diagram",
            description=(
                "Generate an AI-powered funnel diagram visualization. "
                "Suitable for processes, conversions, or filtering stages. "
                "MEDIUM COST: Requires strawman context."
            ),
            cost_tier=CostTier.MEDIUM,
            requires_context=["strawman"],
            requires_approval=False,
            input_schema={
                "type": "object",
                "required": ["topic"],
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic for the funnel (e.g., 'Sales Pipeline')"
                    },
                    "num_stages": {
                        "type": "integer",
                        "minimum": 2,
                        "maximum": 7,
                        "default": 5,
                        "description": "Number of funnel stages (2-7)"
                    },
                    "target_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific labels for each stage (optional)"
                    },
                    "context": {
                        "type": "object",
                        "description": "Presentation context"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "html_content": {"type": "string"},
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "stages_generated": {"type": "integer"},
                            "topic": {"type": "string"}
                        }
                    }
                }
            }
        )

    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """Execute funnel generation via Illustrator Service."""
        if not self._client:
            return ToolResult(
                success=False,
                error="Illustrator service client not configured",
                tool_id=self.tool_id
            )

        try:
            topic = parameters.get('topic')
            num_stages = parameters.get('num_stages', 5)

            logger.info(f"Generating funnel: topic='{topic}', stages={num_stages}")

            request = {
                "topic": topic,
                "num_stages": num_stages
            }

            if parameters.get('target_points'):
                request['target_points'] = parameters['target_points']

            if parameters.get('context'):
                request['context'] = parameters['context']
            elif context:
                request['context'] = {
                    "presentation_title": context.get('presentation_title', ''),
                    "previous_slides": context.get('previous_slides', [])
                }

            response = await self._call_illustrator(
                endpoint="/v1.0/funnel/generate",
                request=request
            )

            if not response or 'html_content' not in response:
                return ToolResult(
                    success=False,
                    error="Illustrator Service returned invalid response",
                    tool_id=self.tool_id
                )

            return ToolResult(
                success=True,
                data={
                    "html_content": response['html_content'],
                    "variant_id": "funnel",
                    "service_type": "llm_generated",
                    "metadata": response.get('metadata', {
                        "stages_generated": num_stages,
                        "topic": topic
                    })
                },
                tool_id=self.tool_id
            )

        except Exception as e:
            logger.error(f"Funnel generation failed: {e}")
            return ToolResult(
                success=False,
                error=f"Funnel generation failed: {str(e)}",
                tool_id=self.tool_id
            )

    async def _call_illustrator(
        self,
        endpoint: str,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call Illustrator Service endpoint."""
        if hasattr(self._client, 'generate'):
            return await self._client.generate(endpoint, request)
        elif hasattr(self._client, 'post'):
            return await self._client.post(endpoint, request)
        raise NotImplementedError("Illustrator client not properly configured")


class GenerateConcentricTool(BaseTool):
    """
    Tool for generating concentric circle diagram visualizations.

    Wraps Illustrator Service v1.0 /v1.0/circles/generate endpoint.
    MEDIUM cost - requires strawman context.
    """

    def __init__(self, illustrator_client=None):
        self._client = illustrator_client

    def set_client(self, client):
        self._client = client

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="illustrator.generate_concentric",
            display_name="Generate Concentric Circles",
            description=(
                "Generate an AI-powered concentric circles diagram. "
                "Suitable for layers of influence, ecosystems, or nested concepts. "
                "MEDIUM COST: Requires strawman context."
            ),
            cost_tier=CostTier.MEDIUM,
            requires_context=["strawman"],
            requires_approval=False,
            input_schema={
                "type": "object",
                "required": ["topic"],
                "properties": {
                    "topic": {
                        "type": "string",
                        "description": "Topic for the diagram (e.g., 'Customer Journey')"
                    },
                    "num_circles": {
                        "type": "integer",
                        "minimum": 2,
                        "maximum": 5,
                        "default": 3,
                        "description": "Number of concentric circles (2-5)"
                    },
                    "target_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific labels for each circle (optional)"
                    },
                    "context": {
                        "type": "object",
                        "description": "Presentation context"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "html_content": {"type": "string"},
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "circles_generated": {"type": "integer"},
                            "topic": {"type": "string"}
                        }
                    }
                }
            }
        )

    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """Execute concentric circles generation via Illustrator Service."""
        if not self._client:
            return ToolResult(
                success=False,
                error="Illustrator service client not configured",
                tool_id=self.tool_id
            )

        try:
            topic = parameters.get('topic')
            num_circles = parameters.get('num_circles', 3)

            logger.info(f"Generating concentric circles: topic='{topic}', circles={num_circles}")

            request = {
                "topic": topic,
                "num_circles": num_circles
            }

            if parameters.get('target_points'):
                request['target_points'] = parameters['target_points']

            if parameters.get('context'):
                request['context'] = parameters['context']
            elif context:
                request['context'] = {
                    "presentation_title": context.get('presentation_title', ''),
                    "previous_slides": context.get('previous_slides', [])
                }

            response = await self._call_illustrator(
                endpoint="/v1.0/circles/generate",
                request=request
            )

            if not response or 'html_content' not in response:
                return ToolResult(
                    success=False,
                    error="Illustrator Service returned invalid response",
                    tool_id=self.tool_id
                )

            return ToolResult(
                success=True,
                data={
                    "html_content": response['html_content'],
                    "variant_id": "concentric_circles",
                    "service_type": "llm_generated",
                    "metadata": response.get('metadata', {
                        "circles_generated": num_circles,
                        "topic": topic
                    })
                },
                tool_id=self.tool_id
            )

        except Exception as e:
            logger.error(f"Concentric circles generation failed: {e}")
            return ToolResult(
                success=False,
                error=f"Concentric circles generation failed: {str(e)}",
                tool_id=self.tool_id
            )

    async def _call_illustrator(
        self,
        endpoint: str,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call Illustrator Service endpoint."""
        if hasattr(self._client, 'generate'):
            return await self._client.generate(endpoint, request)
        elif hasattr(self._client, 'post'):
            return await self._client.post(endpoint, request)
        raise NotImplementedError("Illustrator client not properly configured")

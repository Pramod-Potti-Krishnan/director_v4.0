"""
Text Service Tools for Director Agent v4.0

HIGH-cost tools that wrap Text Service v1.2 for content generation:
- GenerateContentTool: Generate template-based slide content
- GenerateHeroTitleTool: Generate title slide hero content
- GenerateHeroSectionTool: Generate section divider hero content
- GenerateHeroClosingTool: Generate closing slide hero content

These tools require approved strawman and explicit user approval before execution.
"""

import logging
from typing import Dict, Any, Optional

from .base_tool import BaseTool, ToolDefinition, ToolResult, CostTier

logger = logging.getLogger(__name__)


class GenerateContentTool(BaseTool):
    """
    Tool for generating template-based slide content.

    Wraps Text Service v1.2 /v1.2/generate endpoint.
    HIGH cost - requires approved strawman and user approval.
    """

    def __init__(self, text_service_client=None):
        """
        Initialize with optional text service client.

        Args:
            text_service_client: TextServiceClient instance (injected at runtime)
        """
        self._client = text_service_client

    def set_client(self, client):
        """Set the text service client (for dependency injection)."""
        self._client = client

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="text.generate_content",
            display_name="Generate Slide Content",
            description=(
                "Generate HTML content for a slide using Text Service v1.2. "
                "Uses template-based generation with variant_id to select "
                "the content type (comparison, list, process, etc.). "
                "HIGH COST: Requires approved strawman and explicit user approval."
            ),
            cost_tier=CostTier.HIGH,
            requires_context=["strawman"],
            requires_approval=True,
            input_schema={
                "type": "object",
                "required": ["variant_id", "title"],
                "properties": {
                    "variant_id": {
                        "type": "string",
                        "description": "Template variant ID (e.g., 'bilateral_comparison', 'bullet_list')"
                    },
                    "title": {
                        "type": "string",
                        "description": "Slide title",
                        "maxLength": 100
                    },
                    "subtitle": {
                        "type": "string",
                        "description": "Slide subtitle (optional)"
                    },
                    "key_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key points or bullet items"
                    },
                    "narrative": {
                        "type": "string",
                        "description": "Context/narrative for content generation"
                    },
                    "tone": {
                        "type": "string",
                        "enum": ["professional", "casual", "inspirational"],
                        "default": "professional"
                    },
                    "audience": {
                        "type": "string",
                        "description": "Target audience (e.g., 'executives', 'team members')"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "html_content": {"type": "string"},
                    "variant_id": {"type": "string"},
                    "service_type": {"type": "string"}
                }
            }
        )

    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        Execute content generation via Text Service.

        Args:
            parameters: Generation parameters including variant_id, title, etc.
            context: Session context with strawman and presentation info

        Returns:
            ToolResult with generated HTML content
        """
        if not self._client:
            return ToolResult(
                success=False,
                error="Text service client not configured",
                tool_id=self.tool_id
            )

        try:
            variant_id = parameters.get('variant_id')
            title = parameters.get('title')

            logger.info(f"Generating content for variant: {variant_id}, title: {title}")

            # Build request for Text Service
            request = {
                "variant_id": variant_id,
                "title": title
            }

            # Add optional fields
            if parameters.get('subtitle'):
                request['subtitle'] = parameters['subtitle']
            if parameters.get('key_points'):
                request['key_points'] = parameters['key_points']
            if parameters.get('narrative'):
                request['narrative'] = parameters['narrative']
            if parameters.get('tone'):
                request['tone'] = parameters['tone']
            if parameters.get('audience'):
                request['audience'] = parameters['audience']

            # Add context if available
            if context:
                if context.get('presentation_title'):
                    request['presentation_title'] = context['presentation_title']
                if context.get('theme'):
                    request['theme'] = context['theme']

            # Call Text Service (adapter pattern - using unified router)
            # In real implementation, this would go through UnifiedServiceRouter
            response = await self._call_text_service(request)

            if not response or 'html_content' not in response:
                return ToolResult(
                    success=False,
                    error="Text Service returned invalid response",
                    tool_id=self.tool_id
                )

            return ToolResult(
                success=True,
                data={
                    "html_content": response['html_content'],
                    "variant_id": variant_id,
                    "service_type": "template_based"
                },
                tool_id=self.tool_id
            )

        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            return ToolResult(
                success=False,
                error=f"Content generation failed: {str(e)}",
                tool_id=self.tool_id
            )

    async def _call_text_service(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Call Text Service via client."""
        # This will be implemented to use the actual client
        # For now, delegate to adapter pattern
        if hasattr(self._client, 'generate'):
            return await self._client.generate(request)
        raise NotImplementedError("Text service client not properly configured")


class GenerateHeroTitleTool(BaseTool):
    """
    Tool for generating title slide hero content.

    Wraps Text Service v1.2 /v1.2/hero/title endpoint.
    HIGH cost - requires approved strawman and user approval.
    """

    def __init__(self, text_service_client=None):
        self._client = text_service_client

    def set_client(self, client):
        self._client = client

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="text.generate_hero_title",
            display_name="Generate Title Slide",
            description=(
                "Generate hero content for a title slide (slide 1). "
                "Creates visually impactful opening with title, subtitle, and imagery. "
                "HIGH COST: Requires approved strawman and explicit user approval."
            ),
            cost_tier=CostTier.HIGH,
            requires_context=["strawman"],
            requires_approval=True,
            input_schema={
                "type": "object",
                "required": ["slide_number", "narrative"],
                "properties": {
                    "slide_number": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Slide position (usually 1 for title)"
                    },
                    "slide_type": {
                        "type": "string",
                        "enum": ["title_slide"],
                        "default": "title_slide"
                    },
                    "narrative": {
                        "type": "string",
                        "description": "Presentation topic/narrative"
                    },
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key topics to highlight"
                    },
                    "context": {
                        "type": "object",
                        "description": "Theme, audience, and style context"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "html_content": {"type": "string"},
                    "metadata": {"type": "object"}
                }
            }
        )

    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """Generate title slide hero content."""
        if not self._client:
            return ToolResult(
                success=False,
                error="Text service client not configured",
                tool_id=self.tool_id
            )

        try:
            logger.info("Generating title slide hero content")

            payload = {
                "slide_number": parameters.get('slide_number', 1),
                "slide_type": "title_slide",
                "narrative": parameters.get('narrative', ''),
                "topics": parameters.get('topics', [])
            }

            # Add context
            if parameters.get('context'):
                payload['context'] = parameters['context']
            elif context:
                payload['context'] = {
                    "theme": context.get('theme', 'professional'),
                    "audience": context.get('audience', 'general')
                }

            # Call hero endpoint
            response = await self._client.call_hero_endpoint(
                endpoint="/v1.2/hero/title",
                payload=payload
            )

            return ToolResult(
                success=True,
                data={
                    "html_content": response.get('content', ''),
                    "metadata": response.get('metadata', {})
                },
                tool_id=self.tool_id
            )

        except Exception as e:
            logger.error(f"Title slide generation failed: {e}")
            return ToolResult(
                success=False,
                error=f"Title slide generation failed: {str(e)}",
                tool_id=self.tool_id
            )


class GenerateHeroSectionTool(BaseTool):
    """
    Tool for generating section divider hero content.

    Wraps Text Service v1.2 /v1.2/hero/section endpoint.
    HIGH cost - requires approved strawman and user approval.
    """

    def __init__(self, text_service_client=None):
        self._client = text_service_client

    def set_client(self, client):
        self._client = client

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="text.generate_hero_section",
            display_name="Generate Section Divider",
            description=(
                "Generate hero content for a section divider slide. "
                "Creates visual break between presentation sections. "
                "HIGH COST: Requires approved strawman and explicit user approval."
            ),
            cost_tier=CostTier.HIGH,
            requires_context=["strawman"],
            requires_approval=True,
            input_schema={
                "type": "object",
                "required": ["slide_number", "narrative"],
                "properties": {
                    "slide_number": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Slide position"
                    },
                    "slide_type": {
                        "type": "string",
                        "enum": ["section_divider"],
                        "default": "section_divider"
                    },
                    "narrative": {
                        "type": "string",
                        "description": "Section topic/narrative"
                    },
                    "section_title": {
                        "type": "string",
                        "description": "Section title text"
                    },
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key topics in this section"
                    },
                    "context": {
                        "type": "object",
                        "description": "Theme, audience, and style context"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "html_content": {"type": "string"},
                    "metadata": {"type": "object"}
                }
            }
        )

    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """Generate section divider hero content."""
        if not self._client:
            return ToolResult(
                success=False,
                error="Text service client not configured",
                tool_id=self.tool_id
            )

        try:
            logger.info(f"Generating section divider for slide {parameters.get('slide_number')}")

            payload = {
                "slide_number": parameters.get('slide_number', 1),
                "slide_type": "section_divider",
                "narrative": parameters.get('narrative', ''),
                "topics": parameters.get('topics', [])
            }

            if parameters.get('section_title'):
                payload['section_title'] = parameters['section_title']

            # Add context
            if parameters.get('context'):
                payload['context'] = parameters['context']
            elif context:
                payload['context'] = {
                    "theme": context.get('theme', 'professional'),
                    "audience": context.get('audience', 'general')
                }

            response = await self._client.call_hero_endpoint(
                endpoint="/v1.2/hero/section",
                payload=payload
            )

            return ToolResult(
                success=True,
                data={
                    "html_content": response.get('content', ''),
                    "metadata": response.get('metadata', {})
                },
                tool_id=self.tool_id
            )

        except Exception as e:
            logger.error(f"Section divider generation failed: {e}")
            return ToolResult(
                success=False,
                error=f"Section divider generation failed: {str(e)}",
                tool_id=self.tool_id
            )


class GenerateHeroClosingTool(BaseTool):
    """
    Tool for generating closing slide hero content.

    Wraps Text Service v1.2 /v1.2/hero/closing endpoint.
    HIGH cost - requires approved strawman and user approval.
    """

    def __init__(self, text_service_client=None):
        self._client = text_service_client

    def set_client(self, client):
        self._client = client

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="text.generate_hero_closing",
            display_name="Generate Closing Slide",
            description=(
                "Generate hero content for a closing slide (final slide). "
                "Creates memorable ending with call-to-action or summary. "
                "HIGH COST: Requires approved strawman and explicit user approval."
            ),
            cost_tier=CostTier.HIGH,
            requires_context=["strawman"],
            requires_approval=True,
            input_schema={
                "type": "object",
                "required": ["slide_number", "narrative"],
                "properties": {
                    "slide_number": {
                        "type": "integer",
                        "minimum": 1,
                        "description": "Slide position (usually last)"
                    },
                    "slide_type": {
                        "type": "string",
                        "enum": ["closing_slide"],
                        "default": "closing_slide"
                    },
                    "narrative": {
                        "type": "string",
                        "description": "Closing message/call-to-action"
                    },
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key takeaways to reinforce"
                    },
                    "call_to_action": {
                        "type": "string",
                        "description": "Specific call-to-action text"
                    },
                    "context": {
                        "type": "object",
                        "description": "Theme, audience, and style context"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "html_content": {"type": "string"},
                    "metadata": {"type": "object"}
                }
            }
        )

    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """Generate closing slide hero content."""
        if not self._client:
            return ToolResult(
                success=False,
                error="Text service client not configured",
                tool_id=self.tool_id
            )

        try:
            logger.info(f"Generating closing slide for slide {parameters.get('slide_number')}")

            payload = {
                "slide_number": parameters.get('slide_number', 1),
                "slide_type": "closing_slide",
                "narrative": parameters.get('narrative', ''),
                "topics": parameters.get('topics', [])
            }

            if parameters.get('call_to_action'):
                payload['call_to_action'] = parameters['call_to_action']

            # Add context
            if parameters.get('context'):
                payload['context'] = parameters['context']
            elif context:
                payload['context'] = {
                    "theme": context.get('theme', 'professional'),
                    "audience": context.get('audience', 'general')
                }

            response = await self._client.call_hero_endpoint(
                endpoint="/v1.2/hero/closing",
                payload=payload
            )

            return ToolResult(
                success=True,
                data={
                    "html_content": response.get('content', ''),
                    "metadata": response.get('metadata', {})
                },
                tool_id=self.tool_id
            )

        except Exception as e:
            logger.error(f"Closing slide generation failed: {e}")
            return ToolResult(
                success=False,
                error=f"Closing slide generation failed: {str(e)}",
                tool_id=self.tool_id
            )

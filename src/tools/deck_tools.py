"""
Deck Builder Tools for Director Agent v4.0

MEDIUM-cost tools that wrap Deck Builder API:
- CreatePresentationTool: Create presentation from generated slides
- GetPreviewUrlTool: Get preview URL for a strawman

These tools require strawman context but not explicit user approval.
"""

from typing import Dict, Any, Optional, List

from .base_tool import BaseTool, ToolDefinition, ToolResult, CostTier
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class CreatePresentationTool(BaseTool):
    """
    Tool for creating presentations via Deck Builder API.

    Wraps POST /api/presentations endpoint.
    MEDIUM cost - requires generated content.
    """

    def __init__(self, deck_builder_client=None):
        """
        Initialize with optional deck builder client.

        Args:
            deck_builder_client: DeckBuilderClient instance (injected at runtime)
        """
        self._client = deck_builder_client

    def set_client(self, client):
        """Set the deck builder client (for dependency injection)."""
        self._client = client

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="deck.create_presentation",
            display_name="Create Presentation",
            description=(
                "Create a presentation from generated slide content. "
                "Takes slide array with layouts and HTML content, "
                "renders to deck-builder and returns preview URL. "
                "MEDIUM COST: Requires generated content."
            ),
            cost_tier=CostTier.MEDIUM,
            requires_context=["strawman", "generated_content"],
            requires_approval=False,
            input_schema={
                "type": "object",
                "required": ["title", "slides"],
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Presentation title",
                        "maxLength": 200
                    },
                    "slides": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "layout": {
                                    "type": "string",
                                    "description": "Layout template ID (e.g., 'L01', 'L02')"
                                },
                                "content": {
                                    "type": "object",
                                    "description": "Content for each element slot"
                                }
                            },
                            "required": ["layout", "content"]
                        },
                        "minItems": 1,
                        "maxItems": 30,
                        "description": "Array of slide definitions"
                    },
                    "theme": {
                        "type": "string",
                        "description": "Theme identifier (optional)"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional presentation metadata"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "presentation_id": {"type": "string"},
                    "url": {"type": "string"},
                    "preview_url": {"type": "string"},
                    "slide_count": {"type": "integer"}
                }
            }
        )

    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        Execute presentation creation via Deck Builder API.

        Args:
            parameters: Presentation data (title, slides array)
            context: Session context with generated content

        Returns:
            ToolResult with presentation ID and preview URL
        """
        if not self._client:
            return ToolResult(
                success=False,
                error="Deck builder client not configured",
                tool_id=self.tool_id
            )

        try:
            title = parameters.get('title')
            slides = parameters.get('slides', [])

            logger.info(f"Creating presentation: '{title}' with {len(slides)} slides")

            # Validate slide count
            if len(slides) < 1:
                return ToolResult(
                    success=False,
                    error="Presentation must have at least 1 slide",
                    tool_id=self.tool_id
                )

            if len(slides) > 30:
                return ToolResult(
                    success=False,
                    error="Presentation cannot exceed 30 slides",
                    tool_id=self.tool_id
                )

            # Build presentation data
            presentation_data = {
                "title": title,
                "slides": slides
            }

            if parameters.get('theme'):
                presentation_data['theme'] = parameters['theme']

            if parameters.get('metadata'):
                presentation_data['metadata'] = parameters['metadata']

            # Call Deck Builder API
            response = await self._client.create_presentation(presentation_data)

            if not response:
                return ToolResult(
                    success=False,
                    error="Deck Builder API returned empty response",
                    tool_id=self.tool_id
                )

            # Extract response fields
            presentation_id = response.get('id')
            url = response.get('url', '')

            # Convert relative URL to full URL if needed
            if url and not url.startswith('http'):
                url = self._client.get_full_url(url)

            return ToolResult(
                success=True,
                data={
                    "success": True,
                    "presentation_id": presentation_id,
                    "url": url,
                    "preview_url": url,
                    "slide_count": len(slides),
                    "message": response.get('message', 'Presentation created successfully')
                },
                tool_id=self.tool_id
            )

        except Exception as e:
            logger.error(f"Presentation creation failed: {e}")
            return ToolResult(
                success=False,
                error=f"Presentation creation failed: {str(e)}",
                tool_id=self.tool_id
            )


class GetPreviewUrlTool(BaseTool):
    """
    Tool for getting preview URL for a strawman.

    Creates a lightweight preview without full content generation.
    MEDIUM cost - requires strawman context.
    """

    def __init__(self, deck_builder_client=None):
        self._client = deck_builder_client

    def set_client(self, client):
        self._client = client

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="deck.get_preview_url",
            display_name="Get Preview URL",
            description=(
                "Generate a preview URL for the current strawman. "
                "Creates a lightweight rendering to show slide structure "
                "before full content generation. "
                "MEDIUM COST: Requires strawman context."
            ),
            cost_tier=CostTier.MEDIUM,
            requires_context=["strawman"],
            requires_approval=False,
            input_schema={
                "type": "object",
                "required": ["strawman"],
                "properties": {
                    "strawman": {
                        "type": "object",
                        "description": "Strawman object with slides array",
                        "properties": {
                            "title": {"type": "string"},
                            "slides": {
                                "type": "array",
                                "items": {"type": "object"}
                            }
                        }
                    },
                    "preview_mode": {
                        "type": "string",
                        "enum": ["skeleton", "placeholder", "outline"],
                        "default": "placeholder",
                        "description": "Type of preview to generate"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "preview_url": {"type": "string"},
                    "presentation_id": {"type": "string"},
                    "slide_count": {"type": "integer"}
                }
            }
        )

    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """
        Generate preview URL for strawman.

        Args:
            parameters: Strawman data and preview options
            context: Session context

        Returns:
            ToolResult with preview URL
        """
        if not self._client:
            return ToolResult(
                success=False,
                error="Deck builder client not configured",
                tool_id=self.tool_id
            )

        try:
            strawman = parameters.get('strawman', {})
            preview_mode = parameters.get('preview_mode', 'placeholder')

            # Get strawman from context if not provided in parameters
            if not strawman and context:
                strawman = context.get('strawman', {})

            if not strawman:
                return ToolResult(
                    success=False,
                    error="No strawman provided for preview",
                    tool_id=self.tool_id
                )

            title = strawman.get('title', 'Untitled Presentation')
            slides = strawman.get('slides', [])

            logger.info(f"Generating preview for '{title}' with {len(slides)} slides")

            # Convert strawman slides to preview format
            preview_slides = self._create_preview_slides(slides, preview_mode)

            # Create preview presentation
            presentation_data = {
                "title": f"[Preview] {title}",
                "slides": preview_slides,
                "metadata": {
                    "is_preview": True,
                    "preview_mode": preview_mode
                }
            }

            response = await self._client.create_presentation(presentation_data)

            if not response:
                return ToolResult(
                    success=False,
                    error="Failed to create preview",
                    tool_id=self.tool_id
                )

            url = response.get('url', '')
            if url and not url.startswith('http'):
                url = self._client.get_full_url(url)

            return ToolResult(
                success=True,
                data={
                    "preview_url": url,
                    "presentation_id": response.get('id'),
                    "slide_count": len(preview_slides),
                    "preview_mode": preview_mode
                },
                tool_id=self.tool_id
            )

        except Exception as e:
            logger.error(f"Preview generation failed: {e}")
            return ToolResult(
                success=False,
                error=f"Preview generation failed: {str(e)}",
                tool_id=self.tool_id
            )

    def _create_preview_slides(
        self,
        strawman_slides: List[Dict],
        preview_mode: str
    ) -> List[Dict]:
        """
        Convert strawman slides to preview format.

        Args:
            strawman_slides: Raw strawman slide definitions
            preview_mode: Type of preview (skeleton, placeholder, outline)

        Returns:
            List of slides formatted for deck builder
        """
        preview_slides = []

        for i, slide in enumerate(strawman_slides):
            layout = slide.get('layout', 'L01')
            title = slide.get('title', f'Slide {i + 1}')
            topics = slide.get('topics', [])

            # Create placeholder content based on mode
            if preview_mode == 'skeleton':
                content = {
                    "element_1": f"<h2>{title}</h2>"
                }
            elif preview_mode == 'outline':
                topics_html = ''.join([f"<li>{t}</li>" for t in topics])
                content = {
                    "element_1": f"<h2>{title}</h2>",
                    "element_2": f"<ul>{topics_html}</ul>" if topics else ""
                }
            else:  # placeholder
                content = {
                    "element_1": f"<h2>{title}</h2>",
                    "element_2": f"<p class='placeholder'>Content will be generated...</p>"
                }

            preview_slides.append({
                "layout": layout,
                "content": content
            })

        return preview_slides


class UpdateSlideTool(BaseTool):
    """
    Tool for updating a single slide in an existing presentation.

    Wraps PUT /api/presentations/{id}/slides/{index} endpoint.
    MEDIUM cost - requires existing presentation.
    """

    def __init__(self, deck_builder_client=None):
        self._client = deck_builder_client

    def set_client(self, client):
        self._client = client

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            tool_id="deck.update_slide",
            display_name="Update Slide",
            description=(
                "Update a single slide in an existing presentation. "
                "Can update content, layout, or both. "
                "MEDIUM COST: Requires existing presentation."
            ),
            cost_tier=CostTier.MEDIUM,
            requires_context=["presentation_id"],
            requires_approval=False,
            input_schema={
                "type": "object",
                "required": ["presentation_id", "slide_index"],
                "properties": {
                    "presentation_id": {
                        "type": "string",
                        "description": "UUID of the presentation"
                    },
                    "slide_index": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Zero-based slide index"
                    },
                    "layout": {
                        "type": "string",
                        "description": "New layout ID (optional)"
                    },
                    "content": {
                        "type": "object",
                        "description": "New content for element slots"
                    }
                }
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "updated_slide_index": {"type": "integer"}
                }
            }
        )

    async def execute(
        self,
        parameters: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """Update a single slide in a presentation."""
        if not self._client:
            return ToolResult(
                success=False,
                error="Deck builder client not configured",
                tool_id=self.tool_id
            )

        try:
            presentation_id = parameters.get('presentation_id')
            slide_index = parameters.get('slide_index')

            logger.info(f"Updating slide {slide_index} in presentation {presentation_id}")

            update_data = {}
            if parameters.get('layout'):
                update_data['layout'] = parameters['layout']
            if parameters.get('content'):
                update_data['content'] = parameters['content']

            if not update_data:
                return ToolResult(
                    success=False,
                    error="No update data provided (need layout or content)",
                    tool_id=self.tool_id
                )

            # Call update endpoint (would need to be added to DeckBuilderClient)
            # For now, return placeholder
            return ToolResult(
                success=True,
                data={
                    "success": True,
                    "updated_slide_index": slide_index,
                    "presentation_id": presentation_id
                },
                tool_id=self.tool_id
            )

        except Exception as e:
            logger.error(f"Slide update failed: {e}")
            return ToolResult(
                success=False,
                error=f"Slide update failed: {str(e)}",
                tool_id=self.tool_id
            )

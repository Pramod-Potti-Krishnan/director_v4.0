"""
Tools Package for Director Agent v4.0

MCP-style tools that wrap external services and internal functionality.

Tool Categories by Cost Tier:
- LOW: Conversation tools (respond, ask_questions, propose_plan)
- MEDIUM: Illustrator tools (pyramid, funnel, concentric), Deck tools (create, preview)
- HIGH: Text tools (content, hero slides), Analytics tools (charts, tables)
"""

from .base_tool import (
    BaseTool,
    ToolDefinition,
    ToolResult,
    ToolCall,
    CostTier,
    ToolExecutionError,
    ToolValidationError,
    ToolPrerequisiteError
)

from .registry import (
    ToolRegistry,
    get_registry,
    register_all_tools
)

from .conversation_tools import (
    RespondTool,
    AskQuestionsTool,
    ProposePlanTool
)

from .text_tools import (
    GenerateContentTool,
    GenerateHeroTitleTool,
    GenerateHeroSectionTool,
    GenerateHeroClosingTool
)

from .illustrator_tools import (
    GeneratePyramidTool,
    GenerateFunnelTool,
    GenerateConcentricTool
)

from .analytics_tools import (
    GenerateChartTool,
    GenerateTableTool
)

from .deck_tools import (
    CreatePresentationTool,
    GetPreviewUrlTool,
    UpdateSlideTool
)

__all__ = [
    # Base classes
    'BaseTool',
    'ToolDefinition',
    'ToolResult',
    'ToolCall',
    'CostTier',
    'ToolExecutionError',
    'ToolValidationError',
    'ToolPrerequisiteError',

    # Registry
    'ToolRegistry',
    'get_registry',
    'register_all_tools',

    # Conversation tools (LOW cost)
    'RespondTool',
    'AskQuestionsTool',
    'ProposePlanTool',

    # Text tools (HIGH cost)
    'GenerateContentTool',
    'GenerateHeroTitleTool',
    'GenerateHeroSectionTool',
    'GenerateHeroClosingTool',

    # Illustrator tools (MEDIUM cost)
    'GeneratePyramidTool',
    'GenerateFunnelTool',
    'GenerateConcentricTool',

    # Analytics tools (HIGH cost)
    'GenerateChartTool',
    'GenerateTableTool',

    # Deck tools (MEDIUM cost)
    'CreatePresentationTool',
    'GetPreviewUrlTool',
    'UpdateSlideTool'
]

"""
Decision Engine for Director Agent v4.0

Single AI agent that analyzes conversation context and decides what action to take.
Replaces the rigid 6-stage state machine with flexible, context-driven decisions.

Uses:
- Pydantic-AI with Gemini via Vertex AI
- Guidance system (markdown files) for best practices
- Tool registry for available actions
- Cost control rules for guardrails
"""

import os
import json
import random
from typing import Dict, Any, Optional, List
from pathlib import Path
from pydantic_ai import Agent

from src.models.decision import (
    DecisionOutput, DecisionContext, ActionType,
    ToolCallRequest, ApprovalDetectionResult,
    Strawman, StrawmanSlide, PresentationPlan
)
from src.models.layout import LayoutRecommendation
from src.models.content_hints import ContentHints
from src.tools.registry import ToolRegistry, get_registry
from src.utils.logger import setup_logger
from config.settings import get_settings

logger = setup_logger(__name__)


class DecisionEngine:
    """
    AI-driven decision engine for Director Agent v4.0.

    Analyzes conversation context and decides:
    - What action to take (respond, ask questions, generate content, etc.)
    - Which tools to invoke (if any)
    - What response to give the user

    Guided by:
    - director_guidance.md (best practices)
    - cost_control_rules.md (guardrails)
    - Tool registry (available actions)
    """

    def __init__(
        self,
        tool_registry: Optional[ToolRegistry] = None,
        model_name: str = "gemini-2.5-flash"
    ):
        """
        Initialize the Decision Engine.

        Args:
            tool_registry: Registry of available tools (uses global if None)
            model_name: Gemini model to use for decisions
        """
        self.tool_registry = tool_registry or get_registry()
        self.model_name = model_name

        # Load guidance system
        self.guidance = self._load_guidance()
        self.cost_rules = self._load_cost_rules()
        self.approval_phrases = self.tool_registry.get_approval_phrases()

        # Build system prompt from guidance
        self.system_prompt = self._build_system_prompt()

        # Initialize Pydantic-AI agent
        self._init_agent()

        logger.info(f"DecisionEngine initialized with model: {model_name}")
        logger.info(f"  - Tools available: {len(self.tool_registry.get_tool_ids())}")
        logger.info(f"  - Guidance loaded: {len(self.guidance)} chars")

    def _load_guidance(self) -> str:
        """Load director guidance from markdown file."""
        base_dir = Path(__file__).parent.parent.parent
        guidance_path = base_dir / "config" / "guidance" / "director_guidance.md"

        try:
            if guidance_path.exists():
                with open(guidance_path, 'r') as f:
                    return f.read()
            else:
                logger.warning(f"Guidance file not found: {guidance_path}")
                return self._default_guidance()
        except Exception as e:
            logger.error(f"Failed to load guidance: {e}")
            return self._default_guidance()

    def _load_cost_rules(self) -> str:
        """Load cost control rules from markdown file."""
        base_dir = Path(__file__).parent.parent.parent
        rules_path = base_dir / "config" / "guidance" / "cost_control_rules.md"

        try:
            if rules_path.exists():
                with open(rules_path, 'r') as f:
                    return f.read()
            else:
                logger.warning(f"Cost rules file not found: {rules_path}")
                return self._default_cost_rules()
        except Exception as e:
            logger.error(f"Failed to load cost rules: {e}")
            return self._default_cost_rules()

    def _default_guidance(self) -> str:
        """Default guidance if file not found."""
        return """
## Default Guidance
- Be helpful and conversational
- Ask clarifying questions when topic is vague
- Generate content only with explicit approval
- Follow best practices for presentation structure
"""

    def _default_cost_rules(self) -> str:
        """Default cost rules if file not found."""
        return """
## Default Cost Rules
- Never call HIGH cost tools without explicit approval
- Explicit approval phrases: "generate", "create it", "proceed"
- Soft approval phrases (need confirmation): "looks good", "yes", "ok"
"""

    def _build_system_prompt(self) -> str:
        """Build the system prompt from guidance and tool definitions."""
        tools_summary = self._get_tools_summary()

        return f"""You are the Director Agent, an AI assistant that helps users create professional presentations.

## CRITICAL: CONTEXT EXTRACTION RULES (HIGHEST PRIORITY - READ FIRST!)
**You MUST populate extracted_context for EVERY response. This is MANDATORY.**

When the user provides ANY information, you MUST extract it into extracted_context:

**Topic Extraction (MOST IMPORTANT):**
- If user mentions ANY subject (e.g., "Sri Krishna", "Machine Learning", "Sales Report", "Elephants"), you MUST set:
  - extracted_context.topic = "the exact topic the user mentioned"
  - extracted_context.has_topic = true

**Example:**
User says: "Sri Krishna"
You MUST return in extracted_context:
- topic = "Sri Krishna"
- has_topic = true

User says: "I want to create a presentation about elephants"
You MUST return in extracted_context:
- topic = "elephants"
- has_topic = true

**NEVER acknowledge a topic in your response_text without ALSO setting extracted_context.topic!**
If you write "Great! 'X' is a fascinating topic" in response_text, you MUST set extracted_context.topic = "X".

## YOUR ROLE
You analyze user messages and conversation context to decide what action to take next.
You have access to various tools (services) that can generate content, but you must use them wisely.

## GUIDANCE
{self.guidance}

## COST CONTROL
{self.cost_rules}

## AVAILABLE TOOLS
{tools_summary}

## DECISION RULES
1. Always analyze the context before deciding
2. Prefer conversation (LOW cost) over generation (HIGH cost) when uncertain
3. Never invoke HIGH cost tools without explicit user approval
4. Ask clarifying questions if the request is vague
5. Propose a plan before generating content
6. Be helpful and professional

## OUTPUT FORMAT
You must return a structured decision with:
- action_type: What to do (respond, ask_questions, propose_plan, generate_strawman, invoke_tools, complete)
- response_text: Text for the user (if applicable)
- tool_calls: Tools to invoke (if action_type is invoke_tools)
- reasoning: Why you chose this action
- confidence: How confident you are (0.0-1.0)
- extracted_context: IMPORTANT! Extract and return any new information from the user's message:
  - topic: The presentation topic (if mentioned)
  - audience: The target audience (if mentioned)
  - duration: Duration in minutes (if mentioned, e.g., "10 minutes" -> 10)
  - purpose: The goal (inform, persuade, inspire, teach, etc.)
  - tone: Desired style (professional, casual, inspiring, etc.)
  - has_topic: true if user provided a topic
  - has_audience: true if user mentioned who the audience is
  - has_duration: true if user specified duration/length
  - has_purpose: true if user stated the goal/purpose
  - slide_count: Explicit slide count if user specifies (e.g., "I need 20 slides" -> 20)
  - has_explicit_slide_count: true if user explicitly specified slide count
  - audience_preset: Map audience to preset (see below)
  - purpose_preset: Map purpose to preset (see below)
  - time_preset: Map duration to preset (see below)

## v4.5: SMART CONTEXT EXTRACTION (CRITICAL!)

### SLIDE COUNT PARSING
If user explicitly specifies slide count, extract it:
- "I need 20 slides" → slide_count=20, has_explicit_slide_count=true
- "make it 15 slides max" → slide_count=15, has_explicit_slide_count=true
- "about 10 slides" → slide_count=10, has_explicit_slide_count=true
- "create a 12-slide presentation" → slide_count=12, has_explicit_slide_count=true

### AUDIENCE PRESET MAPPING
Map user's audience description to the closest preset:
- "for my team" / "internal meeting" / "colleagues" → audience_preset="professional"
- "board meeting" / "C-suite" / "executives" / "leadership" → audience_preset="executive"
- "investors" / "VCs" / "fundraising" → audience_preset="executive"
- "kindergarten" / "kids" / "children" / "young children" → audience_preset="kids_young"
- "middle school" / "tweens" → audience_preset="middle_school"
- "high school" / "teenagers" → audience_preset="high_school"
- "college" / "university" / "students" → audience_preset="college"
- "training" / "workshop" / "new hires" → audience_preset="professional"
- "general public" / "everyone" → audience_preset="general"

### PURPOSE PRESET MAPPING
Map user's purpose/goal to the closest preset:
- "pitch" / "sell" / "convince" / "persuade" → purpose_preset="persuade"
- "teach" / "training" / "explain" / "educate" → purpose_preset="educate"
- "update" / "status" / "report" / "share information" → purpose_preset="inform"
- "inspire" / "motivate" / "rally" → purpose_preset="inspire"
- "QBR" / "quarterly review" / "quarterly business review" → purpose_preset="qbr"
- "entertain" / "fun" / "engage" → purpose_preset="entertain"

### TIME/DURATION PRESET MAPPING
Map user's time/duration description to preset:
- "quick" / "5 minutes" / "lightning" / "brief" → time_preset="lightning"
- "10 minutes" / "short" → time_preset="quick"
- "15-20 minutes" / "standard" / "regular" → time_preset="standard"
- "30 minutes" / "deep dive" / "detailed" → time_preset="extended"
- "45 minutes" / "comprehensive" / "thorough" → time_preset="comprehensive"

## v4.5: CONTEXTUAL QUESTIONS (Don't Be a Broken Record!)

BEFORE asking a question, check what you already know from context:

1. If user said "board meeting" → DON'T ask about audience (infer: executive)
2. If user said "15 minute presentation" → DON'T ask about duration (infer: standard)
3. If user said "training for new hires" → DON'T ask about purpose (infer: educate)
4. If user said "pitch deck" → DON'T ask about purpose (infer: persuade)
5. If user said "for kids" → DON'T ask about audience (infer: kids_young/kids_older)

ONLY ask what's genuinely unclear. Use CONTEXTUAL questions:

✗ BAD: "Who is your audience?" (generic, robotic)
✓ GOOD: "For your board meeting, should this be a quick 10-minute update or a detailed 30-minute review?"

✗ BAD: "What is the purpose of this presentation?" (always same question)
✓ GOOD: "Should we focus on persuading them to approve the budget, or informing them about progress?"

✗ BAD: "How long should the presentation be?" (generic)
✓ GOOD: "Since this is for executives, would you prefer a concise 10-minute overview or a comprehensive 20-minute deep dive?"

## CRITICAL RULES FOR CONTEXT EXTRACTION
1. When user says "make your assumptions" or similar, set has_audience=true, has_duration=true, has_purpose=true
2. When user provides ANY topic, set has_topic=true and extract the topic
3. Don't keep asking questions if user has provided enough context
4. After 1-2 rounds of questions, proceed to propose_plan if you have a topic
5. If user says "just create something" or "make assumptions", proceed without more questions
6. v4.5: ALWAYS extract slide_count if user explicitly mentions slide count
7. v4.5: ALWAYS map audience/purpose/time to presets when they can be inferred
8. v4.5: If you can INFER something from context, DON'T ask about it
"""

    def _get_tools_summary(self) -> str:
        """Get a summary of available tools for the prompt."""
        tools = self.tool_registry.get_tool_for_llm()
        lines = []

        for tool in tools:
            tier_marker = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(tool['cost_tier'], "⚪")
            approval = " [REQUIRES APPROVAL]" if tool['requires_approval'] else ""
            lines.append(f"{tier_marker} {tool['tool_id']}: {tool['description']}{approval}")

        return "\n".join(lines)

    def _init_agent(self):
        """Initialize the Pydantic-AI agent."""
        try:
            # v3.3 style: Use Vertex AI with ADC
            from src.utils.gcp_auth import initialize_vertex_ai

            # Initialize Vertex AI
            initialize_vertex_ai()

            # Create agent with Vertex AI model
            model_id = f"google-vertex:{self.model_name}"

            self.agent = Agent(
                model=model_id,
                system_prompt=self.system_prompt,
                output_type=DecisionOutput
            )

            logger.info(f"Decision Agent initialized with Vertex AI model: {model_id}")

        except Exception as e:
            logger.error(f"Failed to initialize Decision Agent: {e}")
            # Create a fallback agent that returns safe defaults
            self.agent = None
            logger.warning("Decision Engine running in fallback mode")

    async def decide(
        self,
        context: DecisionContext
    ) -> DecisionOutput:
        """
        Analyze context and decide what action to take.

        Args:
            context: Current conversation and session context

        Returns:
            DecisionOutput with the chosen action and details
        """
        # First, detect if user is giving approval
        approval_result = self._detect_approval(context.user_message)

        # Update context with approval detection
        if approval_result.is_explicit_approval:
            context.has_explicit_approval = True

        # Build the prompt for the agent
        prompt = self._build_decision_prompt(context, approval_result)

        # If agent is available, use it
        if self.agent:
            try:
                from src.utils.vertex_retry import call_with_retry

                # Call agent with retry logic for 429 errors
                # Note: call_with_retry expects a callable with no args
                result = await call_with_retry(
                    lambda: self.agent.run(prompt),
                    operation_name="Decision Engine"
                )
                # Pydantic-AI 1.0+: use .output instead of .data
                decision = result.output

                # Validate and adjust decision based on rules
                decision = self._validate_decision(decision, context)

                return decision

            except Exception as e:
                logger.error(f"Decision agent failed: {e}")
                return self._fallback_decision(context, str(e))
        else:
            return self._fallback_decision(context, "Agent not initialized")

    def _build_decision_prompt(
        self,
        context: DecisionContext,
        approval_result: ApprovalDetectionResult
    ) -> str:
        """Build the prompt for the decision agent."""
        parts = [
            f"## USER MESSAGE\n{context.user_message}",
            f"\n## APPROVAL STATUS\n- Explicit approval: {approval_result.is_explicit_approval}",
            f"- Soft approval: {approval_result.is_soft_approval}",
            f"- Matched phrase: {approval_result.matched_phrase or 'None'}",
        ]

        # Add session state
        parts.append("\n## SESSION STATE")
        parts.append(f"- Has topic: {context.has_topic}")
        parts.append(f"- Has audience: {context.has_audience}")
        parts.append(f"- Has duration: {context.has_duration}")
        parts.append(f"- Has purpose: {context.has_purpose}")
        parts.append(f"- Has plan: {context.has_plan}")
        parts.append(f"- Has strawman: {context.has_strawman}")
        parts.append(f"- Has explicit approval: {context.has_explicit_approval}")
        parts.append(f"- Has content: {context.has_content}")

        # Add key session data
        if context.topic:
            parts.append(f"\n## TOPIC\n{context.topic}")
        if context.audience:
            parts.append(f"\n## AUDIENCE\n{context.audience}")
        if context.strawman:
            parts.append(f"\n## STRAWMAN\n{json.dumps(context.strawman, indent=2)[:1000]}...")

        # Add conversation history (last 5 turns)
        if context.conversation_history:
            parts.append("\n## RECENT CONVERSATION")
            for turn in context.conversation_history[-5:]:
                parts.append(f"[{turn.role}]: {turn.content[:200]}...")

        parts.append("\n## TASK\nAnalyze the above context and decide what action to take.")

        return "\n".join(parts)

    def _detect_approval(self, message: str) -> ApprovalDetectionResult:
        """Detect if user message contains approval."""
        message_lower = message.lower().strip()

        # Check explicit approval phrases
        explicit_phrases = self.approval_phrases.get('explicit_approval', [])
        for phrase in explicit_phrases:
            if phrase.lower() in message_lower:
                return ApprovalDetectionResult(
                    is_explicit_approval=True,
                    is_soft_approval=False,
                    confidence=0.95,
                    matched_phrase=phrase
                )

        # Check soft approval phrases (need confirmation)
        soft_phrases = self.approval_phrases.get('not_approval', [])
        for phrase in soft_phrases:
            if message_lower == phrase.lower() or message_lower.startswith(phrase.lower()):
                return ApprovalDetectionResult(
                    is_explicit_approval=False,
                    is_soft_approval=True,
                    confidence=0.7,
                    matched_phrase=phrase
                )

        return ApprovalDetectionResult(
            is_explicit_approval=False,
            is_soft_approval=False,
            confidence=0.5,
            matched_phrase=None
        )

    def _validate_decision(
        self,
        decision: DecisionOutput,
        context: DecisionContext
    ) -> DecisionOutput:
        """
        Validate and potentially adjust the decision based on rules.

        Enforces cost control and prerequisite rules.
        """
        # Rule: Never invoke HIGH cost tools without explicit approval
        if decision.action_type == ActionType.INVOKE_TOOLS and decision.tool_calls:
            if not context.has_explicit_approval:
                # Check if any tool requires approval
                for call in decision.tool_calls:
                    if self.tool_registry.requires_approval(call.tool_id):
                        logger.warning(
                            f"Blocked HIGH cost tool {call.tool_id} - no approval"
                        )
                        # Convert to asking for approval
                        decision.action_type = ActionType.RESPOND
                        decision.response_text = (
                            "I'm ready to generate the presentation content. "
                            "Would you like me to proceed? (Say 'generate' or 'create it' to confirm)"
                        )
                        decision.tool_calls = None
                        decision.reasoning += " [BLOCKED: Required approval not given]"
                        break

        # Rule: Need strawman before invoking content tools
        if decision.action_type == ActionType.INVOKE_TOOLS and decision.tool_calls:
            if not context.has_strawman:
                # Check if tools require strawman
                for call in decision.tool_calls:
                    tool_def = self.tool_registry.get_definition(call.tool_id)
                    if tool_def and "strawman" in tool_def.requires_context:
                        logger.warning(
                            f"Blocked tool {call.tool_id} - no strawman"
                        )
                        decision.action_type = ActionType.GENERATE_STRAWMAN
                        decision.response_text = (
                            "Let me first create an outline (strawman) for your presentation "
                            "before generating the actual content."
                        )
                        decision.tool_calls = None
                        decision.reasoning += " [BLOCKED: Strawman required first]"
                        break

        return decision

    def _fallback_decision(
        self,
        context: DecisionContext,
        error: str
    ) -> DecisionOutput:
        """
        Generate a safe fallback decision when agent fails.

        Uses simple rules to determine a reasonable action.
        """
        logger.warning(f"Using fallback decision due to: {error}")

        # Simple rule-based fallback
        if not context.has_topic:
            return DecisionOutput(
                action_type=ActionType.ASK_QUESTIONS,
                response_text="I'd love to help you create a presentation! What topic would you like to cover?",
                questions=["What is the topic of your presentation?"],
                reasoning=f"Fallback: No topic provided. Error: {error}",
                confidence=0.5
            )

        if not context.has_strawman:
            return DecisionOutput(
                action_type=ActionType.GENERATE_STRAWMAN,
                response_text="Let me create an outline for your presentation.",
                reasoning=f"Fallback: Need to generate strawman. Error: {error}",
                confidence=0.5
            )

        if context.has_strawman and not context.has_content:
            if context.has_explicit_approval:
                return DecisionOutput(
                    action_type=ActionType.INVOKE_TOOLS,
                    response_text="Generating your presentation content now...",
                    tool_calls=[],  # Would need to populate based on strawman
                    reasoning=f"Fallback: Ready to generate content. Error: {error}",
                    confidence=0.5
                )
            else:
                return DecisionOutput(
                    action_type=ActionType.RESPOND,
                    response_text=(
                        "Your presentation outline is ready! "
                        "Say 'generate' when you'd like me to create the actual content."
                    ),
                    reasoning=f"Fallback: Waiting for approval. Error: {error}",
                    confidence=0.5
                )

        return DecisionOutput(
            action_type=ActionType.RESPOND,
            response_text="How can I help you with your presentation?",
            reasoning=f"Fallback: Default response. Error: {error}",
            confidence=0.3
        )

    def get_guardrails(self) -> Dict[str, Any]:
        """Get guardrail configuration."""
        return self.tool_registry.get_guardrails()


class StrawmanGenerator:
    """
    Helper for generating presentation strawmans (outlines).

    Uses AI to create slide structure based on topic and context.

    v4.0.25: Story-driven multi-service coordination with two-step process:
    - Step 1: Generate storyline with AI (slide_type_hint, purpose)
    - Step 2: Apply Layout Analysis (layout, service, variant strategy)

    v4.0.24: Added Layout Service coordination support.
    When USE_LAYOUT_SERVICE_COORDINATION is enabled, layouts and variants
    are selected dynamically via the Layout Service instead of hardcoded L25/L29.
    """

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        self._init_agent()

        # v4.0.24: Layout Service coordination
        self.settings = get_settings()
        self.layout_client = None
        if self.settings.USE_LAYOUT_SERVICE_COORDINATION:
            try:
                from src.clients.layout_service_client import LayoutServiceClient
                self.layout_client = LayoutServiceClient()
                logger.info("StrawmanGenerator: Layout Service coordination enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize Layout Service client: {e}")

        # v4.0.25: Layout Analyzer for story-driven routing
        self.layout_analyzer = None
        try:
            from src.core.layout_analyzer import LayoutAnalyzer, LayoutSeriesMode
            series_mode_str = getattr(self.settings, 'LAYOUT_SERIES_MODE', 'L_ONLY')
            series_mode = LayoutSeriesMode(series_mode_str)
            self.layout_analyzer = LayoutAnalyzer(series_mode=series_mode)
            logger.info(f"StrawmanGenerator: LayoutAnalyzer initialized with mode={series_mode_str}")
        except Exception as e:
            logger.warning(f"Failed to initialize LayoutAnalyzer: {e}")

        # v4.0: Content analyzer and Text Service coordination
        self.content_analyzer = None
        self.text_coord_client = None
        if self.settings.USE_TEXT_SERVICE_COORDINATION:
            try:
                from src.core.content_analyzer import ContentAnalyzer
                from src.clients.text_service_coordination import TextServiceCoordinationClient
                self.content_analyzer = ContentAnalyzer()
                self.text_coord_client = TextServiceCoordinationClient()
                logger.info("StrawmanGenerator: Text Service coordination enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize Text Service coordination: {e}")

        # v4.1: Playbook system for pre-defined presentation structures
        self.playbook_manager = None
        self.playbook_merger = None
        if getattr(self.settings, 'USE_PLAYBOOK_SYSTEM', True):
            try:
                from src.core.playbook_manager import PlaybookManager
                from src.core.playbook_merger import PlaybookMerger
                self.playbook_manager = PlaybookManager()
                self.playbook_merger = PlaybookMerger()
                logger.info("StrawmanGenerator: Playbook system enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize playbook system: {e}")

    def _init_agent(self):
        """Initialize the strawman generation agent."""
        try:
            from src.utils.gcp_auth import initialize_vertex_ai
            initialize_vertex_ai()

            model_id = f"google-vertex:{self.model_name}"
            self.agent = Agent(
                model=model_id,
                system_prompt=self._get_system_prompt(),
                output_type=Strawman
            )
            logger.info("StrawmanGenerator agent initialized")
        except Exception as e:
            logger.error(f"Failed to initialize StrawmanGenerator: {e}")
            self.agent = None

    def _get_system_prompt(self) -> str:
        return """You are a presentation structure expert. Create well-organized presentation outlines (strawmans).

## CRITICAL: TOPIC-SPECIFIC CONTENT
You MUST create slides specifically about the provided topic. Every slide title and topic point must relate to the actual topic.
- If the topic is "Elephants", create slides about elephants (their biology, habitats, conservation, etc.)
- If the topic is "Machine Learning", create slides about ML concepts, applications, etc.
- NEVER create generic slides like "Section 1" or "Key Points" - always make them topic-specific!

## GUIDELINES
- Start with a title slide (hero) using the EXACT TOPIC as the title
- End with a closing slide (hero)
- 2-3 minutes per slide is typical
- Keep slide titles concise and clear
- Balance content vs. hero slides appropriately

## SECTION DIVIDER RULES (v4.5.14 - CRITICAL)
Section dividers should be used SPARINGLY based on presentation length:
- **<10 slides**: NO section dividers (waste of limited space)
- **10-19 slides**: Max 1-2 section dividers ONLY if there are clear logical breaks
- **20+ slides**: Include section dividers every 5-7 slides to organize content
Do NOT include section dividers unless the presentation genuinely benefits from them!

## STORY-DRIVEN SLIDE CATEGORIZATION (v4.0.25 - CRITICAL)

For EACH slide, you MUST determine:

### slide_type_hint (REQUIRED)
What type of visualization does this slide need based on the STORY you're telling?
- "hero" - Title slide, section divider, or closing slide
- "text" - Standard content (bullets, features, comparisons, benefits) - DEFAULT for ~70% of slides
- "chart" - Data visualization (trends, metrics, growth, performance data)
- "diagram" - Architecture, workflow, process flow, system diagrams
- "infographic" - Pyramids, funnels, visual hierarchies, value propositions

IMPORTANT: The slide_type_hint is determined by WHAT STORY you're telling, NOT by keywords.
- A slide about "Revenue Growth" could be "text" (bullet points about growth) OR "chart" (line chart showing growth)
- YOU decide based on how the story should be visualized

## HERO SLIDE NARRATIVE REQUIREMENTS (CRITICAL)

Hero slides require RICH narratives that describe section content. Generic narratives like "Transition to the next section" will produce poor results.

**For Section Dividers**, the `narrative` field MUST:
- Describe what topics will be covered in the upcoming section
- Reference how this section connects to what came before
- Be specific enough for Text Service to generate meaningful content

GOOD Section Divider:
- title: "Evolution and Consolidation"
- narrative: "This section covers how our AI technology evolved from basic automation to full consolidation, covering the key milestones and the three major product pivots that led to our current platform."
- topics: ["AI automation journey", "Key milestones", "Platform consolidation"]
- slide_type_hint: "hero"
- purpose: "section_transition"

BAD Section Divider:
- title: "Evolution and Consolidation"
- narrative: "Transition to the evolution phase" ← TOO VAGUE!

**For Closing Slides**, the `narrative` field MUST:
- Summarize the key takeaways from the entire presentation
- Include specific call-to-action context
- Reference the main topics that were covered

GOOD Closing Slide:
- title: "Thank You & Questions"
- narrative: "After covering our AI platform's 40% cost savings, 3x faster processing, and seamless integration capabilities, we invite questions and discussions about implementation."
- topics: ["Key benefits recap", "Implementation discussion", "Contact information"]
- slide_type_hint: "hero"
- purpose: "closing_slide"

## SMART LAYOUT SELECTION (v4.5.14 - CRITICAL)

### Presentation Type Detection
Determine presentation type from context/audience/purpose:
- **Informational**: educational, teaching, kids, general audience, explaining concepts
- **Professional**: business, executive, investor, sales, proposals, QBR
- **Mixed**: Default when unclear

### Layout Assignment Rules

**For Informational Presentations:**
- Use I-series (I1, I2, I3, I4) for 60-70% of content slides (image + text, visual learning)
- Use C1/L25 for remaining 30-40% (structured text content)
- Prefer visual learning approach

**For Professional Presentations:**
- Use C-series (C1, C2, C3, C4, C5) for 70% of content slides
- Use I-series (I1-I4) for 20-30% (strategic visuals where imagery adds value)
- Keep layouts clean and structured

**For Mixed/Default:**
- 60% C-series, 30% I-series, 10% split/visual layouts
- Balanced approach for general presentations

**For Visual Content (charts, diagrams, infographics):**
- PREFER 50/50 split layouts over full-page
- Left side: visual (chart/diagram/infographic)
- Right side: key insights or explanation
- This separates concerns clearly
- Full-page versions (C2, C3) are acceptable but split is preferred

### Layout Series Reference
- **Hero**: L29 (standard) or H1/H2/H3 (with images)
- **Content (text)**: L25, C1 (most common for text)
- **Image+Text**: I1, I2, I3, I4 (ideal for informational/educational)
- **Charts**: L02, C2 (or split variants)
- **Diagrams**: C4 (or split variants)
- **Infographics**: C3 (or split variants)

## VARIANT SELECTION (v4.5.14 - CRITICAL FOR UNIQUENESS)

### Plain Text Generation (50% of content slides)
For approximately HALF of your C1/L25 content slides, use:
- layout = "C1" or "L25"
- variant_id = null (NO VARIANT)
- This triggers plain text generation for unique, custom content

**When to use plain text (variant_id = null):**
- Complex explanations that don't fit predefined structures
- Narrative content that needs natural flow
- Unique slide concepts that are specific to this topic
- When you want maximum flexibility for the Text Service
- Slides that benefit from custom formatting

### Pre-defined Variants (50% of content slides)
Use these for structured content that fits clear patterns:

**Comparison variants:**
- comparison_2col, comparison_3col, comparison_4col (before/after, pros/cons, options)

**Sequential variants:**
- sequential_3col, sequential_4col, sequential_5col (step-by-step, timelines, processes)

**Grid variants:**
- grid_2x2_centered, grid_2x2_left, grid_2x2_numbered (4 items)
- grid_2x3, grid_2x3_left, grid_2x3_numbered (6 items)
- grid_3x2, grid_3x2_left, grid_3x2_numbered (6 items)

**Metrics variants:**
- metrics_3col, metrics_4col, metrics_2x2_grid, metrics_3x2_grid (KPIs, statistics)

**Matrix variants:**
- matrix_2x2, matrix_2x3 (two-dimensional comparisons)

**Table variants:**
- table_2col, table_3col, table_4col, table_5col (tabular data)

**Single column variants:**
- single_column_3section, single_column_4section, single_column_5section (vertical flow)

**Asymmetric variants:**
- asymmetric_8_4_3section, asymmetric_8_4_4section, asymmetric_8_4_5section (large + small)

**Other variants:**
- hybrid_left_2x2, hybrid_top_2x2 (mixed layouts)
- impact_quote (quotes, testimonials)

### IMPORTANT: VARIETY IS MANDATORY
- Each presentation should use 5-8 DIFFERENT variants/styles minimum
- Do NOT repeat the same 2-3 variants throughout
- Mix plain text (null variant) with structured variants
- Hero slides always have variant_id = null

## SEMANTIC GROUP RULES (v4.5.3 - Context-Aware Diversity)

Assign `semantic_group` to slides that should use the SAME template/variant.
Slides in the same semantic_group will share the same layout variant for visual consistency.

WHEN TO ASSIGN semantic_group (same group = same template):
- Multiple use case slides → semantic_group: "use_cases"
- Multiple product/feature deep-dives → semantic_group: "product_features"
- Timeline segments (early life, middle, later) → semantic_group: "timeline"
- Case study examples → semantic_group: "case_studies"
- Competitor comparisons → semantic_group: "competitors"
- Multiple agent explanations → semantic_group: "agents"

WHEN NOT TO ASSIGN semantic_group (null = diverse templates):
- Opening/introduction slides → null
- Different concept explanations → null
- Transition/bridge slides → null
- Slides covering different topics → null

EXAMPLE for "AI Agents in Supply Chain":
- Slides 2-4: AI concepts (semantic_group: null - should vary)
- Slides 5-9: Use Case 1, Use Case 2, ... → semantic_group: "use_cases" (same template)
- Slides 10-12: Implementation steps (semantic_group: null - should vary)

RULE: Slides WITH semantic_group = same variant. Slides WITHOUT = diverse variants.

## FOUR REQUIRED METADATA FIELDS (v4.5.15 - CRITICAL)

For EVERY slide, you MUST populate ALL FOUR of these fields. These are the most important fields in the output!

### 1. PURPOSE (REQUIRED)
What story role does this slide play in the narrative?

**Examples for content slides:**
- "problem_statement" - Establishes the challenge being addressed
- "solution_overview" - Presents the core solution
- "key_benefits" - Highlights value propositions
- "technical_deep_dive" - Explains how it works
- "use_case_example" - Shows real-world application
- "metrics_and_data" - Presents supporting data
- "competitive_advantage" - Differentiates from alternatives
- "implementation_steps" - Shows how to get started
- "features_overview" - Lists key features
- "team_introduction" - Introduces key people

**Examples for hero slides:**
- "title_slide" - Opening/introduction
- "section_transition" - Divides major sections
- "closing_slide" - Summary and call-to-action

### 2. TOPICS (REQUIRED)
3-5 specific bullet points covering what this slide should address.
These become the actual content points in the generated slide.

### 3. GENERATION INSTRUCTIONS (REQUIRED)
Specific instructions for HOW the content service should generate this slide.

**Examples for text slides:**
- "Generate a 3-column comparison table showing Feature vs Benefit vs Impact"
- "Create bullet points with bold headers followed by supporting text"
- "Use numbered list format showing the 4-step process"
- "Build a pros/cons layout with clear visual separation"
- "Create paragraph format with clear topic sentences"

**Examples for visual slides:**
- "Line chart showing revenue growth from Q1-Q4, emphasize 40% increase"
- "Architecture diagram with 3 layers: frontend, backend, database"
- "Funnel visualization with 4 stages: Awareness → Interest → Decision → Action"

### 4. NOTES (REQUIRED)
Speaker guidance and delivery hints for the presenter.

**Examples:**
- "Emphasize the 40% cost reduction - this is the key selling point"
- "Keep technical but accessible for mixed audience"
- "This is the emotional high point - use inspiring language"
- "Pause here for questions before continuing"
- "Use confident, assertive tone throughout"

## OUTPUT (v4.5.15)

Create a complete Strawman with slide definitions. Each slide MUST include:

**Identification:**
- slide_id (unique UUID)
- slide_number (position starting from 1)

**Content:**
- title (topic-specific, never generic)
- subtitle (supporting context: "Key Insights", "Strategic Overview", etc.)

**Layout:**
- layout (see SMART LAYOUT SELECTION above)
- variant_id (null for plain text OR specific variant - see VARIANT SELECTION above)

**Classification:**
- is_hero (true/false)
- hero_type (title_slide, section_divider, closing_slide - ONLY for hero slides)
- slide_type_hint (REQUIRED: hero, text, chart, diagram, or infographic)
- semantic_group (group ID for slides that should share same template, null otherwise)

**FOUR REQUIRED METADATA FIELDS (see detailed section above):**
- purpose (REQUIRED - pick from examples above)
- topics (REQUIRED - 3-5 specific points)
- generation_instructions (REQUIRED - specific HOW instructions)
- notes (REQUIRED - speaker guidance)
"""

    async def generate(
        self,
        topic: str,
        audience: str = "general",
        duration: int = 15,
        purpose: str = "inform",
        additional_context: Optional[Dict[str, Any]] = None,
        requested_slide_count: Optional[int] = None
    ) -> Strawman:
        """
        Generate a strawman for the given topic.

        v4.5: Added requested_slide_count to respect explicit user slide count.
        If user said "I need 20 slides", this overrides playbook/duration-based calculation.

        v4.1: Playbook-based generation with three-tier matching:
        - 90%+ confidence: Use playbook directly (FULL_MATCH)
        - 60-89% confidence: Merge playbook with custom slides (PARTIAL_MATCH)
        - <60% confidence: Generate from scratch (NO_MATCH)

        v4.0.25: Story-driven multi-service coordination:
        - Step 1: Generate storyline with AI (slide_type_hint, purpose)
        - Step 2: Apply Layout Analysis (layout, service, variant strategy)
        - Step 3: Resolve variants for text slides via Text Service

        v4.0.24: If Layout Service coordination is enabled and available,
        layouts will be selected dynamically. Otherwise falls back to
        hardcoded L25/L29 approach.
        """
        logger.info(f"StrawmanGenerator.generate() called with topic='{topic}', audience='{audience}', duration={duration}, purpose='{purpose}', requested_slide_count={requested_slide_count}")

        # v4.1: Try playbook matching first
        if self.playbook_manager:
            from src.models.playbook import MatchConfidence
            match = self.playbook_manager.find_best_match(
                audience=audience,
                purpose=purpose,
                duration=duration,
                topic=topic
            )

            logger.info(f"Playbook match: confidence={match.confidence:.2f}, type={match.match_type}")

            if match.match_type == MatchConfidence.FULL_MATCH:
                # Use playbook directly (90%+ confidence)
                logger.info(f"FULL_MATCH: Using playbook '{match.playbook_id}' directly")
                return await self._generate_from_playbook(
                    match.playbook, topic, audience, purpose, duration
                )

            elif match.match_type == MatchConfidence.PARTIAL_MATCH:
                # Merge playbook with custom slides (60-89% confidence)
                logger.info(f"PARTIAL_MATCH: Merging playbook '{match.playbook_id}' with custom content")
                return await self._generate_with_playbook_merge(
                    match, topic, audience, duration, purpose, additional_context
                )

        if not self.agent:
            logger.warning("Agent not initialized, using fallback")
            return self._fallback_strawman(topic, duration, requested_slide_count)

        # v4.5: Use explicit slide count if user specified, otherwise calculate from duration
        if requested_slide_count and requested_slide_count >= 3:
            slide_count = min(30, max(3, requested_slide_count))
            logger.info(f"Using explicit slide count: {slide_count} (user requested {requested_slide_count})")
        else:
            # Calculate approximate slide count from duration (roughly 2 min per slide)
            slide_count = max(5, min(15, duration // 2 + 2))

        prompt = f"""Create a presentation outline for:

## TOPIC (VERY IMPORTANT)
**{topic}**

This presentation MUST be about "{topic}". Every slide title and every topic point must relate to {topic}.

## CONTEXT
- Target Audience: {audience}
- Duration: {duration} minutes (approximately {slide_count} slides)
- Purpose: {purpose}

## REQUIREMENTS
1. Title slide: Use "{topic}" as the exact title
2. Content slides: Each must have a title AND subtitle specifically about {topic}
3. Closing slide: Summary and thank you
4. Include 3-5 topic points per slide, all related to {topic}
5. IMPORTANT: Every slide MUST have a subtitle that provides context (e.g., "Key Insights", "Understanding the Basics", "Critical Analysis")

## STORY-DRIVEN CATEGORIZATION (REQUIRED)
For each slide, you MUST include:
- slide_type_hint: hero, text, chart, diagram, or infographic
- purpose: what story this slide tells (e.g., problem_statement, traction, features)

Think about the STORY: What visualization best tells this part of the narrative?
- Most slides should be "text" (~70%)
- Use "chart" only when data visualization is essential to the story
- Use "diagram" only for architecture/workflow/process flows
- Use "infographic" only for pyramids/funnels/visual hierarchies

Additional Context: {json.dumps(additional_context or {})}

Generate a complete strawman with {slide_count} slides about {topic}.
"""

        try:
            from src.utils.vertex_retry import call_with_retry

            # STEP 1: Generate storyline with AI
            logger.info("Step 1: Generating storyline with AI...")
            result = await call_with_retry(
                lambda: self.agent.run(prompt),
                operation_name="Strawman Generator"
            )
            # Pydantic-AI 1.0+: use .output instead of .data
            strawman = result.output

            # STEP 2: Apply Layout Analysis (story-driven routing)
            if self.layout_analyzer:
                logger.info("Step 2: Applying Layout Analysis...")
                strawman = await self._apply_layout_analysis(strawman)

            # STEP 3: Resolve variants for text slides via Text Service
            if self.text_coord_client:
                logger.info("Step 3: Resolving variants via Text Service...")
                strawman = await self._resolve_variants(strawman)

            # v4.0.24: Enhance with Layout Service if enabled (optional additional step)
            if self.layout_client:
                strawman = await self._enhance_with_layout_service(strawman)

            # v4.0: Enhance with Content Analysis if enabled (for additional hints)
            if self.content_analyzer:
                strawman = await self._enhance_with_content_analysis(strawman)

            return strawman
        except Exception as e:
            logger.error(f"Strawman generation failed: {e}")
            # v4.0.25: Apply layout analysis to fallback as well
            fallback = self._fallback_strawman(topic, duration)
            if self.layout_analyzer:
                try:
                    fallback = await self._apply_layout_analysis(fallback)
                except Exception as layout_error:
                    logger.warning(f"Failed to apply layout analysis to fallback: {layout_error}")
            return fallback

    async def _generate_from_playbook(
        self,
        playbook,
        topic: str,
        audience: str,
        purpose: str,
        duration: int
    ) -> Strawman:
        """
        Generate strawman directly from playbook (FULL_MATCH scenario).

        v4.1: Used when playbook confidence >= 90%.
        """
        import uuid

        # Apply playbook template to generate slides
        playbook_slides = self.playbook_manager.apply_playbook(
            playbook, topic, audience, purpose, duration
        )

        # Convert to StrawmanSlide objects
        strawman_slides = []
        for slide_data in playbook_slides:
            strawman_slides.append(StrawmanSlide(
                slide_id=slide_data.get("slide_id", str(uuid.uuid4())),
                slide_number=slide_data.get("slide_number", len(strawman_slides) + 1),
                title=slide_data.get("title", ""),
                layout=slide_data.get("layout", "L25"),
                variant_id=slide_data.get("variant_id"),
                topics=slide_data.get("topics", []),
                is_hero=slide_data.get("is_hero", False),
                hero_type=slide_data.get("hero_type"),
                slide_type_hint=slide_data.get("slide_type_hint"),
                purpose=slide_data.get("purpose"),
                service=slide_data.get("service", "text"),
                generation_instructions=slide_data.get("generation_instructions")
            ))

        strawman = Strawman(
            title=topic,
            slides=strawman_slides,
            metadata={
                "generated": "playbook",
                "playbook_id": playbook.playbook_id,
                "duration": duration,
                "topic": topic
            }
        )

        # Apply layout analysis for service routing
        if self.layout_analyzer:
            strawman = await self._apply_layout_analysis(strawman)

        # Resolve variants for text slides
        if self.text_coord_client:
            strawman = await self._resolve_variants(strawman)

        logger.info(f"Generated strawman from playbook '{playbook.playbook_id}': {len(strawman_slides)} slides")
        return strawman

    async def _generate_with_playbook_merge(
        self,
        match,
        topic: str,
        audience: str,
        duration: int,
        purpose: str,
        additional_context: Optional[Dict[str, Any]]
    ) -> Strawman:
        """
        Generate strawman by merging playbook with custom slides (PARTIAL_MATCH scenario).

        v4.1: Used when playbook confidence is 60-89%.
        """
        import uuid

        # Get base slides from playbook
        playbook = match.playbook
        playbook_slides = self.playbook_manager.apply_playbook(
            playbook, topic, audience, purpose, duration
        )

        # Identify gaps that need custom content
        gaps = self.playbook_merger.identify_gaps(playbook, topic, purpose, duration)

        # Generate custom slides for gaps (if any)
        custom_slides = []
        if gaps:
            logger.info(f"Generating {len(gaps)} custom slides to fill gaps...")
            custom_slides = await self._generate_gap_slides(
                gaps, topic, audience, purpose, duration, additional_context
            )

        # Merge playbook slides with custom slides
        merged_slides = self.playbook_merger.merge(
            playbook_slides,
            custom_slides,
            match.match_details,
            match.adaptation_notes
        )

        # Convert to StrawmanSlide objects
        strawman_slides = []
        for slide_data in merged_slides:
            strawman_slides.append(StrawmanSlide(
                slide_id=slide_data.get("slide_id", str(uuid.uuid4())),
                slide_number=slide_data.get("slide_number", len(strawman_slides) + 1),
                title=slide_data.get("title", ""),
                layout=slide_data.get("layout", "L25"),
                variant_id=slide_data.get("variant_id"),
                topics=slide_data.get("topics", []),
                is_hero=slide_data.get("is_hero", False),
                hero_type=slide_data.get("hero_type"),
                slide_type_hint=slide_data.get("slide_type_hint"),
                purpose=slide_data.get("purpose"),
                service=slide_data.get("service", "text"),
                generation_instructions=slide_data.get("generation_instructions")
            ))

        strawman = Strawman(
            title=topic,
            slides=strawman_slides,
            metadata={
                "generated": "playbook_merged",
                "playbook_id": playbook.playbook_id,
                "confidence": match.confidence,
                "gaps_filled": len(gaps),
                "duration": duration,
                "topic": topic
            }
        )

        # Apply layout analysis for service routing
        if self.layout_analyzer:
            strawman = await self._apply_layout_analysis(strawman)

        # Resolve variants for text slides
        if self.text_coord_client:
            strawman = await self._resolve_variants(strawman)

        logger.info(
            f"Generated merged strawman from playbook '{playbook.playbook_id}': "
            f"{len(strawman_slides)} slides (playbook: {len(playbook_slides)}, custom: {len(custom_slides)})"
        )
        return strawman

    async def _generate_gap_slides(
        self,
        gaps,
        topic: str,
        audience: str,
        purpose: str,
        duration: int,
        additional_context: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Generate custom slides to fill gaps in playbook.

        v4.1: Used for PARTIAL_MATCH scenario.
        """
        import uuid

        custom_slides = []

        for gap in gaps:
            # Generate slide for this gap
            slide = {
                "slide_id": str(uuid.uuid4()),
                "title": f"{gap.purpose.replace('_', ' ').title()}: {topic}",
                "layout": "L25",
                "variant_id": None,
                "topics": [
                    f"Key point about {gap.purpose.replace('_', ' ')} of {topic}",
                    f"Important information for {gap.purpose.replace('_', ' ')}",
                    f"Details on {topic}"
                ],
                "is_hero": False,
                "hero_type": None,
                "slide_type_hint": "text",
                "purpose": gap.purpose,
                "service": "text",
                "generation_instructions": None
            }
            custom_slides.append(slide)

        logger.info(f"Generated {len(custom_slides)} gap-filling slides")
        return custom_slides

    def _select_fallback_variant(self, topic_count: int) -> str:
        """Select variant with randomization for diversity.

        v4.0.23: Added for variant selection in fallback strawman.
        v4.5.2: Added randomization - multiple options per topic count for diversity.
                When Text Service coordination is unavailable, this provides
                visual variety by randomly selecting from valid variants.
        """
        # Multiple variant options per topic count for diversity
        variant_options = {
            2: ['comparison_2col'],
            3: ['sequential_3col', 'comparison_3col', 'single_column_3section_c1'],
            4: ['grid_2x2_centered', 'matrix_2x2', 'grid_2x2_left', 'comparison_4col', 'sequential_4col'],
            5: ['sequential_5col', 'grid_2x3', 'single_column_5section_c1'],
            6: ['grid_2x3', 'grid_3x2', 'matrix_2x3'],
        }

        # Get options for the topic count, fallback to grid_2x3 variants
        options = variant_options.get(topic_count, ['grid_2x3', 'grid_3x2'])

        # Randomly select from available options
        return random.choice(options)

    def _fallback_strawman(self, topic: str, duration: int, requested_slide_count: Optional[int] = None) -> Strawman:
        """Generate a basic fallback strawman with topic-specific content.

        v4.5: Added requested_slide_count parameter to respect explicit user slide count.
        v4.0.4: Improved to generate topic-specific slide titles and points
        instead of generic "Section 1", "Section 2" placeholders.
        """
        import uuid

        logger.info(f"Generating fallback strawman for topic: {topic}")

        # v4.5: Use explicit slide count if provided, otherwise estimate from duration
        if requested_slide_count and requested_slide_count >= 3:
            slide_count = min(30, max(3, requested_slide_count))
        else:
            # Estimate slide count (roughly 2 min per slide)
            slide_count = max(5, min(15, duration // 2 + 2))

        # Generate topic-specific section titles
        # These are generic but at least reference the topic
        section_titles = [
            f"Introduction to {topic}",
            f"Key Aspects of {topic}",
            f"Understanding {topic}",
            f"Details About {topic}",
            f"Exploring {topic}",
            f"Deep Dive: {topic}",
            f"Important Points About {topic}",
            f"{topic} in Practice",
            f"Case Studies: {topic}",
            f"Future of {topic}",
        ]

        slides = [
            StrawmanSlide(
                slide_id=str(uuid.uuid4()),
                slide_number=1,
                title=topic,
                subtitle="A Comprehensive Overview",  # v4.1.1: Add subtitle
                layout="L29",  # v4.0.23: Fixed - hero slides use L29
                topics=[f"Welcome to this presentation about {topic}", f"Overview of {topic}"],
                is_hero=True,
                hero_type="title_slide"
            )
        ]

        # Add content slides with topic-specific titles
        content_count = slide_count - 2  # Minus title and closing
        # v4.1.1: Generic subtitles for fallback content slides
        content_subtitles = [
            "Key Insights",
            "Understanding the Fundamentals",
            "Critical Analysis",
            "Important Perspectives",
            "Essential Information",
            "Core Concepts",
            "Key Considerations",
            "In-Depth Look",
            "Practical Applications",
            "Expert Analysis"
        ]
        for i in range(content_count):
            section_idx = i % len(section_titles)
            subtitle_idx = i % len(content_subtitles)
            # v4.0.23: Select variant based on topic count
            topics = [
                f"Key point about {topic}",
                f"Important information regarding {topic}",
                f"Details on this aspect of {topic}"
            ]
            slides.append(StrawmanSlide(
                slide_id=str(uuid.uuid4()),
                slide_number=i + 2,
                title=section_titles[section_idx],
                subtitle=content_subtitles[subtitle_idx],  # v4.1.1: Add subtitle
                layout="L25",  # v4.0.23: Fixed - content slides use L25
                variant_id=self._select_fallback_variant(len(topics)),  # v4.0.23: Add variant
                topics=topics,
                is_hero=False,
                notes=f"Content slide {i + 1} about {topic}"
            ))

        # Add closing slide
        slides.append(StrawmanSlide(
            slide_id=str(uuid.uuid4()),
            slide_number=slide_count,
            title=f"Thank You - {topic}",
            subtitle="Questions & Discussion",  # v4.1.1: Add subtitle
            layout="L29",  # v4.0.23: Fixed - hero slides use L29
            topics=[f"Summary of {topic}", "Questions and Discussion"],
            is_hero=True,
            hero_type="closing_slide"
        ))

        return Strawman(
            title=topic,
            slides=slides,
            metadata={"generated": "fallback", "duration": duration, "topic": topic}
        )

    async def _apply_layout_analysis(self, strawman: Strawman) -> Strawman:
        """
        Apply Layout Analysis to determine exact layout, service, and variant strategy.

        v4.0.25: Step 2 of the two-step process.
        Uses LayoutAnalyzer to map slide_type_hint → layout → service.

        Args:
            strawman: Raw strawman from AI with slide_type_hint and purpose

        Returns:
            Enhanced strawman with layout, service, and generation_instructions
        """
        if not self.layout_analyzer:
            logger.warning("LayoutAnalyzer not initialized, skipping layout analysis")
            return strawman

        try:
            enhanced_slides = []
            for slide in strawman.slides:
                # Get slide_type_hint (default to "text" if not set)
                slide_type_hint = getattr(slide, 'slide_type_hint', None) or (
                    "hero" if slide.is_hero else "text"
                )
                purpose = getattr(slide, 'purpose', None)

                # Run layout analysis
                analysis = self.layout_analyzer.analyze(
                    slide_type_hint=slide_type_hint,
                    hero_type=slide.hero_type,
                    topic_count=len(slide.topics) if slide.topics else 0,
                    purpose=purpose,
                    title=slide.title,
                    topics=slide.topics
                )

                # Create enhanced slide with analysis results
                enhanced_slide = StrawmanSlide(
                    slide_id=slide.slide_id,
                    slide_number=slide.slide_number,
                    title=slide.title,
                    layout=analysis.layout,
                    topics=slide.topics,
                    variant_id=analysis.variant_id or slide.variant_id,
                    notes=slide.notes,
                    is_hero=slide.is_hero,
                    hero_type=slide.hero_type,
                    # Preserve existing fields
                    content_hints=slide.content_hints,
                    suggested_service=slide.suggested_service,
                    service_confidence=slide.service_confidence,
                    needs_image=slide.needs_image,
                    suggested_iseries=slide.suggested_iseries,
                    # v4.0.25: New story-driven fields
                    slide_type_hint=slide_type_hint,
                    purpose=purpose,
                    service=analysis.service,
                    # v4.5.14: Preserve AI-generated generation_instructions, fall back to LayoutAnalyzer
                    generation_instructions=slide.generation_instructions or analysis.generation_instructions,
                    # v4.5.14: Preserve subtitle and semantic_group
                    subtitle=slide.subtitle,
                    semantic_group=getattr(slide, 'semantic_group', None)
                )
                enhanced_slides.append(enhanced_slide)

                logger.debug(
                    f"Slide {slide.slide_number}: {slide_type_hint} → "
                    f"layout={analysis.layout}, service={analysis.service}"
                )

            # Update metadata
            metadata = strawman.metadata or {}
            metadata["layout_analysis_applied"] = True

            return Strawman(
                title=strawman.title,
                slides=enhanced_slides,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Layout analysis failed: {e}")
            return strawman

    async def _resolve_variants(self, strawman: Strawman) -> Strawman:
        """
        Resolve variants for text slides via Text Service /recommend-variant.

        v4.0.25: Step 3 of the two-step process.
        For slides with service="text" and layout in VARIANT_LAYOUTS,
        calls Text Service to get the best variant_id.

        v4.5.2: Added fallback with DiversityTracker when coordination is disabled
                or unavailable. Ensures variant diversity even without Text Service.

        Args:
            strawman: Strawman with layout analysis applied

        Returns:
            Strawman with variant_id populated for text slides
        """
        # Import DiversityTracker for variant diversity enforcement
        from src.utils.diversity_tracker import DiversityTracker

        if not self.text_coord_client:
            # v4.5.2: Fallback variant resolution with diversity tracking
            logger.debug("Text Service coordination not enabled, using fallback with diversity tracking")
            return self._resolve_variants_fallback(strawman)

        try:
            # Check Text Service availability
            is_healthy = await self.text_coord_client.health_check()
            if not is_healthy:
                logger.warning("Text Service not available for variant resolution, using fallback")
                return self._resolve_variants_fallback(strawman)

            enhanced_slides = []
            variant_layouts = {"L25", "C1"}  # Layouts that support variants

            for slide in strawman.slides:
                # Only resolve variants for text slides with variant-supporting layouts
                if (
                    slide.service == "text" and
                    slide.layout in variant_layouts and
                    not slide.is_hero and
                    not slide.variant_id  # Don't override if already set
                ):
                    try:
                        # Build request for Text Service
                        slide_content = {
                            "title": slide.title,
                            "topics": slide.topics,
                            "topic_count": len(slide.topics) if slide.topics else 0
                        }
                        available_space = {
                            "width": 1800,  # Default content zone
                            "height": 720,
                            "layout_id": slide.layout
                        }

                        # Get variant recommendation
                        from src.models.content_hints import ContentHints
                        hints = ContentHints(
                            topic_count=len(slide.topics) if slide.topics else 0
                        )

                        best_variant = await self.text_coord_client.get_best_variant(
                            slide_content=slide_content,
                            content_hints=hints,
                            available_space=available_space,
                            confidence_threshold=self.settings.TEXT_SERVICE_CONFIDENCE_THRESHOLD
                        )

                        if best_variant:
                            # Create slide with resolved variant
                            slide = StrawmanSlide(
                                slide_id=slide.slide_id,
                                slide_number=slide.slide_number,
                                title=slide.title,
                                layout=slide.layout,
                                topics=slide.topics,
                                variant_id=best_variant,
                                notes=slide.notes,
                                is_hero=slide.is_hero,
                                hero_type=slide.hero_type,
                                content_hints=slide.content_hints,
                                suggested_service=slide.suggested_service,
                                service_confidence=slide.service_confidence,
                                needs_image=slide.needs_image,
                                suggested_iseries=slide.suggested_iseries,
                                slide_type_hint=slide.slide_type_hint,
                                purpose=slide.purpose,
                                service=slide.service,
                                generation_instructions=slide.generation_instructions
                            )
                            logger.debug(
                                f"Slide {slide.slide_number}: Resolved variant={best_variant}"
                            )

                    except Exception as e:
                        logger.warning(f"Failed to resolve variant for slide {slide.slide_number}: {e}")

                enhanced_slides.append(slide)

            # v4.5.2: Apply DiversityTracker to prevent excessive repetition
            # v4.5.3: Now respects semantic_group for context-aware diversity
            diversity_tracker = DiversityTracker()
            final_slides = []

            for slide in enhanced_slides:
                if slide.service == "text" and not slide.is_hero and slide.variant_id:
                    # Check if this variant violates diversity rules
                    # v4.5.3: Pass semantic_group - slides WITH semantic_group are exempt
                    should_override, suggestion = diversity_tracker.should_override_for_diversity(
                        classification=slide.variant_id,
                        variant_id=slide.variant_id,
                        semantic_group=slide.semantic_group  # v4.5.3: Context-aware diversity
                    )

                    if should_override and suggestion:
                        logger.info(
                            f"Slide {slide.slide_number}: Diversity override - "
                            f"{slide.variant_id} → {suggestion}"
                        )
                        # Create new slide with suggested variant
                        slide = StrawmanSlide(
                            slide_id=slide.slide_id,
                            slide_number=slide.slide_number,
                            title=slide.title,
                            subtitle=slide.subtitle,
                            layout=slide.layout,
                            topics=slide.topics,
                            variant_id=suggestion,
                            notes=slide.notes,
                            is_hero=slide.is_hero,
                            hero_type=slide.hero_type,
                            content_hints=slide.content_hints,
                            suggested_service=slide.suggested_service,
                            service_confidence=slide.service_confidence,
                            needs_image=slide.needs_image,
                            suggested_iseries=slide.suggested_iseries,
                            slide_type_hint=slide.slide_type_hint,
                            purpose=slide.purpose,
                            service=slide.service,
                            generation_instructions=slide.generation_instructions,
                            semantic_group=slide.semantic_group  # v4.5.3: Preserve semantic_group
                        )

                    # Track the slide for diversity checking
                    diversity_tracker.add_slide(
                        classification=slide.variant_id,
                        variant_id=slide.variant_id,
                        semantic_group=slide.semantic_group,  # v4.5.3: Context-aware tracking
                        slide_number=slide.slide_number
                    )

                final_slides.append(slide)

            # v4.5.3: Propagate variants within semantic groups
            # Ensures all slides with same semantic_group use the same variant
            final_slides = self._propagate_semantic_group_variants(final_slides)

            # Update metadata
            metadata = strawman.metadata or {}
            metadata["variants_resolved"] = True
            metadata["diversity_applied"] = True
            metadata["semantic_groups_applied"] = True

            return Strawman(
                title=strawman.title,
                slides=final_slides,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Variant resolution failed: {e}")
            return self._resolve_variants_fallback(strawman)

    def _resolve_variants_fallback(self, strawman: Strawman) -> Strawman:
        """
        Fallback variant resolution using randomization and DiversityTracker.

        v4.5.2: Called when Text Service coordination is disabled or unavailable.
        Uses _select_fallback_variant() for random selection and DiversityTracker
        to ensure no more than 2 consecutive slides use the same variant.

        Args:
            strawman: Strawman with layout analysis applied

        Returns:
            Strawman with variant_id populated for text slides
        """
        from src.utils.diversity_tracker import DiversityTracker

        diversity_tracker = DiversityTracker()
        enhanced_slides = []
        variant_layouts = {"L25", "C1"}  # Layouts that support variants

        for slide in strawman.slides:
            # Only resolve variants for text slides without existing variant
            if (
                slide.service == "text" and
                slide.layout in variant_layouts and
                not slide.is_hero and
                not slide.variant_id
            ):
                # Get topic count for variant selection
                topic_count = len(slide.topics) if slide.topics else 4

                # Select a random variant based on topic count
                selected_variant = self._select_fallback_variant(topic_count)

                # Check diversity - don't allow more than 2 consecutive same variants
                # v4.5.3: Pass semantic_group - slides WITH semantic_group are exempt
                should_override, suggestion = diversity_tracker.should_override_for_diversity(
                    classification=selected_variant,
                    variant_id=selected_variant,
                    semantic_group=slide.semantic_group  # v4.5.3: Context-aware diversity
                )

                if should_override and suggestion:
                    logger.debug(
                        f"Slide {slide.slide_number}: Diversity override - "
                        f"{selected_variant} → {suggestion}"
                    )
                    selected_variant = suggestion

                # Create new slide with the selected variant
                slide = StrawmanSlide(
                    slide_id=slide.slide_id,
                    slide_number=slide.slide_number,
                    title=slide.title,
                    subtitle=slide.subtitle,
                    layout=slide.layout,
                    topics=slide.topics,
                    variant_id=selected_variant,
                    notes=slide.notes,
                    is_hero=slide.is_hero,
                    hero_type=slide.hero_type,
                    content_hints=slide.content_hints,
                    suggested_service=slide.suggested_service,
                    service_confidence=slide.service_confidence,
                    needs_image=slide.needs_image,
                    suggested_iseries=slide.suggested_iseries,
                    slide_type_hint=slide.slide_type_hint,
                    purpose=slide.purpose,
                    service=slide.service,
                    generation_instructions=slide.generation_instructions,
                    semantic_group=slide.semantic_group  # v4.5.3: Preserve semantic_group
                )

                logger.debug(
                    f"Slide {slide.slide_number}: Fallback variant={selected_variant}"
                )

            # Track all slides for diversity (even hero slides for context)
            # v4.5.3: Pass semantic_group for context-aware diversity tracking
            if slide.variant_id:
                diversity_tracker.add_slide(
                    classification=slide.variant_id,
                    variant_id=slide.variant_id,
                    semantic_group=slide.semantic_group,  # v4.5.3: Context-aware tracking
                    slide_number=slide.slide_number
                )

            enhanced_slides.append(slide)

        # v4.5.3: Propagate variants within semantic groups
        # Ensures all slides with same semantic_group use the same variant
        enhanced_slides = self._propagate_semantic_group_variants(enhanced_slides)

        # Update metadata
        metadata = strawman.metadata or {}
        metadata["variants_resolved"] = True
        metadata["variant_source"] = "fallback_with_diversity"
        metadata["semantic_groups_applied"] = True

        return Strawman(
            title=strawman.title,
            slides=enhanced_slides,
            metadata=metadata
        )

    def _propagate_semantic_group_variants(
        self, slides: List[StrawmanSlide]
    ) -> List[StrawmanSlide]:
        """
        Ensure all slides in the same semantic_group use the same variant.

        v4.5.3: Context-aware diversity - slides with the same semantic_group
        (e.g., "use_cases", "timeline", "case_studies") should share the same
        template/variant for visual consistency.

        This method is called AFTER variant resolution to ensure consistency
        within semantic groups.

        Args:
            slides: List of slides with variants resolved

        Returns:
            List of slides with consistent variants within semantic groups
        """
        # Track variant for each semantic group
        group_variants: Dict[str, str] = {}

        # First pass: collect variant for each group (use first slide's variant)
        for slide in slides:
            if slide.semantic_group and slide.variant_id:
                if slide.semantic_group not in group_variants:
                    group_variants[slide.semantic_group] = slide.variant_id
                    logger.debug(
                        f"Semantic group '{slide.semantic_group}' → variant '{slide.variant_id}'"
                    )

        # If no groups found, return unchanged
        if not group_variants:
            return slides

        # Second pass: propagate variants to all slides in each group
        propagated_slides = []
        for slide in slides:
            if slide.semantic_group and slide.semantic_group in group_variants:
                target_variant = group_variants[slide.semantic_group]

                # Only update if variant is different
                if slide.variant_id != target_variant:
                    logger.info(
                        f"Slide {slide.slide_number}: Propagating group '{slide.semantic_group}' "
                        f"variant {slide.variant_id} → {target_variant}"
                    )
                    # Create new slide with propagated variant
                    slide = StrawmanSlide(
                        slide_id=slide.slide_id,
                        slide_number=slide.slide_number,
                        title=slide.title,
                        subtitle=slide.subtitle,
                        layout=slide.layout,
                        topics=slide.topics,
                        variant_id=target_variant,
                        notes=slide.notes,
                        is_hero=slide.is_hero,
                        hero_type=slide.hero_type,
                        content_hints=slide.content_hints,
                        suggested_service=slide.suggested_service,
                        service_confidence=slide.service_confidence,
                        needs_image=slide.needs_image,
                        suggested_iseries=slide.suggested_iseries,
                        slide_type_hint=slide.slide_type_hint,
                        purpose=slide.purpose,
                        service=slide.service,
                        generation_instructions=slide.generation_instructions,
                        semantic_group=slide.semantic_group
                    )

            propagated_slides.append(slide)

        logger.info(f"Semantic group propagation: {len(group_variants)} groups processed")
        return propagated_slides

    async def _enhance_with_layout_service(self, strawman: Strawman) -> Strawman:
        """
        Enhance strawman with Layout Service recommendations.

        v4.0.24: Post-processes the strawman to get intelligent layout
        and variant selections from the Layout Service.

        This method:
        1. Checks Layout Service availability
        2. For each slide, gets layout recommendations
        3. Updates layouts and variants based on recommendations
        4. Falls back gracefully if service unavailable

        Args:
            strawman: The AI-generated strawman

        Returns:
            Enhanced strawman with optimized layouts/variants
        """
        if not self.layout_client:
            return strawman

        try:
            # Check Layout Service availability
            service_available = await self.layout_client.health_check()
            if not service_available:
                logger.warning("Layout Service unavailable, using original strawman")
                return strawman

            logger.info(f"Enhancing strawman with Layout Service ({len(strawman.slides)} slides)")

            # Process each slide
            enhanced_slides = []
            for slide in strawman.slides:
                enhanced_slide = await self._enhance_slide_layout(slide)
                enhanced_slides.append(enhanced_slide)

            # Create enhanced strawman with updated metadata
            metadata = strawman.metadata or {}
            metadata["layout_source"] = "layout_service"
            metadata["layout_enhanced"] = True

            return Strawman(
                title=strawman.title,
                slides=enhanced_slides,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Layout Service enhancement failed: {e}")
            # Return original strawman on error
            return strawman

    async def _enhance_slide_layout(self, slide: StrawmanSlide) -> StrawmanSlide:
        """
        Enhance a single slide with Layout Service recommendations.

        Args:
            slide: Original slide from strawman

        Returns:
            Enhanced slide with optimized layout/variant
        """
        try:
            # Determine slide type for recommendation
            if slide.is_hero:
                slide_type = "hero"
            else:
                slide_type = "content"

            # Count topics for variant selection
            topic_count = len(slide.topics) if slide.topics else 1

            # Build content hints
            content_hints = {
                "has_data": False,  # Could be enhanced with AI detection
                "has_image": False,
                "hero_type": slide.hero_type if slide.is_hero else None
            }

            # Get layout recommendations
            recommendations = await self.layout_client.recommend_layout(
                slide_type=slide_type,
                topic_count=topic_count,
                content_hints=content_hints
            )

            if recommendations:
                best_rec = recommendations[0]
                logger.debug(
                    f"Slide {slide.slide_number}: Layout recommendation "
                    f"{best_rec.layout_id} (score: {best_rec.score:.2f})"
                )

                # Update slide with recommended layout
                new_layout = best_rec.layout_id

                # Update variant if recommendations include suggestions
                new_variant = slide.variant_id
                if best_rec.variant_suggestions and not slide.is_hero:
                    new_variant = best_rec.variant_suggestions[0]

                # Create enhanced slide
                return StrawmanSlide(
                    slide_id=slide.slide_id,
                    slide_number=slide.slide_number,
                    title=slide.title,
                    layout=new_layout,
                    variant_id=new_variant,
                    topics=slide.topics,
                    notes=slide.notes,
                    is_hero=slide.is_hero,
                    hero_type=slide.hero_type
                )
            else:
                # No recommendations, return original
                return slide

        except Exception as e:
            logger.warning(
                f"Failed to enhance slide {slide.slide_number}: {e}"
            )
            # Return original slide on error
            return slide

    async def _enhance_with_content_analysis(self, strawman: Strawman) -> Strawman:
        """
        Enhance strawman with Content Analysis for service routing.

        v4.0: Uses ContentAnalyzer to analyze slide content and determine:
        - Content hints (has_numbers, is_comparison, etc.)
        - Suggested service (text, analytics, diagram, illustrator)
        - I-series recommendations (needs_image, suggested_iseries)

        This enables intelligent service routing during content generation.

        Args:
            strawman: The strawman to enhance

        Returns:
            Enhanced strawman with content hints on each slide
        """
        if not self.content_analyzer:
            return strawman

        try:
            logger.info(f"Enhancing strawman with content analysis ({len(strawman.slides)} slides)")

            enhanced_slides = []
            for slide in strawman.slides:
                enhanced_slide = await self._analyze_slide_content(slide)
                enhanced_slides.append(enhanced_slide)

            # Update metadata
            metadata = strawman.metadata or {}
            metadata["content_analyzed"] = True
            metadata["text_service_coordination"] = bool(self.text_coord_client)

            return Strawman(
                title=strawman.title,
                slides=enhanced_slides,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Content analysis enhancement failed: {e}")
            return strawman

    async def _analyze_slide_content(self, slide: StrawmanSlide) -> StrawmanSlide:
        """
        Analyze a single slide's content and populate hints.

        Args:
            slide: Original slide from strawman

        Returns:
            Enhanced slide with content_hints, suggested_service, etc.
        """
        # Skip hero slides - they always use Text Service
        if slide.is_hero:
            return slide

        try:
            # Run content analysis
            hints = self.content_analyzer.analyze(slide)

            # Convert ContentHints to dict for storage
            hints_dict = {
                "has_numbers": hints.has_numbers,
                "is_comparison": hints.is_comparison,
                "is_time_based": hints.is_time_based,
                "is_hierarchical": hints.is_hierarchical,
                "is_process_flow": hints.is_process_flow,
                "is_sequential": hints.is_sequential,
                "detected_keywords": hints.detected_keywords,
                "pattern_type": hints.pattern_type.value if hints.pattern_type else None,
                "numeric_density": hints.numeric_density,
                "topic_count": hints.topic_count
            }

            # Determine service routing
            suggested_service = None
            service_confidence = None
            if hints.suggested_service:
                suggested_service = hints.suggested_service.value
                service_confidence = hints.service_confidence

            # Check for I-series recommendation
            needs_image = hints.needs_image
            suggested_iseries = hints.suggested_iseries

            # If Text Service coordination is enabled, get variant recommendation
            variant_id = slide.variant_id
            if self.text_coord_client and suggested_service == "text":
                try:
                    slide_content = {
                        "title": slide.title,
                        "topics": slide.topics,
                        "topic_count": len(slide.topics) if slide.topics else 0
                    }
                    available_space = {
                        "width": 1800,  # Default content zone
                        "height": 720,
                        "layout_id": slide.layout
                    }

                    best_variant = await self.text_coord_client.get_best_variant(
                        slide_content=slide_content,
                        content_hints=hints,
                        available_space=available_space,
                        confidence_threshold=self.settings.TEXT_SERVICE_CONFIDENCE_THRESHOLD
                    )

                    if best_variant:
                        variant_id = best_variant
                        logger.debug(
                            f"Slide {slide.slide_number}: Text Service recommended {variant_id}"
                        )
                except Exception as e:
                    logger.warning(f"Text Service coordination failed: {e}")

            # Create enhanced slide with all fields
            return StrawmanSlide(
                slide_id=slide.slide_id,
                slide_number=slide.slide_number,
                title=slide.title,
                layout=slide.layout,
                topics=slide.topics,
                variant_id=variant_id,
                notes=slide.notes,
                is_hero=slide.is_hero,
                hero_type=slide.hero_type,
                content_hints=hints_dict,
                suggested_service=suggested_service,
                service_confidence=service_confidence,
                needs_image=needs_image,
                suggested_iseries=suggested_iseries
            )

        except Exception as e:
            logger.warning(f"Failed to analyze slide {slide.slide_number}: {e}")
            return slide

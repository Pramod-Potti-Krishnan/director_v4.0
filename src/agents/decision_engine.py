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
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from pydantic_ai import Agent

from src.models.decision import (
    DecisionOutput, DecisionContext, ActionType,
    ToolCallRequest, ApprovalDetectionResult,
    Strawman, StrawmanSlide, PresentationPlan
)
from src.tools.registry import ToolRegistry, get_registry

logger = logging.getLogger(__name__)


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
    """

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        self._init_agent()

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

## GUIDELINES
- Start with a title slide (hero)
- Include section dividers for major topic changes
- End with a closing slide (hero)
- 2-3 minutes per slide is typical
- Keep slide titles concise and clear
- Balance content vs. hero slides appropriately

## STRUCTURE RULES
- 5-10 slides: Simple structure (title, 3-8 content, closing)
- 10-20 slides: Include section dividers every 4-6 slides
- 20+ slides: Executive summary after title, multiple sections

## OUTPUT
Create a complete Strawman with slide definitions including:
- slide_id (unique identifier)
- slide_number (position)
- title (concise)
- layout (L01 for simple, L02 for two-column, etc.)
- topics (key points)
- is_hero (true for title/section/closing)
"""

    async def generate(
        self,
        topic: str,
        audience: str = "general",
        duration: int = 15,
        purpose: str = "inform",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Strawman:
        """Generate a strawman for the given topic."""
        if not self.agent:
            return self._fallback_strawman(topic, duration)

        prompt = f"""Create a presentation outline for:

Topic: {topic}
Target Audience: {audience}
Duration: {duration} minutes
Purpose: {purpose}

Additional Context: {json.dumps(additional_context or {})}

Generate a complete strawman with appropriate number of slides for the duration.
"""

        try:
            from src.utils.vertex_retry import call_with_retry
            result = await call_with_retry(
                lambda: self.agent.run(prompt),
                operation_name="Strawman Generator"
            )
            # Pydantic-AI 1.0+: use .output instead of .data
            return result.output
        except Exception as e:
            logger.error(f"Strawman generation failed: {e}")
            return self._fallback_strawman(topic, duration)

    def _fallback_strawman(self, topic: str, duration: int) -> Strawman:
        """Generate a basic fallback strawman."""
        import uuid

        # Estimate slide count (roughly 2 min per slide)
        slide_count = max(5, min(15, duration // 2 + 2))

        slides = [
            StrawmanSlide(
                slide_id=str(uuid.uuid4()),
                slide_number=1,
                title=topic,
                layout="H1",
                topics=["Introduction", "Overview"],
                is_hero=True,
                hero_type="title_slide"
            )
        ]

        # Add content slides
        for i in range(2, slide_count):
            slides.append(StrawmanSlide(
                slide_id=str(uuid.uuid4()),
                slide_number=i,
                title=f"Section {i - 1}",
                layout="L01",
                topics=[f"Key point {j}" for j in range(1, 4)],
                is_hero=False
            ))

        # Add closing slide
        slides.append(StrawmanSlide(
            slide_id=str(uuid.uuid4()),
            slide_number=slide_count,
            title="Thank You",
            layout="H3",
            topics=["Summary", "Questions"],
            is_hero=True,
            hero_type="closing_slide"
        ))

        return Strawman(
            title=topic,
            slides=slides,
            metadata={"generated": "fallback", "duration": duration}
        )

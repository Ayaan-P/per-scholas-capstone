"""
Session Service - Agent conversation management

Handles the agent conversation loop:
1. Load org context from workspace
2. Maintain conversation history
3. Call Claude API with context
4. Save messages to session
5. Extract and save decisions/learnings
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from anthropic import Anthropic
from workspace_service import get_workspace_service

# Claude client
_client: Optional[Anthropic] = None


def get_claude_client() -> Anthropic:
    """Get or create Claude client"""
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        _client = Anthropic(api_key=api_key)
    return _client


# System prompt template for FundFish agent
SYSTEM_PROMPT_TEMPLATE = """You are FundFish, an AI grant research assistant for nonprofit organizations.

## Your Organization
{profile}

## Writing Style
{style}

## Key Decisions & Preferences
{decisions}

## Your Capabilities
- Search and analyze grant opportunities
- Match grants to organization's mission and capacity
- Help prepare grant applications
- Answer questions about funding strategies
- Remember preferences and past decisions

## Guidelines
- Be helpful, concise, and actionable
- Reference the organization's specific programs and metrics
- Follow the writing style guide
- When you learn a new preference or make a decision together, note it clearly
- Format responses for readability (headers, bullets when appropriate)
- If asked to do something outside your capabilities, be honest about limitations

## Response Format
- Keep responses focused and scannable
- Use **bold** for key points
- Use bullet lists for multiple items
- For grant recommendations, include: name, amount, deadline, fit score, and why it matches
"""


class SessionService:
    """Manages agent conversation sessions"""

    def __init__(self, supabase=None):
        self.workspace = get_workspace_service()
        self.supabase = supabase

    def _build_system_prompt(self, org_id: str) -> str:
        """Build system prompt with org context"""
        context = self.workspace.get_agent_context(org_id)

        return SYSTEM_PROMPT_TEMPLATE.format(
            profile=context.get("profile", "(No profile set)"),
            style=context.get("style", "(No style guide set)"),
            decisions=context.get("decisions", "(No decisions recorded)")
        )

    def _get_session_messages(self, org_id: str, session_id: str) -> List[Dict[str, str]]:
        """Parse session history into messages list"""
        history = self.workspace.get_session_history(org_id, session_id)
        if not history:
            return []

        messages = []
        # Parse the markdown format: **[HH:MM:SS] ROLE:** content
        import re
        pattern = r'\*\*\[[\d:]+\] (USER|AGENT):\*\* (.+?)(?=\n\*\*\[|\n---|\Z)'
        matches = re.findall(pattern, history, re.DOTALL)

        for role, content in matches:
            messages.append({
                "role": "user" if role == "USER" else "assistant",
                "content": content.strip()
            })

        return messages

    async def chat(
        self,
        org_id: str,
        session_id: str,
        user_message: str,
        include_grants: bool = False
    ) -> Dict[str, Any]:
        """
        Process a chat message and get agent response.
        
        Args:
            org_id: Organization ID
            session_id: Session ID
            user_message: User's message
            include_grants: Whether to include recent grants in context
            
        Returns:
            Agent response with metadata
        """
        # Ensure workspace exists
        self.workspace.init_workspace(org_id)

        # Build system prompt
        system_prompt = self._build_system_prompt(org_id)

        # Add grants context if requested
        if include_grants and self.supabase:
            grants_context = await self._get_grants_context(org_id)
            if grants_context:
                system_prompt += f"\n\n## Recent Grant Opportunities\n{grants_context}"

        # Get conversation history
        messages = self._get_session_messages(org_id, session_id)

        # Add new user message
        messages.append({"role": "user", "content": user_message})

        # Save user message to session
        self.workspace.append_to_session(org_id, session_id, "user", user_message)

        # Call Claude
        try:
            client = get_claude_client()
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                system=system_prompt,
                messages=messages
            )

            assistant_message = response.content[0].text

            # Save assistant response to session
            self.workspace.append_to_session(org_id, session_id, "agent", assistant_message)

            # Check for decisions to save
            self._extract_and_save_decisions(org_id, assistant_message)

            return {
                "response": assistant_message,
                "session_id": session_id,
                "tokens_used": {
                    "input": response.usage.input_tokens,
                    "output": response.usage.output_tokens
                },
                "model": response.model
            }

        except Exception as e:
            error_msg = f"Error calling Claude: {str(e)}"
            print(f"[SESSION] {error_msg}")
            return {
                "response": "I'm sorry, I encountered an error processing your request. Please try again.",
                "error": error_msg,
                "session_id": session_id
            }

    async def _get_grants_context(self, org_id: str, limit: int = 10) -> str:
        """Get recent matched grants for context"""
        if not self.supabase:
            return ""

        try:
            # Get org's matched grants
            result = self.supabase.table("matched_grants") \
                .select("grant_id, match_score, scraped_grants(title, agency, deadline, amount_max)") \
                .eq("organization_id", org_id) \
                .order("match_score", desc=True) \
                .limit(limit) \
                .execute()

            if not result.data:
                return ""

            grants_text = []
            for match in result.data:
                grant = match.get("scraped_grants", {})
                if grant:
                    grants_text.append(
                        f"- **{grant.get('title', 'Untitled')}** ({match.get('match_score', 0)}% match)\n"
                        f"  Agency: {grant.get('agency', 'Unknown')}\n"
                        f"  Amount: Up to ${grant.get('amount_max', 0):,}\n"
                        f"  Deadline: {grant.get('deadline', 'TBD')}"
                    )

            return "\n".join(grants_text)

        except Exception as e:
            print(f"[SESSION] Error fetching grants context: {e}")
            return ""

    def _extract_and_save_decisions(self, org_id: str, message: str):
        """Extract decisions/preferences from agent response and save"""
        # Look for decision markers
        decision_markers = [
            "I'll remember that",
            "noted for future",
            "I've recorded",
            "preference saved",
            "decision:",
            "going forward,",
        ]

        message_lower = message.lower()
        for marker in decision_markers:
            if marker in message_lower:
                # Extract the sentence containing the marker
                sentences = message.split(". ")
                for sentence in sentences:
                    if marker in sentence.lower():
                        self.workspace.update_decisions(org_id, sentence.strip())
                        break
                break

    async def start_session(self, org_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Start a new conversation session"""
        result = self.workspace.create_session(org_id, session_id)

        # Add initial context to session
        context = self.workspace.get_agent_context(org_id)
        has_profile = bool(context.get("profile", "").strip())

        return {
            **result,
            "has_profile": has_profile,
            "greeting": self._get_greeting(org_id, has_profile)
        }

    def _get_greeting(self, org_id: str, has_profile: bool) -> str:
        """Get contextual greeting for new session"""
        if not has_profile:
            return (
                "👋 Hi! I'm FundFish, your grant research assistant. "
                "I don't have much information about your organization yet. "
                "Would you like to tell me about your mission and programs so I can find relevant grants?"
            )

        context = self.workspace.get_agent_context(org_id)
        profile = context.get("profile", "")

        # Extract org name from profile
        import re
        name_match = re.search(r'\*\*Name:\*\* (.+)', profile)
        org_name = name_match.group(1) if name_match else "your organization"

        return (
            f"👋 Welcome back! I'm here to help {org_name} find and win grants. "
            "What would you like to work on today?\n\n"
            "You can ask me to:\n"
            "- Find new grant opportunities\n"
            "- Review a specific grant's fit\n"
            "- Help draft application content\n"
            "- Update your organization profile"
        )


# Singleton
_session_service: Optional[SessionService] = None


def get_session_service(supabase=None) -> SessionService:
    """Get or create session service singleton"""
    global _session_service
    if _session_service is None:
        _session_service = SessionService(supabase)
    elif supabase and _session_service.supabase is None:
        _session_service.supabase = supabase
    return _session_service

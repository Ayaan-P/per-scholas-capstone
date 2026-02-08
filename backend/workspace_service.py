"""
Workspace Service - File-based per-org workspaces for agentic architecture

Each organization gets an isolated workspace:
  /workspaces/{org_id}/
    PROFILE.md      # Synced from DB, agent-readable org context
    STYLE.md        # Writing voice, tone, preferences
    memory/
      sessions/     # Conversation history per session
      decisions.md  # Key decisions and preferences
    grants/
      saved/        # Grants user is tracking
      applied/      # Grants user has applied to
    documents/
      extracted/    # Extracted text from uploaded docs

This enables:
- Agent can read org context as markdown (not just DB queries)
- Session history persists across restarts
- File-based memory for agent reasoning
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import uuid

# Default workspace root - can be overridden via env var
WORKSPACE_ROOT = os.getenv("FUNDFISH_WORKSPACE_ROOT", "/var/fundfish/workspaces")


class WorkspaceService:
    """Manages file-based workspaces for organizations"""

    def __init__(self, workspace_root: Optional[str] = None):
        self.root = Path(workspace_root or WORKSPACE_ROOT)
        self._ensure_root()

    def _ensure_root(self):
        """Ensure workspace root directory exists"""
        self.root.mkdir(parents=True, exist_ok=True)

    def _org_path(self, org_id: str) -> Path:
        """Get the workspace path for an organization"""
        return self.root / org_id

    def _ensure_workspace(self, org_id: str) -> Path:
        """Ensure workspace exists with proper structure"""
        workspace = self._org_path(org_id)
        
        # Create directory structure
        dirs = [
            workspace,
            workspace / "memory" / "sessions",
            workspace / "grants" / "saved",
            workspace / "grants" / "applied",
            workspace / "documents" / "extracted",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # Create default files if they don't exist
        profile_path = workspace / "PROFILE.md"
        if not profile_path.exists():
            profile_path.write_text(self._default_profile())

        style_path = workspace / "STYLE.md"
        if not style_path.exists():
            style_path.write_text(self._default_style())

        decisions_path = workspace / "memory" / "decisions.md"
        if not decisions_path.exists():
            decisions_path.write_text(self._default_decisions())

        return workspace

    # ========================================
    # Default file templates
    # ========================================

    def _default_profile(self) -> str:
        return """# Organization Profile

*This file is synced from your organization settings. The agent reads this to understand your org.*

## Basic Info
- **Name:** (not set)
- **Mission:** (not set)
- **EIN:** (not set)

## Focus Areas
(not set)

## Programs
(not set)

## Target Demographics
(not set)

## Capacity
- **Annual Budget:** (not set)
- **Staff Size:** (not set)
- **Grant Writing Capacity:** (not set)

---
*Last synced: never*
"""

    def _default_style(self) -> str:
        return """# Writing Style Guide

*Tell the agent how you want proposals written.*

## Voice & Tone
- Professional but warm
- Data-driven with human stories
- Confident, not boastful

## Preferences
- Use active voice
- Lead with impact, not need
- Include specific metrics when possible

## Avoid
- Jargon without explanation
- Deficit framing ("underserved" → "historically excluded")
- Vague claims without evidence

## Sample Phrases
(Add phrases from successful past proposals)

---
*Edit this file to customize how the agent writes for you.*
"""

    def _default_decisions(self) -> str:
        return f"""# Decisions & Preferences

*Key decisions and learnings the agent should remember.*

## Grant Preferences
- (none yet)

## Rejected Approaches
- (none yet)

## Notes
- (none yet)

---
*Created: {datetime.now().isoformat()}*
"""

    # ========================================
    # Workspace initialization
    # ========================================

    def init_workspace(self, org_id: str) -> Dict[str, Any]:
        """Initialize a workspace for a new organization"""
        workspace = self._ensure_workspace(org_id)
        return {
            "org_id": org_id,
            "path": str(workspace),
            "created": True,
            "structure": {
                "profile": str(workspace / "PROFILE.md"),
                "style": str(workspace / "STYLE.md"),
                "memory": str(workspace / "memory"),
                "grants": str(workspace / "grants"),
                "documents": str(workspace / "documents"),
            }
        }

    def workspace_exists(self, org_id: str) -> bool:
        """Check if workspace exists for an organization"""
        return self._org_path(org_id).exists()

    # ========================================
    # Profile sync (DB → files)
    # ========================================

    def sync_profile_from_db(self, org_id: str, org_config: Dict[str, Any]) -> bool:
        """Sync organization profile from database to PROFILE.md"""
        workspace = self._ensure_workspace(org_id)
        profile_path = workspace / "PROFILE.md"

        content = f"""# Organization Profile

*This file is synced from your organization settings. The agent reads this to understand your org.*

## Basic Info
- **Name:** {org_config.get('name', '(not set)')}
- **Mission:** {org_config.get('mission', '(not set)')}
- **EIN:** {org_config.get('ein', '(not set)')}
- **Type:** {org_config.get('organization_type', 'nonprofit')}
- **Tax Status:** {org_config.get('tax_exempt_status', '(not set)')}
- **Years Established:** {org_config.get('years_established', '(not set)')}

## Contact
- **Website:** {org_config.get('website_url', '(not set)')}
- **Email:** {org_config.get('contact_email', '(not set)')}
- **Phone:** {org_config.get('contact_phone', '(not set)')}

## Focus Areas
{self._format_list(org_config.get('focus_areas', []))}

## Programs
{self._format_list(org_config.get('programs', []))}

## Target Demographics
{self._format_list(org_config.get('target_demographics', []))}

## Service Regions
{self._format_list(org_config.get('service_regions', []))}

## Capacity
- **Annual Budget:** {org_config.get('annual_budget', '(not set)')}
- **Staff Size:** {org_config.get('staff_size', '(not set)')}
- **Board Size:** {org_config.get('board_size', '(not set)')}
- **Grant Writing Capacity:** {org_config.get('grant_writing_capacity', 'moderate')}
- **Matching Fund Capacity:** {org_config.get('matching_fund_capacity', 0)}

## Grant Preferences
- **Preferred Size:** ${org_config.get('preferred_grant_size_min', 0):,} - ${org_config.get('preferred_grant_size_max', 0):,}
- **Funding Priorities:** {', '.join(org_config.get('funding_priorities', [])) or '(not set)'}

## Impact Metrics
{self._format_metrics(org_config.get('impact_metrics', {}))}

## Partnerships & Accreditations
- **Key Partnerships:** {', '.join(org_config.get('key_partnerships', [])) or '(not set)'}
- **Accreditations:** {', '.join(org_config.get('accreditations', [])) or '(not set)'}

## Previous Grants
{self._format_list(org_config.get('previous_grants', []))}

---
*Last synced: {datetime.now().isoformat()}*
"""
        profile_path.write_text(content)
        return True

    def _format_list(self, items: List[Any]) -> str:
        """Format a list as markdown bullets"""
        if not items:
            return "(none)"
        return "\n".join(f"- {item}" for item in items)

    def _format_metrics(self, metrics: Dict[str, Any]) -> str:
        """Format metrics dict as markdown"""
        if not metrics:
            return "(none)"
        return "\n".join(f"- **{k}:** {v}" for k, v in metrics.items())

    # ========================================
    # Session management
    # ========================================

    def create_session(self, org_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new conversation session"""
        workspace = self._ensure_workspace(org_id)
        session_id = session_id or str(uuid.uuid4())[:8]
        session_path = workspace / "memory" / "sessions" / f"{session_id}.md"

        content = f"""# Session {session_id}

*Started: {datetime.now().isoformat()}*

## Context
(Agent will add context here)

## Conversation
(Messages will be appended here)

## Decisions Made
(Key decisions from this session)

---
"""
        session_path.write_text(content)
        return {
            "session_id": session_id,
            "path": str(session_path),
            "created": datetime.now().isoformat()
        }

    def append_to_session(self, org_id: str, session_id: str, role: str, content: str) -> bool:
        """Append a message to session history"""
        workspace = self._org_path(org_id)
        session_path = workspace / "memory" / "sessions" / f"{session_id}.md"

        if not session_path.exists():
            return False

        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"\n**[{timestamp}] {role.upper()}:** {content}\n"

        with open(session_path, "a") as f:
            f.write(entry)

        return True

    def get_session_history(self, org_id: str, session_id: str) -> Optional[str]:
        """Get full session history as markdown"""
        workspace = self._org_path(org_id)
        session_path = workspace / "memory" / "sessions" / f"{session_id}.md"

        if not session_path.exists():
            return None

        return session_path.read_text()

    def list_sessions(self, org_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent sessions for an organization"""
        workspace = self._org_path(org_id)
        sessions_dir = workspace / "memory" / "sessions"

        if not sessions_dir.exists():
            return []

        sessions = []
        for f in sorted(sessions_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:limit]:
            sessions.append({
                "session_id": f.stem,
                "path": str(f),
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })

        return sessions

    # ========================================
    # Grant tracking
    # ========================================

    def save_grant(self, org_id: str, grant_id: str, grant_data: Dict[str, Any]) -> bool:
        """Save a grant to the workspace"""
        workspace = self._ensure_workspace(org_id)
        grant_path = workspace / "grants" / "saved" / f"{grant_id}.json"
        grant_path.write_text(json.dumps(grant_data, indent=2, default=str))
        return True

    def get_saved_grants(self, org_id: str) -> List[Dict[str, Any]]:
        """Get all saved grants for an organization"""
        workspace = self._org_path(org_id)
        saved_dir = workspace / "grants" / "saved"

        if not saved_dir.exists():
            return []

        grants = []
        for f in saved_dir.glob("*.json"):
            try:
                grants.append(json.loads(f.read_text()))
            except Exception:
                pass

        return grants

    # ========================================
    # Document storage
    # ========================================

    def save_extracted_text(self, org_id: str, doc_id: str, filename: str, text: str) -> bool:
        """Save extracted document text to workspace"""
        workspace = self._ensure_workspace(org_id)
        doc_path = workspace / "documents" / "extracted" / f"{doc_id}.md"

        content = f"""# {filename}

*Extracted: {datetime.now().isoformat()}*

---

{text}
"""
        doc_path.write_text(content)
        return True

    # ========================================
    # Agent context building
    # ========================================

    def get_agent_context(self, org_id: str) -> Dict[str, str]:
        """Get all context files for agent consumption"""
        workspace = self._org_path(org_id)

        if not workspace.exists():
            return {}

        context = {}

        # Profile
        profile_path = workspace / "PROFILE.md"
        if profile_path.exists():
            context["profile"] = profile_path.read_text()

        # Style guide
        style_path = workspace / "STYLE.md"
        if style_path.exists():
            context["style"] = style_path.read_text()

        # Decisions
        decisions_path = workspace / "memory" / "decisions.md"
        if decisions_path.exists():
            context["decisions"] = decisions_path.read_text()

        return context

    def update_decisions(self, org_id: str, decision: str) -> bool:
        """Append a decision to the decisions file"""
        workspace = self._ensure_workspace(org_id)
        decisions_path = workspace / "memory" / "decisions.md"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n- [{timestamp}] {decision}\n"

        with open(decisions_path, "a") as f:
            f.write(entry)

        return True


# Singleton instance
_workspace_service: Optional[WorkspaceService] = None


def get_workspace_service() -> WorkspaceService:
    """Get or create the workspace service singleton"""
    global _workspace_service
    if _workspace_service is None:
        _workspace_service = WorkspaceService()
    return _workspace_service

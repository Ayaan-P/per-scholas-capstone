"""
Workspace Service - File-based per-org workspaces for agentic architecture

Enhanced for FundFish with:
- Daily memory logs (memory/YYYY-MM-DD.md)
- Brief history (memory/briefs/YYYY-MM-DD.md)
- Grant research notes (grants/grant-{id}.md)
- Automatic cleanup/archiving of old sessions
- Template-based initialization

Each organization gets an isolated workspace:
  /workspaces/{org_id}/
    PROFILE.md      # Synced from DB, agent-readable org context
    STYLE.md        # Writing voice, tone, preferences
    TOOLS.md        # Reference for available tools
    DECISIONS.md    # Key decisions and preferences (learning log)
    memory/
      YYYY-MM-DD.md       # Daily activity logs
      briefs/
        YYYY-MM-DD.md     # Morning brief copies
      sessions/           # Conversation history per session
    grants/
      grant-{id}.md       # Research notes per grant
      saved/              # Legacy: saved grants (JSON)
      applied/            # Legacy: applied grants
    proposals/
      draft-{id}.md       # Proposal drafts
    documents/
      extracted/          # Extracted text from uploads
    archive/              # Archived old sessions/logs
"""

import os
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import uuid

# Default workspace root - can be overridden via env var
WORKSPACE_ROOT = os.getenv("FUNDFISH_WORKSPACE_ROOT", "/var/fundfish/workspaces")

# Template directory (relative to this file)
TEMPLATE_DIR = Path(__file__).parent / "agent_templates" / "fundfish"

# Archive settings
ARCHIVE_AFTER_DAYS = 30  # Archive sessions older than this
MAX_MEMORY_FILES = 90    # Keep max 90 days of memory files


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
            workspace / "memory" / "briefs",
            workspace / "grants" / "saved",
            workspace / "grants" / "applied",
            workspace / "proposals",
            workspace / "documents" / "extracted",
            workspace / "archive" / "sessions",
            workspace / "archive" / "memory",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

        # Initialize from templates if files don't exist
        self._init_from_templates(workspace)

        return workspace

    def _init_from_templates(self, workspace: Path):
        """Initialize workspace files from templates"""
        now = datetime.now().isoformat()
        
        template_files = {
            "PROFILE.md": self._default_profile,
            "STYLE.md": self._default_style,
            "TOOLS.md": self._default_tools,
            "DECISIONS.md": self._default_decisions,
        }
        
        for filename, default_fn in template_files.items():
            file_path = workspace / filename
            if not file_path.exists():
                # Try loading from template file first
                template_path = TEMPLATE_DIR / filename
                if template_path.exists():
                    content = template_path.read_text()
                    # Replace basic placeholders
                    content = content.replace("{{created_at}}", now)
                    content = content.replace("{{updated_at}}", now)
                    content = content.replace("{{last_updated}}", now)
                    content = content.replace("{{last_synced}}", "never")
                else:
                    content = default_fn()
                file_path.write_text(content)

    # ========================================
    # Default file templates (fallbacks)
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

---
*Edit this file to customize how the agent writes for you.*
"""

    def _default_tools(self) -> str:
        return """# Agent Tools Reference

See TOOLS.md template for full documentation.

## Quick Reference
- Grants API: Search, score, save, dismiss
- Workspace: Read context, log memory, save research
- Proposals: Draft sections, review content
- Documents: Extract text, search content

---
*Tools reference v1.0*
"""

    def _default_decisions(self) -> str:
        return f"""# Decisions & Learning Log

*Key decisions and learnings the agent should remember.*

## Grant Preferences
- (none yet)

## User Feedback
- (none yet)

## Communication Preferences
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
                "tools": str(workspace / "TOOLS.md"),
                "decisions": str(workspace / "DECISIONS.md"),
                "memory": str(workspace / "memory"),
                "grants": str(workspace / "grants"),
                "proposals": str(workspace / "proposals"),
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
- **Annual Budget:** ${org_config.get('annual_budget', 0):,}
- **Staff Size:** {org_config.get('staff_size', '(not set)')}
- **Board Size:** {org_config.get('board_size', '(not set)')}
- **Grant Writing Capacity:** {org_config.get('grant_writing_capacity', 'moderate')}
- **Matching Fund Capacity:** {org_config.get('matching_fund_capacity', 0)}%

## Grant Preferences
- **Preferred Size:** ${org_config.get('preferred_grant_size_min', 0):,} - ${org_config.get('preferred_grant_size_max', 0):,}
- **Funding Priorities:** {', '.join(org_config.get('funding_priorities', [])) or '(not set)'}

## Impact Metrics
{self._format_metrics(org_config.get('impact_metrics', {}))}

## Track Record
### Previous Grants
{self._format_list(org_config.get('previous_grants', []))}

### Key Partnerships
{self._format_list(org_config.get('key_partnerships', []))}

### Accreditations
{self._format_list(org_config.get('accreditations', []))}

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
    # Daily Memory Management
    # ========================================

    def _today_str(self) -> str:
        """Get today's date as YYYY-MM-DD string"""
        return datetime.now().strftime("%Y-%m-%d")

    def _get_memory_path(self, org_id: str, date: Optional[str] = None) -> Path:
        """Get path to daily memory file"""
        workspace = self._org_path(org_id)
        date = date or self._today_str()
        return workspace / "memory" / f"{date}.md"

    def log_memory(self, org_id: str, entry: str, entry_type: str = "note") -> bool:
        """
        Log an entry to today's memory file.
        
        Args:
            org_id: Organization ID
            entry: The content to log
            entry_type: One of 'note', 'decision', 'observation', 'feedback', 'action'
        """
        self._ensure_workspace(org_id)
        memory_path = self._get_memory_path(org_id)
        
        # Create file with header if it doesn't exist
        if not memory_path.exists():
            today = datetime.now().strftime("%A, %B %d, %Y")
            header = f"""# Memory Log - {today}

*Daily activity log for agent context*

---

"""
            memory_path.write_text(header)
        
        # Append entry
        timestamp = datetime.now().strftime("%H:%M")
        type_emoji = {
            "note": "📝",
            "decision": "✅",
            "observation": "👁️",
            "feedback": "💬",
            "action": "⚡",
        }.get(entry_type, "•")
        
        formatted_entry = f"\n**[{timestamp}]** {type_emoji} {entry}\n"
        
        with open(memory_path, "a") as f:
            f.write(formatted_entry)
        
        return True

    def get_memory(self, org_id: str, date: Optional[str] = None) -> Optional[str]:
        """Get memory log for a specific date (defaults to today)"""
        memory_path = self._get_memory_path(org_id, date)
        if memory_path.exists():
            return memory_path.read_text()
        return None

    def get_recent_memory(self, org_id: str, days: int = 2) -> Dict[str, str]:
        """Get memory logs for recent days"""
        result = {}
        for i in range(days):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            content = self.get_memory(org_id, date)
            if content:
                result[date] = content
        return result

    # ========================================
    # Brief History Management
    # ========================================

    def _get_brief_path(self, org_id: str, date: Optional[str] = None) -> Path:
        """Get path to brief file for a date"""
        workspace = self._org_path(org_id)
        date = date or self._today_str()
        return workspace / "memory" / "briefs" / f"{date}.md"

    def save_brief(self, org_id: str, subject: str, content: str, 
                   grant_ids: List[str], date: Optional[str] = None) -> bool:
        """
        Save a morning brief to the workspace.
        
        Args:
            org_id: Organization ID
            subject: Brief subject line
            content: Full brief content (markdown)
            grant_ids: List of grant IDs featured in this brief
            date: Optional date override (defaults to today)
        """
        self._ensure_workspace(org_id)
        brief_path = self._get_brief_path(org_id, date)
        
        date_str = date or self._today_str()
        timestamp = datetime.now().isoformat()
        
        full_content = f"""# Morning Brief - {date_str}

**Subject:** {subject}
**Generated:** {timestamp}
**Featured Grants:** {', '.join(grant_ids)}

---

{content}

---
*This brief was auto-generated by your FundFish agent.*
"""
        brief_path.write_text(full_content)
        
        # Also log to memory
        self.log_memory(org_id, f"Sent morning brief: {subject}", "action")
        
        return True

    def get_brief(self, org_id: str, date: Optional[str] = None) -> Optional[str]:
        """Get brief for a specific date"""
        brief_path = self._get_brief_path(org_id, date)
        if brief_path.exists():
            return brief_path.read_text()
        return None

    def list_briefs(self, org_id: str, limit: int = 7) -> List[Dict[str, Any]]:
        """List recent briefs"""
        workspace = self._org_path(org_id)
        briefs_dir = workspace / "memory" / "briefs"
        
        if not briefs_dir.exists():
            return []
        
        briefs = []
        for f in sorted(briefs_dir.glob("*.md"), key=lambda x: x.name, reverse=True)[:limit]:
            briefs.append({
                "date": f.stem,
                "path": str(f),
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
        
        return briefs

    # ========================================
    # Grant Research Notes
    # ========================================

    def _get_grant_research_path(self, org_id: str, grant_id: str) -> Path:
        """Get path to grant research file"""
        workspace = self._org_path(org_id)
        # Sanitize grant_id for filename
        safe_id = grant_id.replace("/", "-").replace("\\", "-")[:50]
        return workspace / "grants" / f"grant-{safe_id}.md"

    def save_grant_research(self, org_id: str, grant_id: str, 
                            grant_data: Dict[str, Any],
                            analysis: Optional[str] = None,
                            eligibility: Optional[Dict[str, Any]] = None,
                            notes: Optional[str] = None) -> bool:
        """
        Save detailed research notes for a grant.
        
        Args:
            org_id: Organization ID
            grant_id: Grant ID (from scraped_grants or external)
            grant_data: Basic grant information
            analysis: AI-generated match analysis
            eligibility: Eligibility check results
            notes: Additional agent/user notes
        """
        self._ensure_workspace(org_id)
        research_path = self._get_grant_research_path(org_id, grant_id)
        
        timestamp = datetime.now().isoformat()
        
        content = f"""# Grant Research: {grant_data.get('title', 'Unknown')}

**Grant ID:** {grant_id}
**Funder:** {grant_data.get('funder', 'Unknown')}
**Amount:** ${grant_data.get('amount_min', 0):,} - ${grant_data.get('amount_max', 0):,}
**Deadline:** {grant_data.get('deadline', 'Unknown')}
**Source:** {grant_data.get('source', 'Unknown')}
**Application URL:** {grant_data.get('application_url', 'N/A')}

---

## Description
{grant_data.get('description', '(No description available)')}

---

## Match Analysis
{analysis or '(Not yet analyzed)'}

---

## Eligibility Check
"""
        
        if eligibility:
            content += "\n".join(f"- **{k}:** {v}" for k, v in eligibility.items())
        else:
            content += "(Not yet checked)"
        
        content += f"""

---

## Agent Notes
{notes or '(No notes yet)'}

---

## Requirements
{self._format_dict(grant_data.get('requirements', {}))}

---

*Research started: {timestamp}*
*Last updated: {timestamp}*
"""
        research_path.write_text(content)
        
        # Log to memory
        self.log_memory(org_id, f"Researched grant: {grant_data.get('title', grant_id)}", "action")
        
        return True

    def get_grant_research(self, org_id: str, grant_id: str) -> Optional[str]:
        """Get research notes for a grant"""
        research_path = self._get_grant_research_path(org_id, grant_id)
        if research_path.exists():
            return research_path.read_text()
        return None

    def update_grant_notes(self, org_id: str, grant_id: str, notes: str) -> bool:
        """Append notes to existing grant research"""
        research_path = self._get_grant_research_path(org_id, grant_id)
        
        if not research_path.exists():
            return False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        
        # Read current content
        content = research_path.read_text()
        
        # Find and update notes section
        if "## Agent Notes" in content:
            parts = content.split("## Agent Notes")
            before = parts[0]
            after = parts[1].split("---", 1)
            updated_notes = f"\n**[{timestamp}]** {notes}\n" + after[0] if len(after) > 1 else ""
            remaining = "---" + after[1] if len(after) > 1 else ""
            
            new_content = before + "## Agent Notes" + updated_notes + remaining
            research_path.write_text(new_content)
        else:
            # Just append
            with open(research_path, "a") as f:
                f.write(f"\n\n**[{timestamp}]** {notes}\n")
        
        return True

    def list_grant_research(self, org_id: str) -> List[Dict[str, Any]]:
        """List all grant research files"""
        workspace = self._org_path(org_id)
        grants_dir = workspace / "grants"
        
        if not grants_dir.exists():
            return []
        
        grants = []
        for f in grants_dir.glob("grant-*.md"):
            grants.append({
                "grant_id": f.stem.replace("grant-", ""),
                "path": str(f),
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat()
            })
        
        return sorted(grants, key=lambda x: x["modified"], reverse=True)

    def _format_dict(self, d: Dict[str, Any]) -> str:
        """Format a dict as markdown"""
        if not d:
            return "(none)"
        return "\n".join(f"- **{k}:** {v}" for k, v in d.items())

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
    # Cleanup & Archiving
    # ========================================

    def cleanup_old_sessions(self, org_id: str, days: int = ARCHIVE_AFTER_DAYS) -> Dict[str, int]:
        """
        Archive sessions older than specified days.
        
        Returns count of archived items.
        """
        workspace = self._org_path(org_id)
        sessions_dir = workspace / "memory" / "sessions"
        archive_dir = workspace / "archive" / "sessions"
        
        if not sessions_dir.exists():
            return {"sessions_archived": 0}
        
        archive_dir.mkdir(parents=True, exist_ok=True)
        cutoff = datetime.now() - timedelta(days=days)
        
        archived = 0
        for f in sessions_dir.glob("*.md"):
            if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                dest = archive_dir / f.name
                shutil.move(str(f), str(dest))
                archived += 1
        
        return {"sessions_archived": archived}

    def cleanup_old_memory(self, org_id: str, max_files: int = MAX_MEMORY_FILES) -> Dict[str, int]:
        """
        Archive memory files beyond max_files limit.
        
        Keeps the most recent max_files, archives the rest.
        """
        workspace = self._org_path(org_id)
        memory_dir = workspace / "memory"
        archive_dir = workspace / "archive" / "memory"
        
        # Get all date-based memory files (YYYY-MM-DD.md pattern)
        memory_files = sorted(
            [f for f in memory_dir.glob("*.md") if len(f.stem) == 10],  # YYYY-MM-DD format
            key=lambda x: x.name,
            reverse=True
        )
        
        if len(memory_files) <= max_files:
            return {"memory_archived": 0}
        
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        archived = 0
        for f in memory_files[max_files:]:
            dest = archive_dir / f.name
            shutil.move(str(f), str(dest))
            archived += 1
        
        return {"memory_archived": archived}

    def full_cleanup(self, org_id: str) -> Dict[str, Any]:
        """Run all cleanup tasks for an org"""
        sessions = self.cleanup_old_sessions(org_id)
        memory = self.cleanup_old_memory(org_id)
        
        return {
            **sessions,
            **memory,
            "timestamp": datetime.now().isoformat()
        }

    # ========================================
    # Legacy: Grant tracking (JSON-based)
    # ========================================

    def save_grant(self, org_id: str, grant_id: str, grant_data: Dict[str, Any]) -> bool:
        """Save a grant to the workspace (legacy JSON format)"""
        workspace = self._ensure_workspace(org_id)
        grant_path = workspace / "grants" / "saved" / f"{grant_id}.json"
        grant_path.write_text(json.dumps(grant_data, indent=2, default=str))
        return True

    def get_saved_grants(self, org_id: str) -> List[Dict[str, Any]]:
        """Get all saved grants for an organization (legacy)"""
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

        # Core files
        for filename, key in [
            ("PROFILE.md", "profile"),
            ("STYLE.md", "style"),
            ("TOOLS.md", "tools"),
            ("DECISIONS.md", "decisions"),
        ]:
            file_path = workspace / filename
            if file_path.exists():
                context[key] = file_path.read_text()

        # Recent memory (today + yesterday)
        recent_memory = self.get_recent_memory(org_id, days=2)
        if recent_memory:
            context["recent_memory"] = "\n\n---\n\n".join(
                f"## {date}\n{content}" for date, content in recent_memory.items()
            )

        return context

    def update_decisions(self, org_id: str, decision: str) -> bool:
        """Append a decision to the decisions file"""
        workspace = self._ensure_workspace(org_id)
        decisions_path = workspace / "DECISIONS.md"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = f"\n- [{timestamp}] {decision}\n"

        with open(decisions_path, "a") as f:
            f.write(entry)
        
        # Also log to daily memory
        self.log_memory(org_id, decision, "decision")

        return True


# Singleton instance
_workspace_service: Optional[WorkspaceService] = None


def get_workspace_service() -> WorkspaceService:
    """Get or create the workspace service singleton"""
    global _workspace_service
    if _workspace_service is None:
        _workspace_service = WorkspaceService()
    return _workspace_service

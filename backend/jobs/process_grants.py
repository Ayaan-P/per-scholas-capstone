"""
Grant Processing Job - Batch processing of scraped grants

Triggered by:
- Cron (nightly after discovery completes)
- On-demand (user opens dashboard, requests re-score)
- Webhook (when new grants are scraped)

Workflow:
1. Query new/updated grants from scraped_grants
2. For each org:
   - Load org profile
   - Score grants against org
   - Write results to org_grants
3. Log processing to workspace memory
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("process_grants")

# Try to import project modules
try:
    from scoring_agent import ScoringAgent, ScoringResult
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from scoring_agent import ScoringAgent, ScoringResult


@dataclass
class ProcessingConfig:
    """Configuration for grant processing job"""
    workspace_root: str = "/var/fundfish/workspaces"
    max_grants_per_run: int = 100
    score_threshold: int = 20  # Minimum score to save
    use_llm: bool = True
    batch_size: int = 10
    dry_run: bool = False


class GrantProcessingJob:
    """
    Processes scraped grants for an organization.
    
    Queries new grants from scraped_grants, scores them,
    and writes qualified results to org_grants.
    """
    
    def __init__(
        self,
        supabase_client,
        config: Optional[ProcessingConfig] = None
    ):
        self.supabase = supabase_client
        self.config = config or ProcessingConfig()
        self.stats = {
            "started_at": None,
            "completed_at": None,
            "grants_fetched": 0,
            "grants_scored": 0,
            "grants_saved": 0,
            "grants_skipped": 0,
            "errors": 0,
            "total_tokens": 0,
            "orgs_processed": [],
        }
    
    async def run(
        self,
        org_id: str,
        since: Optional[datetime] = None,
        force_rescore: bool = False
    ) -> Dict[str, Any]:
        """
        Run the processing job for an organization.
        
        Args:
            org_id: Organization ID to process grants for
            since: Only process grants created after this time (default: 24h ago)
            force_rescore: Re-score even if grant was already scored
            
        Returns:
            Processing statistics
        """
        self.stats["started_at"] = datetime.now().isoformat()
        self.stats["orgs_processed"].append(org_id)
        
        logger.info(f"[ProcessGrants] Starting job for org {org_id}")
        
        try:
            # Initialize scoring agent
            agent = ScoringAgent(org_id, self.config.workspace_root)
            agent.load_org_profile()
            
            # Fetch grants to process
            grants = await self._fetch_grants(org_id, since, force_rescore)
            self.stats["grants_fetched"] = len(grants)
            
            if not grants:
                logger.info(f"[ProcessGrants] No new grants to process for org {org_id}")
                return self._finalize_stats()
            
            logger.info(f"[ProcessGrants] Processing {len(grants)} grants")
            
            # Process in batches
            for i in range(0, len(grants), self.config.batch_size):
                batch = grants[i:i + self.config.batch_size]
                await self._process_batch(agent, org_id, batch)
            
            # Log to workspace memory
            await self._log_to_memory(org_id, agent.get_stats())
            
            self.stats["total_tokens"] = agent.get_stats()["total_tokens"]
            
        except FileNotFoundError as e:
            logger.error(f"[ProcessGrants] Org profile not found: {e}")
            self.stats["errors"] += 1
        except Exception as e:
            logger.error(f"[ProcessGrants] Error processing grants: {e}")
            self.stats["errors"] += 1
            raise
        
        return self._finalize_stats()
    
    async def _fetch_grants(
        self,
        org_id: str,
        since: Optional[datetime] = None,
        force_rescore: bool = False
    ) -> List[Dict[str, Any]]:
        """Fetch grants from scraped_grants that need processing"""
        
        if since is None:
            since = datetime.now() - timedelta(days=1)
        
        try:
            # Fetch new/updated grants from scraped_grants
            query = self.supabase.table("scraped_grants")\
                .select("*")\
                .gte("created_at", since.isoformat())\
                .order("created_at", desc=True)\
                .limit(self.config.max_grants_per_run)
            
            response = query.execute()
            grants = response.data or []
            
            if not force_rescore and grants:
                # Filter out already scored grants
                grant_ids = [g["id"] for g in grants]
                
                existing = self.supabase.table("org_grants")\
                    .select("grant_id")\
                    .eq("org_id", org_id)\
                    .in_("grant_id", grant_ids)\
                    .execute()
                
                existing_ids = {e["grant_id"] for e in (existing.data or [])}
                grants = [g for g in grants if g["id"] not in existing_ids]
                
                logger.info(f"[ProcessGrants] {len(existing_ids)} grants already scored, {len(grants)} remaining")
            
            return grants
            
        except Exception as e:
            logger.error(f"[ProcessGrants] Error fetching grants: {e}")
            return []
    
    async def _process_batch(
        self,
        agent: ScoringAgent,
        org_id: str,
        grants: List[Dict[str, Any]]
    ):
        """Process a batch of grants"""
        
        for grant in grants:
            try:
                # Score the grant
                result = agent.score_grant(grant, use_llm=self.config.use_llm)
                self.stats["grants_scored"] += 1
                
                # Skip low scores
                if result.match_score < self.config.score_threshold:
                    logger.debug(f"[ProcessGrants] Skipping grant {grant['id']} - score {result.match_score}")
                    self.stats["grants_skipped"] += 1
                    continue
                
                # Save to org_grants
                if not self.config.dry_run:
                    await self._save_org_grant(org_id, result)
                    self.stats["grants_saved"] += 1
                else:
                    logger.info(f"[ProcessGrants] DRY RUN: Would save grant {result.grant_id} with score {result.match_score}")
                    self.stats["grants_saved"] += 1
                
            except Exception as e:
                logger.error(f"[ProcessGrants] Error processing grant {grant.get('id', 'unknown')}: {e}")
                self.stats["errors"] += 1
    
    async def _save_org_grant(self, org_id: str, result: ScoringResult):
        """Save scored grant to org_grants table"""
        
        record = {
            "org_id": org_id,
            "grant_id": result.grant_id,
            "status": "active",
            "match_score": result.match_score,
            "llm_summary": result.summary,
            "match_reasoning": result.reasoning,
            "key_tags": result.key_tags,
            "effort_estimate": result.effort_estimate,
            "winning_strategies": result.winning_strategies,
            "tagged_at": datetime.now().isoformat(),
        }
        
        try:
            # Upsert to handle re-scoring
            self.supabase.table("org_grants")\
                .upsert(record, on_conflict="org_id,grant_id")\
                .execute()
                
            logger.info(f"[ProcessGrants] Saved grant {result.grant_id} with score {result.match_score}")
            
        except Exception as e:
            logger.error(f"[ProcessGrants] Error saving org_grant: {e}")
            raise
    
    async def _log_to_memory(self, org_id: str, agent_stats: Dict[str, Any]):
        """Log processing run to workspace memory"""
        
        memory_path = Path(self.config.workspace_root) / org_id / "memory"
        memory_path.mkdir(parents=True, exist_ok=True)
        
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = memory_path / f"{today}.md"
        
        log_entry = f"""
## Grant Processing - {datetime.now().strftime("%H:%M:%S")}

**Stats:**
- Grants fetched: {self.stats['grants_fetched']}
- Grants scored: {self.stats['grants_scored']}
- Grants saved: {self.stats['grants_saved']}
- Grants skipped: {self.stats['grants_skipped']}
- Errors: {self.stats['errors']}
- Tokens used: {agent_stats.get('total_tokens', 0)}
- Est. cost: ${agent_stats.get('estimated_cost_usd', 0):.4f}

"""
        
        # Append to daily log
        try:
            if log_file.exists():
                current = log_file.read_text()
                log_file.write_text(current + log_entry)
            else:
                log_file.write_text(f"# Memory Log - {today}\n\n" + log_entry)
        except Exception as e:
            logger.warning(f"[ProcessGrants] Could not write to memory: {e}")
    
    def _finalize_stats(self) -> Dict[str, Any]:
        """Finalize and return processing statistics"""
        self.stats["completed_at"] = datetime.now().isoformat()
        
        # Calculate duration
        if self.stats["started_at"]:
            start = datetime.fromisoformat(self.stats["started_at"])
            end = datetime.fromisoformat(self.stats["completed_at"])
            self.stats["duration_seconds"] = (end - start).total_seconds()
        
        return self.stats


# CLI entry point for cron jobs
async def main():
    """Main entry point for cron/CLI execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process grants for organizations")
    parser.add_argument("--org-id", required=True, help="Organization ID to process")
    parser.add_argument("--since-hours", type=int, default=24, help="Process grants from last N hours")
    parser.add_argument("--force", action="store_true", help="Force re-scoring of all grants")
    parser.add_argument("--dry-run", action="store_true", help="Don't save results, just log")
    parser.add_argument("--no-llm", action="store_true", help="Use rule-based scoring only")
    parser.add_argument("--workspace", default="/var/fundfish/workspaces", help="Workspace root")
    
    args = parser.parse_args()
    
    # Initialize Supabase client
    from dotenv import load_dotenv
    load_dotenv()
    
    from supabase import create_client
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    )
    
    config = ProcessingConfig(
        workspace_root=args.workspace,
        dry_run=args.dry_run,
        use_llm=not args.no_llm
    )
    
    job = GrantProcessingJob(supabase, config)
    
    since = datetime.now() - timedelta(hours=args.since_hours)
    stats = await job.run(args.org_id, since=since, force_rescore=args.force)
    
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

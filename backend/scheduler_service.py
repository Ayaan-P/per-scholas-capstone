"""
Scheduled Grant Scraping Service
Runs periodic jobs to pull grants from multiple data sources
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from typing import List, Dict, Any
import asyncio
import logging
from supabase import Client

# Import scrapers
from scrapers.grants_gov_scraper import GrantsGovScraper
from scrapers.state_scrapers import CaliforniaGrantsScraper, NewYorkGrantsScraper
from scrapers.federal_scrapers import SAMGovScraper, USASpendingScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchedulerService:
    """Manages scheduled scraping jobs for grant data sources"""

    def __init__(self, supabase_client: Client):
        self.scheduler = AsyncIOScheduler()
        self.supabase = supabase_client
        self.scrapers = self._initialize_scrapers()
        self.job_history = []

    def _initialize_scrapers(self):
        """Initialize all data source scrapers"""
        return {
            'grants_gov': GrantsGovScraper(),
            'california': CaliforniaGrantsScraper(),
            'new_york': NewYorkGrantsScraper(),
            'sam_gov': SAMGovScraper(),
            'usa_spending': USASpendingScraper()
        }

    def start(self):
        """Start the scheduler with all configured jobs"""
        logger.info("Starting scheduler service...")

        # Federal grants - run every 6 hours
        self.scheduler.add_job(
            self._scrape_grants_gov,
            trigger=IntervalTrigger(hours=6),
            id='grants_gov_job',
            name='Scrape Grants.gov',
            replace_existing=True
        )

        # SAM.gov opportunities - run every 12 hours
        self.scheduler.add_job(
            self._scrape_sam_gov,
            trigger=IntervalTrigger(hours=12),
            id='sam_gov_job',
            name='Scrape SAM.gov',
            replace_existing=True
        )

        # State grants - run daily at 2 AM
        self.scheduler.add_job(
            self._scrape_state_grants,
            trigger=CronTrigger(hour=2, minute=0),
            id='state_grants_job',
            name='Scrape State Grants',
            replace_existing=True
        )

        # City/county grants - run daily at 3 AM
        self.scheduler.add_job(
            self._scrape_local_grants,
            trigger=CronTrigger(hour=3, minute=0),
            id='local_grants_job',
            name='Scrape Local Grants',
            replace_existing=True
        )

        # Cleanup old grants - run weekly on Sunday at 4 AM
        self.scheduler.add_job(
            self._cleanup_expired_grants,
            trigger=CronTrigger(day_of_week='sun', hour=4, minute=0),
            id='cleanup_job',
            name='Cleanup Expired Grants',
            replace_existing=True
        )

        self.scheduler.start()
        logger.info("Scheduler started successfully")

        # Run initial scrape immediately on startup
        asyncio.create_task(self._run_initial_scrape())

    async def _run_initial_scrape(self):
        """Run initial scrape on startup"""
        logger.info("Running initial scrape...")
        await asyncio.sleep(5)  # Wait for system to fully initialize
        await self._scrape_grants_gov()
        logger.info("Initial scrape completed")

    async def _scrape_grants_gov(self):
        """Scrape federal grants from Grants.gov"""
        job_id = self._create_job_record('grants_gov', 'running')

        try:
            logger.info("Starting Grants.gov scrape...")
            scraper = self.scrapers['grants_gov']

            # Scrape multiple technology-related keywords
            keywords = [
                "technology workforce development",
                "STEM education",
                "digital skills training",
                "cybersecurity training",
                "software development education"
            ]

            all_grants = []
            for keyword in keywords:
                grants = await scraper.scrape(keyword, limit=5)
                all_grants.extend(grants)

            # Deduplicate by opportunity ID
            unique_grants = self._deduplicate_grants(all_grants, 'id')

            # Store in database
            saved_count = await self._store_grants(unique_grants, 'grants_gov')

            logger.info(f"Grants.gov scrape completed: {saved_count} grants saved")
            self._update_job_record(job_id, 'completed', saved_count)

        except Exception as e:
            logger.error(f"Grants.gov scrape failed: {e}")
            self._update_job_record(job_id, 'failed', 0, str(e))

    async def _scrape_sam_gov(self):
        """Scrape procurement opportunities from SAM.gov"""
        job_id = self._create_job_record('sam_gov', 'running')

        try:
            logger.info("Starting SAM.gov scrape...")
            scraper = self.scrapers['sam_gov']
            grants = await scraper.scrape(limit=20)

            saved_count = await self._store_grants(grants, 'sam_gov')

            logger.info(f"SAM.gov scrape completed: {saved_count} grants saved")
            self._update_job_record(job_id, 'completed', saved_count)

        except Exception as e:
            logger.error(f"SAM.gov scrape failed: {e}")
            self._update_job_record(job_id, 'failed', 0, str(e))

    async def _scrape_state_grants(self):
        """Scrape state-level grant databases"""
        job_id = self._create_job_record('state_grants', 'running')

        try:
            logger.info("Starting state grants scrape...")
            all_grants = []

            # California
            ca_scraper = self.scrapers['california']
            ca_grants = await ca_scraper.scrape(limit=10)
            all_grants.extend(ca_grants)

            # New York
            ny_scraper = self.scrapers['new_york']
            ny_grants = await ny_scraper.scrape(limit=10)
            all_grants.extend(ny_grants)

            saved_count = await self._store_grants(all_grants, 'state')

            logger.info(f"State grants scrape completed: {saved_count} grants saved")
            self._update_job_record(job_id, 'completed', saved_count)

        except Exception as e:
            logger.error(f"State grants scrape failed: {e}")
            self._update_job_record(job_id, 'failed', 0, str(e))

    async def _scrape_local_grants(self):
        """Scrape city and county grant opportunities"""
        job_id = self._create_job_record('local_grants', 'running')

        try:
            logger.info("Starting local grants scrape...")
            # TODO: Implement city/county scrapers
            # For now, return empty
            grants = []

            saved_count = await self._store_grants(grants, 'local')

            logger.info(f"Local grants scrape completed: {saved_count} grants saved")
            self._update_job_record(job_id, 'completed', saved_count)

        except Exception as e:
            logger.error(f"Local grants scrape failed: {e}")
            self._update_job_record(job_id, 'failed', 0, str(e))

    async def _cleanup_expired_grants(self):
        """Remove grants with past deadlines"""
        try:
            logger.info("Starting cleanup of expired grants...")

            # Delete grants with deadlines in the past
            cutoff_date = datetime.now().strftime('%Y-%m-%d')

            result = self.supabase.table("scraped_grants")\
                .delete()\
                .lt("deadline", cutoff_date)\
                .execute()

            logger.info(f"Cleanup completed: removed expired grants")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    async def _store_grants(self, grants: List[Dict[str, Any]], source: str) -> int:
        """Store scraped grants in database"""
        if not grants:
            return 0

        saved_count = 0

        for grant in grants:
            try:
                # Check if grant already exists
                existing = self.supabase.table("scraped_grants")\
                    .select("id")\
                    .eq("opportunity_id", grant.get("id"))\
                    .execute()

                if existing.data:
                    # Update existing grant
                    self.supabase.table("scraped_grants")\
                        .update({
                            "title": grant.get("title"),
                            "funder": grant.get("funder"),
                            "amount": grant.get("amount"),
                            "deadline": grant.get("deadline"),
                            "description": grant.get("description"),
                            "requirements": grant.get("requirements", []),
                            "contact": grant.get("contact"),
                            "application_url": grant.get("application_url"),
                            "match_score": grant.get("match_score", 0),
                            "updated_at": datetime.now().isoformat()
                        })\
                        .eq("opportunity_id", grant.get("id"))\
                        .execute()
                else:
                    # Insert new grant
                    self.supabase.table("scraped_grants").insert({
                        "opportunity_id": grant.get("id"),
                        "title": grant.get("title"),
                        "funder": grant.get("funder"),
                        "amount": grant.get("amount"),
                        "deadline": grant.get("deadline"),
                        "description": grant.get("description"),
                        "requirements": grant.get("requirements", []),
                        "contact": grant.get("contact"),
                        "application_url": grant.get("application_url"),
                        "match_score": grant.get("match_score", 0),
                        "source": source,
                        "status": "active",
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }).execute()

                saved_count += 1

            except Exception as e:
                logger.error(f"Failed to store grant {grant.get('id')}: {e}")
                continue

        return saved_count

    def _deduplicate_grants(self, grants: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
        """Remove duplicate grants based on key"""
        seen = set()
        unique = []

        for grant in grants:
            grant_key = grant.get(key)
            if grant_key and grant_key not in seen:
                seen.add(grant_key)
                unique.append(grant)

        return unique

    def _create_job_record(self, job_name: str, status: str) -> str:
        """Create job execution record"""
        job_record = {
            'job_name': job_name,
            'status': status,
            'started_at': datetime.now().isoformat(),
            'grants_found': 0
        }
        self.job_history.append(job_record)
        return job_name

    def _update_job_record(self, job_id: str, status: str, grants_found: int = 0, error: str = None):
        """Update job execution record"""
        for job in self.job_history:
            if job['job_name'] == job_id:
                job['status'] = status
                job['completed_at'] = datetime.now().isoformat()
                job['grants_found'] = grants_found
                if error:
                    job['error'] = error
                break

    def get_job_status(self) -> List[Dict[str, Any]]:
        """Get status of recent jobs"""
        return self.job_history[-20:]  # Return last 20 jobs

    def stop(self):
        """Stop the scheduler"""
        logger.info("Stopping scheduler service...")
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")

    async def run_job_now(self, job_name: str):
        """Manually trigger a scraping job"""
        job_map = {
            'grants_gov': self._scrape_grants_gov,
            'sam_gov': self._scrape_sam_gov,
            'state_grants': self._scrape_state_grants,
            'local_grants': self._scrape_local_grants
        }

        if job_name in job_map:
            logger.info(f"Manually triggering job: {job_name}")
            await job_map[job_name]()
        else:
            raise ValueError(f"Unknown job: {job_name}")

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
from scrapers.state_scrapers import CaliforniaGrantsScraper, NewYorkGrantsScraper, NYDOLScraper
from scrapers.federal_scrapers import SAMGovScraper, USASpendingScraper, DOLWorkforceScraper
from scrapers.gmail_scraper import GmailInboxScraper

# Import centralized keyword configuration
from search_keywords import get_keywords_for_source, get_high_priority_keywords

# Import category service
from category_service import get_category_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SchedulerService:
    """Manages scheduled scraping jobs for grant data sources"""

    def __init__(self, supabase_client: Client):
        self.scheduler = AsyncIOScheduler()
        self.supabase = supabase_client
        self.scrapers = self._initialize_scrapers()
        self.job_history = []

        # Load scheduler settings from database
        self.scheduler_settings = self._load_scheduler_settings()
        logger.info(f"Scheduler settings loaded: frequency={self.scheduler_settings['scheduler_frequency']}, locations={len(self.scheduler_settings['locations'])}")

        # Initialize semantic service for enhanced match scoring
        try:
            from semantic_service import SemanticService
            self.semantic_service = SemanticService()
            logger.info("Semantic service initialized for enhanced match scoring")
        except Exception as e:
            logger.warning(f"Could not initialize semantic service: {e}")
            self.semantic_service = None

    def _initialize_scrapers(self):
        """Initialize all data source scrapers"""
        scrapers = {
            'grants_gov': GrantsGovScraper(supabase_client=self.supabase),
            'california': CaliforniaGrantsScraper(),
            'new_york': NewYorkGrantsScraper(),
            'new_york_dol': NYDOLScraper(),
            'sam_gov': SAMGovScraper(),
            'usa_spending': USASpendingScraper(),
            'dol_workforce': DOLWorkforceScraper()
        }

        # Initialize Gmail scraper if token exists
        try:
            scrapers['gmail_inbox'] = GmailInboxScraper()
            logger.info("Gmail inbox scraper initialized successfully")
        except FileNotFoundError:
            logger.warning("Gmail token not found - skipping Gmail inbox scraper")
        except Exception as e:
            logger.error(f"Failed to initialize Gmail scraper: {e}")

        return scrapers

    def _load_scheduler_settings(self) -> Dict[str, Any]:
        """Load scheduler settings from database, fallback to defaults if not found"""
        try:
            # Try to fetch settings from database
            result = self.supabase.table("scheduler_settings").select("*").limit(1).execute()

            if result.data and len(result.data) > 0:
                settings = result.data[0]
                selected_states = settings.get("selected_states", [])
                selected_cities = settings.get("selected_cities", [])

                # Reconstruct locations as (state, city) tuples
                locations = list(zip(selected_states, selected_cities)) if selected_states and selected_cities else self._get_default_locations()

                logger.info(f"Loaded scheduler settings from database: frequency={settings.get('scheduler_frequency')}, {len(locations)} locations")
                return {
                    "scheduler_frequency": settings.get("scheduler_frequency", "weekly"),
                    "locations": locations
                }
            else:
                logger.info("No scheduler settings found in database, using defaults")
                return {
                    "scheduler_frequency": "weekly",
                    "locations": self._get_default_locations()
                }
        except Exception as e:
            logger.warning(f"Failed to load scheduler settings from database: {e}, using defaults")
            return {
                "scheduler_frequency": "weekly",
                "locations": self._get_default_locations()
            }

    def _get_default_locations(self) -> List[tuple]:
        """Get default list of target locations"""
        return [
            ("Georgia", "Atlanta"),
            ("Maryland", "Baltimore"),
            ("Massachusetts", "Boston"),
            ("Illinois", "Chicago"),
            ("Texas", "Dallas/Houston"),
            ("Colorado", "Denver"),
            ("Michigan", "Detroit"),
            ("Indiana", "Indianapolis"),
            ("Missouri", "Kansas City/St. Louis"),
            ("California", "Los Angeles/San Francisco"),
            ("New York", "New York/Newark"),
            ("Pennsylvania", "Philadelphia/Pittsburgh"),
            ("North Carolina", "Charlotte/Raleigh"),
            ("Florida", "Orlando/Tampa/Miami"),
            ("Arizona", "Phoenix"),
            ("Washington", "Seattle"),
            ("Virginia", "Washington DC/Virginia"),
            ("Ohio", "Cincinnati/Columbus/Cleveland"),
            ("Tennessee", "Nashville"),
        ]

    def _get_ai_scrape_trigger(self):
        """Get trigger for AI scraping based on scheduler_frequency setting"""
        frequency = self.scheduler_settings.get("scheduler_frequency", "weekly").lower()

        if frequency == "daily":
            # Run every day at 2 AM
            return CronTrigger(hour=2, minute=0)
        elif frequency == "weekly":
            # Run every Monday at 2 AM
            return CronTrigger(day_of_week='mon', hour=2, minute=0)
        elif frequency == "biweekly":
            # Run every other Monday at 2 AM (approximated as a custom interval)
            # Note: APScheduler doesn't directly support biweekly, so we'll use a 14-day interval
            return IntervalTrigger(days=14, start_date=datetime.now())
        elif frequency == "monthly":
            # Run on the first day of every month at 2 AM
            return CronTrigger(day=1, hour=2, minute=0)
        else:
            # Default to weekly if unknown frequency
            logger.warning(f"Unknown scheduler frequency: {frequency}, defaulting to weekly")
            return CronTrigger(day_of_week='mon', hour=2, minute=0)

    async def reload_scheduler_settings(self):
        """Reload settings from database and reschedule AI job dynamically"""
        try:
            logger.info("Reloading scheduler settings from database...")

            # Load fresh settings
            new_settings = self._load_scheduler_settings()
            self.scheduler_settings = new_settings

            # Reschedule the AI state/local opportunities job with new settings
            try:
                # Remove existing job
                self.scheduler.remove_job('ai_state_local_job')
                logger.info("Removed existing AI state/local job")
            except Exception as e:
                logger.warning(f"Job didn't exist or couldn't be removed: {e}")

            # Add job with new trigger
            ai_trigger = self._get_ai_scrape_trigger()
            self.scheduler.add_job(
                self._scrape_ai_state_local_opportunities,
                trigger=ai_trigger,
                id='ai_state_local_job',
                name='AI Scrape State & Local Opportunities',
                replace_existing=True
            )

            logger.info(f"AI state/local opportunities job rescheduled with frequency: {self.scheduler_settings['scheduler_frequency']}, locations: {len(self.scheduler_settings['locations'])}")
            return True

        except Exception as e:
            logger.error(f"Failed to reload scheduler settings: {e}")
            return False

    def start(self):
        """Start the scheduler with all configured jobs"""
        logger.info("Starting scheduler service...")

        # Federal grants (Grants.gov) - run daily at 1 AM
        self.scheduler.add_job(
            self._scrape_grants_gov,
            trigger=CronTrigger(hour=1, minute=0),
            id='grants_gov_job',
            name='Scrape Grants.gov',
            replace_existing=True
        )

        # State and local grants (AI-powered) - run based on scheduler_frequency setting
        ai_trigger = self._get_ai_scrape_trigger()
        self.scheduler.add_job(
            self._scrape_ai_state_local_opportunities,
            trigger=ai_trigger,
            id='ai_state_local_job',
            name='AI Scrape State & Local Opportunities',
            replace_existing=True
        )
        logger.info(f"AI state/local opportunities job scheduled with frequency: {self.scheduler_settings['scheduler_frequency']}")

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
        """Run Grants.gov and AI state/local scrapes on startup"""
        logger.info("Running initial scrape on startup...")
        await asyncio.sleep(10)  # Wait for system to fully initialize

        # Run Grants.gov scrape
        try:
            logger.info("[STARTUP] Running Grants.gov scrape...")
            await self._scrape_grants_gov()
            logger.info("[STARTUP] Grants.gov scrape completed")
        except Exception as e:
            logger.error(f"[STARTUP] Grants.gov scrape failed: {e}")

        # Run AI state/local scrape
        try:
            logger.info("[STARTUP] Running AI state/local scrape...")
            await self._scrape_ai_state_local_opportunities()
            logger.info("[STARTUP] AI state/local scrape completed")
        except Exception as e:
            logger.error(f"[STARTUP] AI state/local scrape failed: {e}")

        logger.info("[STARTUP] Initial scrape completed")

    async def _scrape_grants_gov(self):
        """Scrape federal grants from Grants.gov using centralized keywords"""
        job_id = self._create_job_record('grants_gov', 'running')

        try:
            logger.info("Starting Grants.gov multi-keyword scrape...")
            scraper = self.scrapers['grants_gov']

            # Get keywords from centralized configuration
            keywords = get_keywords_for_source('grants_gov')
            logger.info(f"Using {len(keywords)} keywords for Grants.gov search: {keywords}")

            all_grants = []
            for keyword in keywords:
                try:
                    logger.info(f"Searching Grants.gov with keyword: '{keyword}'")
                    grants = await scraper.scrape(keyword, limit=5)
                    all_grants.extend(grants)
                    logger.info(f"Found {len(grants)} opportunities for keyword '{keyword}'")
                except Exception as e:
                    logger.warning(f"Failed to scrape Grants.gov with keyword '{keyword}': {e}")
                    continue

            # Deduplicate by opportunity ID
            unique_grants = self._deduplicate_grants(all_grants, 'id')

            # Store in database
            saved_count = await self._store_grants(unique_grants, 'grants_gov')

            logger.info(f"Grants.gov multi-keyword scrape completed: {saved_count} unique grants saved from {len(all_grants)} total opportunities")
            self._update_job_record(job_id, 'completed', saved_count)

        except Exception as e:
            logger.error(f"Grants.gov scrape failed: {e}")
            self._update_job_record(job_id, 'failed', 0, str(e))

    async def _scrape_sam_gov(self):
        """Scrape procurement opportunities from SAM.gov using multi-keyword search"""
        job_id = self._create_job_record('sam_gov', 'running')

        try:
            logger.info("Starting SAM.gov multi-keyword scrape...")
            scraper = self.scrapers['sam_gov']
            
            # Get keywords for SAM.gov
            keywords = get_keywords_for_source('sam_gov')
            logger.info(f"Using {len(keywords)} keywords for SAM.gov search: {keywords}")
            
            all_grants = []
            
            # Search with each keyword to maximize opportunity discovery
            for keyword in keywords:
                try:
                    logger.info(f"Searching SAM.gov with keyword: '{keyword}'")
                    keyword_grants = await scraper.scrape_with_keyword(keyword, limit=10)
                    all_grants.extend(keyword_grants)
                    logger.info(f"Found {len(keyword_grants)} opportunities for keyword '{keyword}'")
                except Exception as e:
                    logger.warning(f"Failed to scrape SAM.gov with keyword '{keyword}': {e}")
                    continue
            
            # Remove duplicates based on opportunity ID
            unique_grants = {}
            for grant in all_grants:
                if grant.get('opportunity_id'):
                    unique_grants[grant['opportunity_id']] = grant
                elif grant.get('id'):
                    unique_grants[grant['id']] = grant
            
            final_grants = list(unique_grants.values())
            saved_count = await self._store_grants(final_grants, 'sam_gov')

            logger.info(f"SAM.gov multi-keyword scrape completed: {saved_count} unique grants saved from {len(all_grants)} total opportunities")
            self._update_job_record(job_id, 'completed', saved_count)

        except Exception as e:
            logger.error(f"SAM.gov scrape failed: {e}")
            self._update_job_record(job_id, 'failed', 0, str(e))

    async def _scrape_dol_workforce(self):
        """Scrape workforce development opportunities from DOL using multi-keyword search"""
        job_id = self._create_job_record('dol_workforce', 'running')

        try:
            logger.info("Starting DOL Workforce Development multi-keyword scrape...")
            scraper = self.scrapers['dol_workforce']
            
            # Get keywords for DOL
            keywords = get_keywords_for_source('dol')
            logger.info(f"Using {len(keywords)} keywords for DOL search: {keywords}")
            
            all_grants = []
            
            # Search with each keyword to maximize opportunity discovery
            for keyword in keywords:
                try:
                    logger.info(f"Searching DOL with keyword: '{keyword}'")
                    keyword_grants = await scraper.scrape_with_keyword(keyword, limit=10)
                    all_grants.extend(keyword_grants)
                    logger.info(f"Found {len(keyword_grants)} opportunities for keyword '{keyword}'")
                except Exception as e:
                    logger.warning(f"Failed to scrape DOL with keyword '{keyword}': {e}")
                    continue
            
            # Remove duplicates based on opportunity ID
            unique_grants = {}
            for grant in all_grants:
                if grant.get('opportunity_id'):
                    unique_grants[grant['opportunity_id']] = grant
                elif grant.get('id'):
                    unique_grants[grant['id']] = grant
            
            final_grants = list(unique_grants.values())
            saved_count = await self._store_grants(final_grants, 'dol_workforce')

            logger.info(f"DOL Workforce Development multi-keyword scrape completed: {saved_count} unique grants saved from {len(all_grants)} total opportunities")
            self._update_job_record(job_id, 'completed', saved_count)

        except Exception as e:
            logger.error(f"DOL Workforce Development scrape failed: {e}")
            self._update_job_record(job_id, 'failed', 0, str(e))

    async def _scrape_usa_spending(self):
        """Scrape federal spending opportunities from USASpending.gov using multi-keyword search"""
        job_id = self._create_job_record('usa_spending', 'running')

        try:
            logger.info("Starting USASpending.gov multi-keyword scrape...")
            scraper = self.scrapers['usa_spending']
            
            # Get federal keywords for USASpending (historical federal awards)
            keywords = get_keywords_for_source('federal')  # Use federal keywords for federal spending data
            logger.info(f"Using {len(keywords)} keywords for USASpending search: {keywords}")
            
            all_grants = []
            
            # Search with each keyword to maximize opportunity discovery
            for keyword in keywords[:5]:  # Limit to 5 keywords to manage server load
                try:
                    logger.info(f"Searching USASpending with keyword: '{keyword}'")
                    keyword_grants = await scraper.scrape_with_keyword(keyword, limit=8)
                    all_grants.extend(keyword_grants)
                    logger.info(f"Found {len(keyword_grants)} opportunities for keyword '{keyword}'")
                except Exception as e:
                    logger.warning(f"Failed to scrape USASpending with keyword '{keyword}': {e}")
                    continue
            
            # Remove duplicates based on opportunity ID
            unique_grants = {}
            for grant in all_grants:
                if grant.get('opportunity_id'):
                    unique_grants[grant['opportunity_id']] = grant
                elif grant.get('id'):
                    unique_grants[grant['id']] = grant
            
            final_grants = list(unique_grants.values())
            saved_count = await self._store_grants(final_grants, 'usa_spending')

            logger.info(f"USASpending.gov multi-keyword scrape completed: {saved_count} unique grants saved from {len(all_grants)} total opportunities")
            self._update_job_record(job_id, 'completed', saved_count)

        except Exception as e:
            logger.error(f"USASpending scrape failed: {e}")
            self._update_job_record(job_id, 'failed', 0, str(e))


    async def _scrape_ai_state_local_opportunities(self):
        """Search for grant opportunities across all categories - builds general grants database"""
        job_id = self._create_job_record('ai_state_local', 'running')

        try:
            logger.info("Starting AI-powered category-based grants scrape...")

            # Get target locations from scheduler settings (user-configured or defaults)
            locations = self.scheduler_settings.get('locations', self._get_default_locations())
            logger.info(f"Using {len(locations)} target locations from scheduler settings")

            # Get ALL categories - we search for everything to build comprehensive grants DB
            # Pass our supabase client in case the module-level one wasn't initialized
            category_service = get_category_service(self.supabase)
            categories_to_search = category_service.get_all_categories()
            logger.info(f"Searching ALL {len(categories_to_search)} categories: {[c['name'] for c in categories_to_search]}")

            all_grants = []
            total_found = 0

            # Search each location for each category
            for state, city in locations:
                for category in categories_to_search:
                    if not category:
                        continue

                    try:
                        logger.info(f"Searching for {category['name']} opportunities in {state} ({city})...")

                        # Build search request using category service (no org context - general search)
                        orchestration_prompt = category_service.build_orchestration_prompt(
                            category_id=category['id'],
                            location=(state, city),
                            organization_context=None,  # General search, not org-specific
                        )

                        if not orchestration_prompt:
                            logger.warning(f"Could not build prompt for category {category['id']}")
                            continue

                        # Get existing opportunities to avoid duplicates (same as search endpoint)
                        try:
                            existing_result = self.supabase.table("saved_opportunities").select("title, funder").execute()
                            existing_opps = [f"{opp['title']} - {opp['funder']}" for opp in existing_result.data]
                            existing_list = "; ".join(existing_opps) if existing_opps else "None"
                        except:
                            existing_list = "None"

                        # Add JSON format requirements to the orchestration prompt
                        orchestration_prompt += f"""

Existing opportunities to avoid duplicates: {existing_list}

CRITICAL OUTPUT FORMAT - READ CAREFULLY:
You MUST return ONLY raw JSON - NO markdown code blocks, NO explanatory text, NO ```json markers.
Your response should START with {{ and END with }}.

Return JSON with opportunities array. Each opportunity must have all these fields:
- id, title, funder, amount, deadline, description, requirements, contact, application_url
- contact_name, contact_phone, contact_description (or null)
- eligibility_explanation, cost_sharing, cost_sharing_description
- additional_info_url, additional_info_text, archive_date, forecast_date
- close_date_explanation, expected_number_of_awards, award_floor, award_ceiling
- attachments, version, last_updated_date
- geographic_focus: State(s) or region(s) where applicants can operate
- award_type: Type of award (Grant, Cooperative Agreement, Loan, Subsidy, etc.)
- anticipated_awards: Expected number/range of awards
- consortium_required: Boolean
- consortium_description: Consortium/partnership details or null
- rfp_attachment_requirements: Summary of attachment requirements or null

REQUIREMENTS:
- Return ONLY the JSON object (no markdown, no extra text)
- Start with {{ and end with }}
- All string fields use double quotes
- amount, award_floor, award_ceiling are integers (no commas)
- deadline dates in YYYY-MM-DD format
- Use null for optional fields if no data available
- Do NOT include match_score (it will be calculated automatically)"""

                        # Call same Gemini CLI session as search endpoint
                        from main import create_gemini_cli_session, parse_orchestration_response

                        result = create_gemini_cli_session(
                            prompt=orchestration_prompt,
                            session_type="fundraising",
                            timeout=900
                        )

                        if result.get('success'):
                            # Parse same way as search endpoint
                            opportunities = parse_orchestration_response(result.get('output', ''))
                            if opportunities:
                                logger.info(f"Found {len(opportunities)} opportunities in {state}")
                                total_found += len(opportunities)
                                all_grants.extend(opportunities)
                        else:
                            logger.warning(f"AI search failed for {state}: {result.get('error', 'Unknown error')}")

                    except Exception as e:
                        logger.warning(f"Failed to search {state}: {e}")
                        continue

            # Store all found grants
            saved_count = await self._store_grants(all_grants, 'Agent')

            logger.info(f"AI state/local scrape completed: {saved_count} grants saved from {total_found} found across {len(locations)} locations")
            self._update_job_record(job_id, 'completed', saved_count)

        except Exception as e:
            logger.error(f"AI state/local scrape failed: {e}")
            self._update_job_record(job_id, 'failed', 0, str(e))

    async def _scrape_state_grants(self):
        """Scrape state-level grant databases (DISABLED - using AI scraper instead)"""
        job_id = self._create_job_record('state_grants', 'skipped')
        logger.info("State grants scraper disabled - using biweekly AI scraper for state/local opportunities")
        self._update_job_record(job_id, 'skipped', 0, 'Replaced by AI state/local scraper running biweekly')

    async def _scrape_local_grants(self):
        """Scrape city and county grant opportunities (DISABLED - using AI scraper instead)"""
        job_id = self._create_job_record('local_grants', 'skipped')
        logger.info("Local grants scraper disabled - using biweekly AI scraper for state/local opportunities")
        self._update_job_record(job_id, 'skipped', 0, 'Replaced by AI state/local scraper running biweekly')

    async def _scrape_gmail_inbox(self):
        """Scrape grant opportunities from Gmail inbox"""
        job_id = self._create_job_record('gmail_inbox', 'running')

        try:
            logger.info("Starting Gmail inbox scrape...")
            scraper = self.scrapers.get('gmail_inbox')

            if not scraper:
                logger.warning("Gmail scraper not available")
                self._update_job_record(job_id, 'skipped', 0, 'Scraper not initialized')
                return

            # Scrape unread emails (limit to 50 per run to avoid rate limits)
            raw_grants = await scraper.scrape(max_results=50)

            # Deduplicate by email_id
            grants = self._deduplicate_grants(raw_grants, 'email_id')

            # Store grants with proper format
            saved_count = await self._store_gmail_grants(grants)

            logger.info(f"Gmail inbox scrape completed: {saved_count} grants saved from {len(raw_grants)} emails")
            self._update_job_record(job_id, 'completed', saved_count)

        except Exception as e:
            logger.error(f"Gmail inbox scrape failed: {e}")
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

    @staticmethod
    def _sanitize_grant(grant: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize grant data before DB insertion.
        - Empty-string deadlines → None (Postgres rejects '' for timestamptz)
        - Match scores → int (Postgres rejects floats like '32.0' for int columns)
        """
        sanitized = dict(grant)
        # Fix empty-string deadlines
        if not sanitized.get("deadline"):
            sanitized["deadline"] = None
        return sanitized

    async def _store_grants(self, grants: List[Dict[str, Any]], source: str) -> int:
        """Store scraped grants in database"""
        if not grants:
            return 0

        saved_count = 0

        for grant in grants:
            try:
                grant = self._sanitize_grant(grant)
                # Get match score for logging (ensure integer for DB column)
                match_score = int(grant.get("match_score", 0))

                # Check if grant already exists
                existing = self.supabase.table("scraped_grants")\
                    .select("id, match_score")\
                    .eq("opportunity_id", grant.get("id"))\
                    .execute()

                if existing.data:
                    # Update existing grant - skip match score recalculation
                    logger.info(f"Updating existing grant: {grant.get('id')} - skipping match score recalculation")
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
                            "match_score": match_score,
                            "updated_at": datetime.now().isoformat(),
                            "geographic_focus": grant.get("geographic_focus"),
                            "award_type": grant.get("award_type"),
                            "anticipated_awards": grant.get("anticipated_awards"),
                            "consortium_required": grant.get("consortium_required", False),
                            "consortium_description": grant.get("consortium_description"),
                            "rfp_attachment_requirements": grant.get("rfp_attachment_requirements")
                        })\
                        .eq("opportunity_id", grant.get("id"))\
                        .execute()
                else:
                    # Insert new grant - calculate match score only for new grants
                    logger.info(f"New grant found: {grant.get('id')} - calculating match score")
                    match_score = self._calculate_match_score_for_grant(grant)

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
                        "match_score": match_score,
                        "source": source,
                        "status": "active",
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),

                        # UNIVERSAL COMPREHENSIVE FIELDS from grants_service
                        "contact_name": grant.get("contact_name"),
                        "contact_phone": grant.get("contact_phone"),
                        "contact_description": grant.get("contact_description"),
                        "eligibility_explanation": grant.get("eligibility_explanation"),
                        "cost_sharing": grant.get("cost_sharing"),
                        "cost_sharing_description": grant.get("cost_sharing_description"),
                        "additional_info_url": grant.get("additional_info_url"),
                        "additional_info_text": grant.get("additional_info_text"),
                        "archive_date": grant.get("archive_date"),
                        "forecast_date": grant.get("forecast_date"),
                        "close_date_explanation": grant.get("close_date_explanation"),
                        "expected_number_of_awards": grant.get("expected_number_of_awards"),
                        "award_floor": grant.get("award_floor"),
                        "award_ceiling": grant.get("award_ceiling"),
                        "attachments": grant.get("attachments", []),
                        "version": grant.get("version"),
                        "last_updated_date": grant.get("last_updated_date"),

                        # NEW FIELDS FROM AGENT EXTRACTION
                        "geographic_focus": grant.get("geographic_focus"),
                        "award_type": grant.get("award_type"),
                        "anticipated_awards": grant.get("anticipated_awards"),
                        "consortium_required": grant.get("consortium_required", False),
                        "consortium_description": grant.get("consortium_description"),
                        "rfp_attachment_requirements": grant.get("rfp_attachment_requirements")
                    }).execute()

                saved_count += 1

            except Exception as e:
                logger.error(f"Failed to store grant {grant.get('id')}: {e}")
                continue
        
        logger.info(f"{source}: Saved {saved_count} grants to database")
        return saved_count

    async def _store_gmail_grants(self, grants: List[Dict[str, Any]]) -> int:
        """Store Gmail-scraped grants with special handling for email-specific data"""
        if not grants:
            return 0

        saved_count = 0

        for grant in grants:
            try:
                # Use email_id as opportunity_id for Gmail grants
                opportunity_id = grant.get('email_id', f"gmail_{datetime.now().timestamp()}")

                # Check if grant already exists
                existing = self.supabase.table("scraped_grants")\
                    .select("id, match_score")\
                    .eq("opportunity_id", opportunity_id)\
                    .execute()

                # Parse amount - could be string like "$3,000,000" or None
                raw_amount = grant.get("amount")
                parsed_amount = self._parse_amount_string(raw_amount) if raw_amount else None

                grant_data = {
                    "title": grant.get("title"),
                    "funder": grant.get("organization", "Unknown"),
                    "amount": parsed_amount,
                    "deadline": grant.get("deadline"),
                    "description": grant.get("description"),
                    "requirements": grant.get("eligibility", []),
                    "contact": grant.get("email_sender"),
                    "application_url": grant.get("source_url"),
                    "updated_at": datetime.now().isoformat()
                }

                if existing.data:
                    # Update existing grant - skip match score recalculation
                    logger.info(f"Updating existing Gmail grant: {opportunity_id} - skipping match score recalculation")
                    self.supabase.table("scraped_grants")\
                        .update(grant_data)\
                        .eq("opportunity_id", opportunity_id)\
                        .execute()
                else:
                    # Insert new grant - calculate match score only for new grants
                    logger.info(f"New Gmail grant found: {opportunity_id} - calculating match score")

                    # Build grant dict for match scoring
                    grant_for_scoring = {
                        "title": grant.get("title"),
                        "funder": grant.get("organization", "Unknown"),
                        "amount": parsed_amount,
                        "deadline": grant.get("deadline"),
                        "description": grant.get("description"),
                    }

                    # Calculate match score
                    match_score = self._calculate_match_score_for_grant(grant_for_scoring)

                    grant_data.update({
                        "opportunity_id": opportunity_id,
                        "source": "gmail_inbox",
                        "status": "active",
                        "match_score": match_score,
                        "created_at": datetime.now().isoformat()
                    })
                    self.supabase.table("scraped_grants").insert(grant_data).execute()

                saved_count += 1

            except Exception as e:
                logger.error(f"Failed to store Gmail grant: {e}")
                continue

        return saved_count

    def _parse_amount_string(self, amount_str: str) -> int:
        """Parse amount string like '$3,000,000' into integer"""
        import re
        try:
            # Remove $ and commas
            clean = re.sub(r'[^\d.]', '', str(amount_str))
            if clean:
                return int(float(clean))
            return None
        except (ValueError, AttributeError):
            return None

    def _calculate_match_score_for_grant(self, grant: Dict[str, Any]) -> int:
        """Calculate enhanced match score using semantic similarity with historical RFPs"""
        try:
            from match_scoring import calculate_match_score

            # Find similar RFPs using semantic search if available
            rfp_similarities = []
            if self.semantic_service:
                try:
                    grant_text = f"{grant.get('title', '')} {grant.get('description', '')}"
                    rfp_similarities = self.semantic_service.find_similar_rfps(grant_text, limit=3)

                    if rfp_similarities:
                        logger.info(f"[SCHEDULER] Found {len(rfp_similarities)} similar RFPs for '{grant.get('title', 'Unknown')[:50]}...'")
                        for rfp in rfp_similarities:
                            logger.info(f"  - {rfp.get('title', 'Unknown')[:60]}... (similarity: {rfp.get('similarity_score', 0):.2f})")
                except Exception as e:
                    logger.warning(f"Could not find similar RFPs: {e}")

            # Use enhanced scoring with semantic similarity
            enhanced_score = calculate_match_score(grant, rfp_similarities)
            logger.info(f"[SCHEDULER] Enhanced match score for '{grant.get('title', 'Unknown')[:60]}...': {enhanced_score}%")
            return enhanced_score

        except Exception as e:
            logger.error(f"Error calculating enhanced match score: {e}")
            # Fallback to basic keyword matching
            title = grant.get("title", "").lower()
            description = grant.get("description", "").lower()
            combined = f"{title} {description}"

            keywords = ['technology', 'workforce', 'training', 'education', 'stem', 'coding', 'cyber', 'digital']
            matches = sum(1 for kw in keywords if kw in combined)
            return min(70 + (matches * 5), 95)

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
            'dol_workforce': self._scrape_dol_workforce,
            'usa_spending': self._scrape_usa_spending,
            'state_grants': self._scrape_state_grants,
            'local_grants': self._scrape_local_grants,
            'ai_state_local': self._scrape_ai_state_local_opportunities,
            'gmail_inbox': self._scrape_gmail_inbox
        }

        if job_name in job_map:
            logger.info(f"Manually triggering job: {job_name}")
            await job_map[job_name]()
        else:
            raise ValueError(f"Unknown job: {job_name}")

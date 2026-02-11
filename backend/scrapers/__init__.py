"""
Scrapers package for various grant data sources

Includes:
- discovery_agent: Base class for LLM-powered browser scraping
- grants_gov_agent: Grants.gov implementation with self-healing
- grants_gov_scraper: Legacy API-based scraper
- federal_scrapers: Federal grant sources
- state_scrapers: State grant sources
"""

# Import the new discovery agents (graceful fallback if Playwright not installed)
try:
    from .discovery_agent import DiscoveryAgent, ScrapedGrant, CostTracker
    from .grants_gov_agent import GrantsGovAgent, run_grants_gov_discovery
    DISCOVERY_AVAILABLE = True
except ImportError as e:
    DISCOVERY_AVAILABLE = False
    print(f"Discovery agents not available: {e}")
    print("Install with: pip install playwright && playwright install chromium")

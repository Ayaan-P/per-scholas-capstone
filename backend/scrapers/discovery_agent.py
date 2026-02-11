"""
Discovery Agent Base Class

Uses browser automation (Playwright) + LLM vision/reasoning for self-healing grant scraping.
Unlike brittle regex scrapers, this approach adapts to layout changes using visual understanding.

Key Features:
- No hardcoded CSS selectors - finds elements visually via LLM
- Self-healing: adapts when sites change layout
- Structured data extraction with validation
- Graceful error handling (timeouts, rate limits, etc.)
- Cost tracking for LLM token usage
"""

import asyncio
import base64
import json
import os
import time
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

# Playwright imports - graceful handling for missing browser
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    # Playwright not installed at all
    async_playwright = None
    Page = None
    Browser = None
    BrowserContext = None
    PlaywrightTimeout = Exception

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import openai
except ImportError:
    openai = None


@dataclass
class ScrapedGrant:
    """Structured grant data matching scraped_grants schema"""
    opportunity_id: str
    title: str
    funder: str
    source: str
    
    # Optional fields
    agency: Optional[str] = None
    amount_min: Optional[int] = None
    amount_max: Optional[int] = None
    deadline: Optional[str] = None  # YYYY-MM-DD format
    description: Optional[str] = None
    eligibility: Optional[str] = None
    requirements: Optional[List[str]] = None
    application_url: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    posted_date: Optional[str] = None
    geographic_focus: Optional[str] = None
    program_area: Optional[List[str]] = None
    
    # Metadata
    raw_html: Optional[str] = None
    extraction_confidence: float = 0.0
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion"""
        result = {
            'opportunity_id': self.opportunity_id,
            'title': self.title,
            'funder': self.funder,
            'source': self.source,
            'description': self.description,
            'eligibility_explanation': self.eligibility,
            'application_url': self.application_url,
            'contact_name': self.contact_name,
            'contact': self.contact_email,  # Map to existing 'contact' field
            'contact_phone': self.contact_phone,
        }
        
        # Handle amount range
        if self.amount_max:
            result['amount'] = self.amount_max
            result['award_ceiling'] = self.amount_max
        if self.amount_min:
            result['award_floor'] = self.amount_min
            
        # Handle deadline
        if self.deadline:
            result['deadline'] = self.deadline
            
        # Handle requirements as JSONB
        if self.requirements:
            result['requirements'] = json.dumps(self.requirements)
            
        return {k: v for k, v in result.items() if v is not None}


@dataclass 
class CostTracker:
    """Tracks LLM token usage and costs"""
    input_tokens: int = 0
    output_tokens: int = 0
    vision_requests: int = 0
    reasoning_requests: int = 0
    
    # Pricing (per 1M tokens, as of 2024)
    CLAUDE_SONNET_INPUT: float = 3.00  # $3 per 1M input tokens
    CLAUDE_SONNET_OUTPUT: float = 15.00  # $15 per 1M output tokens
    GPT4V_INPUT: float = 10.00  # $10 per 1M input tokens
    GPT4V_OUTPUT: float = 30.00  # $30 per 1M output tokens
    
    def add_usage(self, input_tokens: int, output_tokens: int, is_vision: bool = False):
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        if is_vision:
            self.vision_requests += 1
        else:
            self.reasoning_requests += 1
    
    def get_cost_estimate(self, model: str = "claude") -> float:
        """Estimate cost in USD"""
        if "claude" in model.lower():
            input_cost = (self.input_tokens / 1_000_000) * self.CLAUDE_SONNET_INPUT
            output_cost = (self.output_tokens / 1_000_000) * self.CLAUDE_SONNET_OUTPUT
        else:  # GPT-4V
            input_cost = (self.input_tokens / 1_000_000) * self.GPT4V_INPUT
            output_cost = (self.output_tokens / 1_000_000) * self.GPT4V_OUTPUT
        return input_cost + output_cost
    
    def summary(self) -> Dict[str, Any]:
        return {
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'total_tokens': self.input_tokens + self.output_tokens,
            'vision_requests': self.vision_requests,
            'reasoning_requests': self.reasoning_requests,
            'estimated_cost_usd': round(self.get_cost_estimate(), 4)
        }


class DiscoveryAgent(ABC):
    """
    Base class for browser-based discovery agents.
    
    Uses LLM vision to understand page layout and extract data without
    relying on brittle CSS selectors. When sites change, the agent adapts
    by re-analyzing the visual structure.
    """
    
    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        headless: bool = True,
        rate_limit_delay: float = 2.0,
        max_retries: int = 3,
        timeout_ms: int = 30000,
        supabase_client=None
    ):
        self.model = model
        self.headless = headless
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.timeout_ms = timeout_ms
        self.supabase = supabase_client
        
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        self.cost_tracker = CostTracker()
        self.grants_discovered: List[ScrapedGrant] = []
        self.errors: List[Dict[str, Any]] = []
        
        # Initialize LLM client
        self._init_llm_client()
    
    def _init_llm_client(self):
        """Initialize the appropriate LLM client"""
        if "claude" in self.model.lower():
            if anthropic is None:
                raise ImportError("anthropic package required for Claude models")
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY environment variable required")
            self.llm_client = anthropic.Anthropic(api_key=api_key)
            self.llm_type = "claude"
        else:
            if openai is None:
                raise ImportError("openai package required for GPT models")
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable required")
            self.llm_client = openai.OpenAI(api_key=api_key)
            self.llm_type = "openai"
    
    async def start_browser(self):
        """Launch browser with appropriate settings"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright not installed. Run: pip install playwright && playwright install chromium")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        self.page = await self.context.new_page()
        
        # Set default timeout
        self.page.set_default_timeout(self.timeout_ms)
        
        print(f"[{self.source_name}] Browser started (headless={self.headless})")
    
    async def stop_browser(self):
        """Clean up browser resources"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.context = None
            self.page = None
            print(f"[{self.source_name}] Browser stopped")
    
    async def take_screenshot(self, name: str = "screenshot") -> bytes:
        """Take a screenshot and return as bytes"""
        if not self.page:
            raise RuntimeError("Browser not started")
        return await self.page.screenshot(full_page=True)
    
    async def get_page_text(self) -> str:
        """Extract visible text content from page"""
        if not self.page:
            raise RuntimeError("Browser not started")
        return await self.page.inner_text('body')
    
    async def analyze_with_vision(
        self, 
        screenshot: bytes, 
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Send screenshot to LLM for visual analysis.
        This is the core of self-healing - the LLM understands the layout visually.
        """
        image_base64 = base64.b64encode(screenshot).decode('utf-8')
        
        if self.llm_type == "claude":
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
            
            response = self.llm_client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt or "You are a web scraping assistant that extracts structured data from screenshots.",
                messages=messages
            )
            
            # Track usage
            self.cost_tracker.add_usage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                is_vision=True
            )
            
            return response.content[0].text
        else:
            # OpenAI GPT-4V
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}",
                                "detail": "high"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
            
            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})
            
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=4096
            )
            
            # Track usage (approximate for vision)
            self.cost_tracker.add_usage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                is_vision=True
            )
            
            return response.choices[0].message.content
    
    async def reason_about_text(self, text: str, prompt: str) -> str:
        """Use LLM to reason about text content (no vision needed)"""
        if self.llm_type == "claude":
            response = self.llm_client.messages.create(
                model=self.model,
                max_tokens=4096,
                messages=[{"role": "user", "content": f"{prompt}\n\nText:\n{text}"}]
            )
            
            self.cost_tracker.add_usage(
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                is_vision=False
            )
            
            return response.content[0].text
        else:
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": f"{prompt}\n\nText:\n{text}"}],
                max_tokens=4096
            )
            
            self.cost_tracker.add_usage(
                input_tokens=response.usage.prompt_tokens,
                output_tokens=response.usage.completion_tokens,
                is_vision=False
            )
            
            return response.choices[0].message.content
    
    async def find_element_visually(
        self, 
        description: str,
        screenshot: Optional[bytes] = None
    ) -> Optional[str]:
        """
        Use LLM vision to find an element by description.
        Returns CSS selector or aria label to click.
        
        This is the self-healing mechanism - instead of hardcoded selectors,
        we describe what we're looking for and let the LLM find it.
        """
        if screenshot is None:
            screenshot = await self.take_screenshot()
        
        prompt = f"""Look at this webpage screenshot. I need to find: {description}

Analyze the page and provide the best way to locate this element. 
Return a JSON object with:
{{
    "found": true/false,
    "selector_type": "css" | "text" | "aria" | "xpath",
    "selector": "the selector string",
    "confidence": 0.0-1.0,
    "reasoning": "why you chose this selector"
}}

Be specific about the selector. For text selectors, provide the exact visible text.
For CSS selectors, prefer stable attributes like data-*, name, aria-label over dynamic classes."""

        response = await self.analyze_with_vision(screenshot, prompt)
        
        try:
            # Extract JSON from response
            json_match = response[response.find('{'):response.rfind('}')+1]
            result = json.loads(json_match)
            
            if result.get('found') and result.get('confidence', 0) > 0.5:
                return result
            return None
        except (json.JSONDecodeError, ValueError):
            print(f"[{self.source_name}] Could not parse element location response")
            return None
    
    async def click_element(self, element_info: Dict[str, Any]) -> bool:
        """Click an element based on visual analysis results"""
        if not self.page or not element_info:
            return False
        
        selector_type = element_info.get('selector_type')
        selector = element_info.get('selector')
        
        try:
            if selector_type == 'text':
                await self.page.click(f"text={selector}")
            elif selector_type == 'css':
                await self.page.click(selector)
            elif selector_type == 'aria':
                await self.page.click(f"[aria-label='{selector}']")
            elif selector_type == 'xpath':
                await self.page.click(f"xpath={selector}")
            else:
                return False
            
            return True
        except Exception as e:
            print(f"[{self.source_name}] Click failed: {e}")
            return False
    
    async def wait_and_retry(self, delay: float = None):
        """Wait with rate limiting"""
        await asyncio.sleep(delay or self.rate_limit_delay)
    
    def log_error(self, error_type: str, message: str, context: Dict[str, Any] = None):
        """Log an error with context"""
        error = {
            'timestamp': datetime.now().isoformat(),
            'type': error_type,
            'message': message,
            'context': context or {}
        }
        self.errors.append(error)
        print(f"[{self.source_name}] ERROR ({error_type}): {message}")
    
    async def save_grant(self, grant: ScrapedGrant) -> bool:
        """Save a scraped grant to the database"""
        self.grants_discovered.append(grant)
        
        if self.supabase:
            try:
                db_dict = grant.to_db_dict()
                db_dict['created_at'] = datetime.now().isoformat()
                db_dict['updated_at'] = datetime.now().isoformat()
                db_dict['status'] = 'active'
                
                # Upsert based on opportunity_id
                result = self.supabase.table('scraped_grants').upsert(
                    db_dict,
                    on_conflict='opportunity_id'
                ).execute()
                
                print(f"[{self.source_name}] Saved grant: {grant.title[:60]}...")
                return True
            except Exception as e:
                self.log_error('database', f"Failed to save grant: {e}", {'grant_id': grant.opportunity_id})
                return False
        else:
            print(f"[{self.source_name}] No database client - grant stored in memory only")
            return True
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the source identifier for this agent"""
        pass
    
    @property
    @abstractmethod
    def base_url(self) -> str:
        """Return the base URL for this source"""
        pass
    
    @abstractmethod
    async def discover(self, **kwargs) -> List[ScrapedGrant]:
        """
        Main discovery method - implementations should:
        1. Navigate to the source
        2. Search for relevant grants
        3. Extract structured data
        4. Return list of ScrapedGrant objects
        """
        pass
    
    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the discovery process with full lifecycle management.
        Returns a summary including discovered grants and costs.
        """
        start_time = time.time()
        
        try:
            await self.start_browser()
            grants = await self.discover(**kwargs)
            
            # Save all grants
            saved_count = 0
            for grant in grants:
                if await self.save_grant(grant):
                    saved_count += 1
            
            elapsed = time.time() - start_time
            
            return {
                'success': True,
                'source': self.source_name,
                'grants_found': len(grants),
                'grants_saved': saved_count,
                'elapsed_seconds': round(elapsed, 2),
                'cost_analysis': self.cost_tracker.summary(),
                'errors': self.errors,
                'grants': [asdict(g) for g in grants]
            }
            
        except Exception as e:
            self.log_error('fatal', str(e))
            return {
                'success': False,
                'source': self.source_name,
                'grants_found': 0,
                'grants_saved': 0,
                'elapsed_seconds': time.time() - start_time,
                'cost_analysis': self.cost_tracker.summary(),
                'errors': self.errors
            }
        finally:
            await self.stop_browser()

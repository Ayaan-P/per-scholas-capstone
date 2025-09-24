# Claude Code Integration as Intelligent Backend

## Architecture Overview

### Core Concept
Claude Code serves as an intelligent backend service that executes complex fundraising workflows dynamically. Instead of traditional REST endpoints, we have an intelligent agent that can reason about fundraising tasks and execute them using available tools.

### Integration Pattern: "Smart Cache + Intelligent Processing"
```
Web Request → API Gateway → Cache Check → [Hit: Serve Data] or [Miss: Claude Code Agent] → Results → Database → Frontend
```

#### Decision Logic:
- **Serve from cache/DB**: Recent searches, existing proposals, static data
- **Use Claude Code**: New discovery requests, complex analysis, fresh proposal generation

### Smart Routing System

```python
class IntelligentRouter:
    def __init__(self, cache_service, db_service, claude_service):
        self.cache = cache_service
        self.db = db_service
        self.claude = claude_service

    async def handle_opportunity_search(self, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Smart routing for opportunity discovery"""

        # Generate cache key from search criteria
        cache_key = self._generate_cache_key("opportunities", criteria)

        # Check if we have fresh data (< 24 hours old)
        cached_result = await self.cache.get(cache_key)
        if cached_result and not self._is_stale(cached_result, hours=24):
            return {
                "data": cached_result["opportunities"],
                "source": "cache",
                "timestamp": cached_result["timestamp"]
            }

        # Check database for similar recent searches
        similar_searches = await self.db.find_similar_searches(criteria, days=7)
        if similar_searches:
            return {
                "data": similar_searches["opportunities"],
                "source": "database",
                "note": "Similar search from past week"
            }

        # No cached data - use Claude Code for fresh discovery
        job_id = await self.claude.execute_workflow("opportunity_discovery", criteria)
        return {
            "job_id": job_id,
            "source": "claude_code",
            "status": "processing"
        }

    async def handle_proposal_generation(self, rfp_data: Dict[str, Any]) -> Dict[str, Any]:
        """Smart routing for proposal generation"""

        # Check if we already have a proposal for this RFP
        existing_proposal = await self.db.get_proposal_by_rfp_id(rfp_data.get("rfp_id"))
        if existing_proposal:
            return {
                "data": existing_proposal,
                "source": "database",
                "note": "Existing proposal found"
            }

        # Check for similar RFPs with existing proposals
        similar_proposals = await self.db.find_similar_rfps(rfp_data)
        if similar_proposals:
            return {
                "data": similar_proposals,
                "source": "database",
                "note": "Similar proposals available for reference"
            }

        # Generate new proposal using Claude Code
        job_id = await self.claude.execute_workflow("proposal_generation", rfp_data)
        return {
            "job_id": job_id,
            "source": "claude_code",
            "status": "generating"
        }

    async def handle_pipeline_analysis(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Smart routing for pipeline analysis"""

        # Pipeline data changes frequently, but analysis can be cached for short periods
        cache_key = f"pipeline_analysis_{params.get('user_id', 'default')}"
        cached_analysis = await self.cache.get(cache_key)

        if cached_analysis and not self._is_stale(cached_analysis, hours=4):
            return {
                "data": cached_analysis["analysis"],
                "source": "cache",
                "timestamp": cached_analysis["timestamp"]
            }

        # Generate fresh analysis
        job_id = await self.claude.execute_workflow("pipeline_analysis", params)
        return {
            "job_id": job_id,
            "source": "claude_code",
            "status": "analyzing"
        }

    def _is_stale(self, cached_data: Dict[str, Any], hours: int) -> bool:
        """Check if cached data is older than specified hours"""
        from datetime import datetime, timedelta
        timestamp = datetime.fromisoformat(cached_data["timestamp"])
        return datetime.now() - timestamp > timedelta(hours=hours)
```

### Caching Strategy

#### What to Cache:
- **Opportunity searches**: 24-48 hour cache (funding landscapes change slowly)
- **Proposal drafts**: Permanent storage with versioning
- **RFP analysis**: 7-day cache (requirements don't change during application period)
- **Pipeline analytics**: 4-hour cache (balance between freshness and performance)

#### What NOT to Cache:
- Real-time deadline alerts
- Custom analysis requests
- User-specific recommendations
- Live competitive intelligence

## Claude Code Service Architecture

### 1. Service Wrapper
A Python service that manages Claude Code instances and executes fundraising workflows.

```python
# claude_service.py
import asyncio
import subprocess
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class WorkflowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class WorkflowJob:
    job_id: str
    workflow_type: str
    parameters: Dict[str, Any]
    status: WorkflowStatus
    progress: int = 0
    current_task: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

class ClaudeCodeService:
    def __init__(self):
        self.active_jobs: Dict[str, WorkflowJob] = {}
        self.job_queue = asyncio.Queue()

    async def execute_workflow(self, workflow_type: str, parameters: Dict[str, Any]) -> str:
        """Execute a fundraising workflow using Claude Code"""
        job_id = self._generate_job_id()

        job = WorkflowJob(
            job_id=job_id,
            workflow_type=workflow_type,
            parameters=parameters,
            status=WorkflowStatus.PENDING
        )

        self.active_jobs[job_id] = job
        await self.job_queue.put(job)

        return job_id

    async def _process_job_queue(self):
        """Background worker to process Claude Code jobs"""
        while True:
            job = await self.job_queue.get()
            await self._execute_claude_code_workflow(job)

    async def _execute_claude_code_workflow(self, job: WorkflowJob):
        """Execute specific workflow using Claude Code"""
        try:
            job.status = WorkflowStatus.RUNNING

            # Generate the Claude Code prompt based on workflow type
            prompt = self._generate_workflow_prompt(job.workflow_type, job.parameters)

            # Execute Claude Code with the generated prompt
            result = await self._run_claude_code(prompt, job)

            job.result = result
            job.status = WorkflowStatus.COMPLETED
            job.progress = 100

        except Exception as e:
            job.status = WorkflowStatus.FAILED
            job.error = str(e)

    def _generate_workflow_prompt(self, workflow_type: str, parameters: Dict[str, Any]) -> str:
        """Generate Claude Code prompt for specific workflow"""

        if workflow_type == "opportunity_discovery":
            return f"""
            You are a fundraising agent for Per Scholas, a nonprofit providing tuition-free IT training.

            Task: Find funding opportunities matching these criteria:
            - Focus areas: {parameters.get('focus_areas', ['IT training', 'workforce development'])}
            - Amount range: ${parameters.get('min_amount', 10000)} - ${parameters.get('max_amount', 500000)}
            - Deadline: Within {parameters.get('days_until_deadline', 90)} days
            - Geographic focus: {parameters.get('locations', ['Chicago', 'New York'])}

            Execute this workflow:
            1. Search GRANTS.gov for relevant federal opportunities
            2. Check foundation databases (Ford, Gates, etc.)
            3. Analyze each opportunity for semantic match to Per Scholas mission
            4. Score opportunities by fit (1-100), feasibility, and timeline
            5. Generate summary with top 10 opportunities
            6. Store results in database with confidence scores

            Per Scholas Mission Context:
            - Enhances economic mobility through tuition-free IT training
            - Serves diverse backgrounds, particularly underrepresented communities
            - Programs: Software Engineering, Cloud Computing, Data Engineering, Cybersecurity
            - Locations: Chicago, New York, Dallas, Atlanta, and expanding
            - Annual budget: ~$50M, serves 3000+ learners annually

            Output format: JSON with opportunities array containing:
            - title, funder, amount, deadline, description
            - match_score (1-100), confidence_level, reasoning
            - application_requirements, contact_info
            - next_steps for application
            """

        elif workflow_type == "proposal_generation":
            return f"""
            You are a grant writing agent for Per Scholas.

            Task: Generate a proposal draft for this opportunity:
            RFP Document: {parameters.get('rfp_text', '')}
            RFP URL: {parameters.get('rfp_url', '')}
            Target Programs: {parameters.get('programs', [])}
            Target Locations: {parameters.get('locations', [])}

            Execute this workflow:
            1. Analyze the RFP requirements and scoring criteria
            2. Retrieve relevant Per Scholas organizational information
            3. Research similar successful proposals from our database
            4. Generate comprehensive proposal sections:
               - Executive Summary
               - Project Description
               - Implementation Plan
               - Budget and Budget Narrative
               - Evaluation Plan
               - Organizational Capacity
            5. Include specific data about Per Scholas outcomes and impact
            6. Ensure alignment with funder priorities
            7. Flag any missing information or areas needing customization

            Per Scholas Organizational Data:
            - Founded 1999, 501(c)(3) nonprofit
            - 85% job placement rate within 12 months
            - Average salary increase: $30K+ for graduates
            - Partnerships with 500+ employer partners
            - Diverse learner population: 50% Black, 30% Latinx, 65% women
            - Proven model with national expansion capability

            Output format: Structured proposal document with:
            - Each section clearly marked
            - Confidence score for each section
            - Areas requiring human review/customization
            - Compliance checklist for RFP requirements
            """

        elif workflow_type == "pipeline_analysis":
            return f"""
            You are a fundraising analytics agent for Per Scholas.

            Task: Analyze current funding pipeline and provide strategic recommendations.

            Execute this workflow:
            1. Query database for all opportunities in pipeline
            2. Analyze deadlines and priority levels
            3. Calculate probability scores based on historical data
            4. Identify resource allocation needs
            5. Flag urgent actions required
            6. Generate weekly priority recommendations
            7. Suggest pipeline optimization strategies

            Analysis Parameters:
            - Current date: {parameters.get('current_date')}
            - Team capacity: {parameters.get('team_capacity', 3)} FTE
            - Monthly funding target: ${parameters.get('monthly_target', 200000)}

            Output format: Pipeline analysis with:
            - Executive summary of pipeline health
            - Urgent actions (next 7 days)
            - High-priority opportunities requiring attention
            - Resource allocation recommendations
            - Success probability forecasts
            """

        return prompt

    async def _run_claude_code(self, prompt: str, job: WorkflowJob) -> Dict[str, Any]:
        """Execute Claude Code with the given prompt"""
        # Create temporary prompt file
        prompt_file = f"/tmp/claude_prompt_{job.job_id}.txt"
        with open(prompt_file, 'w') as f:
            f.write(prompt)

        # Update job progress
        job.current_task = "Initializing Claude Code agent..."
        job.progress = 10

        # Execute Claude Code
        process = await asyncio.create_subprocess_exec(
            'claude-code',
            '--file', prompt_file,
            '--json-output',  # Hypothetical flag for JSON output
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        # Monitor progress (simplified - would need actual progress tracking)
        job.current_task = "Agent analyzing requirements..."
        job.progress = 30

        await asyncio.sleep(2)  # Simulated processing time
        job.current_task = "Searching funding databases..."
        job.progress = 60

        await asyncio.sleep(3)
        job.current_task = "Generating results..."
        job.progress = 90

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise Exception(f"Claude Code execution failed: {stderr.decode()}")

        # Parse Claude Code output
        result = json.loads(stdout.decode())
        return result
```

### 2. Workflow Definitions

#### Opportunity Discovery Workflow
```python
class OpportunityDiscoveryWorkflow:
    """Intelligent funding opportunity discovery using Claude Code"""

    @staticmethod
    def generate_search_strategy(criteria: Dict[str, Any]) -> str:
        """Generate intelligent search strategy based on criteria"""
        return f"""
        Search Strategy for Per Scholas Funding Opportunities:

        1. Federal Sources:
           - GRANTS.gov keyword search: {criteria['keywords']}
           - Department of Labor workforce development grants
           - Department of Education IT/digital literacy programs
           - NSF broadening participation initiatives

        2. Foundation Sources:
           - Ford Foundation (economic mobility focus)
           - Gates Foundation (postsecondary success)
           - JPMorgan Chase Foundation (workforce development)
           - Google.org (digital skills initiatives)

        3. Corporate Sources:
           - Tech company CSR programs
           - Financial services diversity initiatives
           - Workforce development partnerships

        4. Semantic Analysis Criteria:
           - Mission alignment with economic mobility
           - IT/tech training relevance
           - Diversity, equity, inclusion focus
           - Workforce development impact
           - Adult learner population fit

        5. Qualification Filters:
           - Geographic eligibility: {criteria['locations']}
           - Funding amount: ${criteria['min_amount']}-${criteria['max_amount']}
           - Application deadline: Within {criteria['days']} days
           - Organizational capacity requirements
        """

#### Proposal Generation Workflow
```python
class ProposalGenerationWorkflow:
    """Intelligent proposal drafting using organizational knowledge"""

    @staticmethod
    def generate_proposal_framework(rfp_analysis: Dict[str, Any]) -> str:
        """Generate proposal framework based on RFP analysis"""
        return f"""
        Proposal Generation Framework:

        RFP Analysis Results:
        - Funder: {rfp_analysis['funder']}
        - Focus Area: {rfp_analysis['focus_area']}
        - Key Requirements: {rfp_analysis['requirements']}
        - Scoring Criteria: {rfp_analysis['scoring_criteria']}

        Per Scholas Response Strategy:
        1. Executive Summary:
           - Lead with impact statistics (85% job placement rate)
           - Emphasize economic mobility mission alignment
           - Highlight diversity outcomes and community focus

        2. Project Description:
           - Map Per Scholas programs to RFP objectives
           - Integrate proven curriculum and industry partnerships
           - Emphasize evidence-based model and scalability

        3. Implementation Plan:
           - Leverage existing infrastructure and partnerships
           - Detail recruitment from target communities
           - Include wraparound services and support systems

        4. Budget Strategy:
           - Cost-effective model (lower per-participant cost)
           - Sustainability planning beyond grant period
           - Leverage matching funds and in-kind contributions

        5. Evaluation Plan:
           - Employment outcomes and salary increases
           - Participant satisfaction and retention
           - Long-term career progression tracking
        """

### 3. API Gateway Integration

```python
# api_gateway.py
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.websockets import WebSocket
import asyncio
import json

app = FastAPI()
claude_service = ClaudeCodeService()

@app.post("/api/workflows/opportunity-discovery")
async def start_opportunity_discovery(criteria: OpportunityDiscoveryCriteria):
    """Start intelligent opportunity discovery workflow"""
    job_id = await claude_service.execute_workflow(
        workflow_type="opportunity_discovery",
        parameters=criteria.dict()
    )
    return {"job_id": job_id, "status": "started"}

@app.post("/api/workflows/proposal-generation")
async def start_proposal_generation(request: ProposalGenerationRequest):
    """Start intelligent proposal generation workflow"""
    job_id = await claude_service.execute_workflow(
        workflow_type="proposal_generation",
        parameters=request.dict()
    )
    return {"job_id": job_id, "status": "started"}

@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """Real-time updates for workflow progress"""
    await websocket.accept()

    while True:
        job = claude_service.active_jobs.get(job_id)
        if not job:
            await websocket.send_text(json.dumps({"error": "Job not found"}))
            break

        status_update = {
            "status": job.status.value,
            "progress": job.progress,
            "current_task": job.current_task
        }

        await websocket.send_text(json.dumps(status_update))

        if job.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]:
            break

        await asyncio.sleep(1)

@app.get("/api/jobs/{job_id}/result")
async def get_job_result(job_id: str):
    """Get workflow execution result"""
    job = claude_service.active_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job_id,
        "status": job.status.value,
        "result": job.result,
        "error": job.error
    }
```

## Key Innovation: Dynamic Workflow Execution

### Traditional Approach vs. Intelligent Agent Approach

**Traditional Fundraising API:**
```
GET /api/grants?keyword=IT&amount=100000
POST /api/proposals/generate {template_id: 5, data: {...}}
```

**Intelligent Agent Approach:**
```
POST /api/workflows/opportunity-discovery {
  "user_intent": "Find grants for cybersecurity training in underserved communities",
  "context": "Per Scholas expanding to new markets",
  "constraints": "Must be federal funding, $200K minimum"
}
```

The agent then:
1. Interprets the complex request
2. Develops a search strategy
3. Executes multiple searches across different sources
4. Applies semantic analysis for relevance
5. Contextualizes results for Per Scholas specifically
6. Provides actionable next steps

## Integration Benefits

### 1. Adaptive Intelligence
- Handles complex, nuanced requests that traditional APIs cannot
- Learns from Per Scholas' specific context and history
- Adapts search strategies based on success patterns

### 2. Workflow Automation
- Executes complete end-to-end fundraising workflows
- Handles error cases and edge scenarios intelligently
- Provides human-readable explanations for all decisions

### 3. Scalability
- No need to hardcode every possible fundraising scenario
- Can handle new types of opportunities without code changes
- Evolves capabilities through prompt engineering

### 4. User Experience
- Users interact with natural language intents
- Complex backend operations hidden behind simple UI actions
- Real-time progress updates for long-running workflows

## Deployment Considerations

### 1. Resource Management
- Claude Code instances are stateless and can be containerized
- Queue-based processing prevents resource contention
- Horizontal scaling through multiple service instances

### 2. Security
- Isolated execution environments for each workflow
- Secure handling of sensitive Per Scholas data
- Audit trails for all agent actions

### 3. Monitoring
- Real-time workflow monitoring and alerting
- Performance metrics for different workflow types
- Error tracking and automated recovery

This architecture transforms Claude Code from a CLI tool into a powerful backend service that provides intelligent, context-aware fundraising capabilities that traditional APIs simply cannot match.
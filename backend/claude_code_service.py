"""
Claude API Service for PerScholas Fundraising
Uses the Anthropic Python SDK with OAuth token from CLAUDE_CREDENTIALS
"""

import os
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime
import anthropic

# Per Scholas organizational context
PER_SCHOLAS_CONTEXT = """
Per Scholas is a leading national nonprofit that advances economic equity through rigorous,
tuition-free technology training for individuals from underrepresented communities.

Mission: To advance economic equity by providing access to technology careers for individuals
from underrepresented communities.

Programs:
- Cybersecurity Training (16-week intensive program)
- Cloud Computing (AWS/Azure certification tracks)
- Software Development (Full-stack development)
- IT Support (CompTIA certification preparation)

Impact:
- 20,000+ graduates to date
- 85% job placement rate
- 150% average salary increase
- 24 markets across the United States
- Focus on underrepresented minorities, women, veterans

Target Demographics:
- Individuals from underrepresented communities
- Women seeking technology careers
- Veterans transitioning to civilian workforce
- Career changers from declining industries
- Low-income individuals seeking economic mobility
"""


def get_claude_client() -> Optional[anthropic.Anthropic]:
    """
    Get an Anthropic client using OAuth credentials from environment.
    
    Supports two formats:
    1. CLAUDE_CREDENTIALS as JSON with full OAuth structure
    2. CLAUDE_ACCESS_TOKEN as direct token string
    
    Returns:
        anthropic.Anthropic client or None if credentials unavailable
    """
    # Try CLAUDE_CREDENTIALS JSON format first
    credentials_json = os.getenv('CLAUDE_CREDENTIALS')
    if credentials_json:
        try:
            credentials = json.loads(credentials_json)
            oauth_data = credentials.get('claudeAiOauth', {})
            access_token = oauth_data.get('accessToken')
            expires_at = oauth_data.get('expiresAt', 0)
            
            # Check if token is expired (expires_at is in milliseconds)
            if expires_at and expires_at < (time.time() * 1000):
                print("[Claude API] Warning: Access token may be expired")
                # Continue anyway - Anthropic might handle refresh
            
            if access_token:
                print(f"[Claude API] Using OAuth token from CLAUDE_CREDENTIALS")
                return anthropic.Anthropic(api_key=access_token)
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[Claude API] Error parsing CLAUDE_CREDENTIALS: {e}")
    
    # Fallback to CLAUDE_ACCESS_TOKEN
    access_token = os.getenv('CLAUDE_ACCESS_TOKEN')
    if access_token:
        print(f"[Claude API] Using token from CLAUDE_ACCESS_TOKEN")
        return anthropic.Anthropic(api_key=access_token)
    
    # Last resort: try ANTHROPIC_API_KEY
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if api_key:
        print(f"[Claude API] Using ANTHROPIC_API_KEY")
        return anthropic.Anthropic(api_key=api_key)
    
    print("[Claude API] No valid credentials found")
    return None


def generate_proposal_content(
    opportunity_title: str,
    funder: str,
    amount: int,
    deadline: str,
    description: str,
    requirements: list,
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Generate a grant proposal using Claude API.
    
    Args:
        opportunity_title: Title of the grant opportunity
        funder: Name of the funding organization
        amount: Requested funding amount
        deadline: Application deadline
        description: Opportunity description
        requirements: List of requirements
        timeout: API timeout in seconds
    
    Returns:
        Dict with 'success', 'content', and optionally 'error'
    """
    client = get_claude_client()
    
    if not client:
        return {
            'success': False,
            'content': None,
            'error': 'Claude API credentials not configured. Set CLAUDE_CREDENTIALS or CLAUDE_ACCESS_TOKEN.'
        }
    
    # Build the proposal generation prompt
    prompt = f"""You are an expert grant writer for Per Scholas, a leading national nonprofit that advances economic equity through technology training.

Organization Context:
{PER_SCHOLAS_CONTEXT}

Grant Opportunity Details:
- Title: {opportunity_title}
- Funder: {funder}
- Amount Requested: ${amount:,}
- Deadline: {deadline}
- Description: {description}
- Requirements: {', '.join(requirements) if requirements else 'Not specified'}

Please generate a complete, professional grant proposal with the following sections:

1. **Executive Summary** (compelling 1-paragraph overview)
2. **Organization Background** (Per Scholas history, mission, track record)
3. **Project Description and Goals** (what this grant will fund, SMART goals)
4. **Target Population and Need Assessment** (who we serve, the problem we solve)
5. **Implementation Plan and Timeline** (phases, milestones, 12-24 month timeline)
6. **Budget Justification** (how funds will be allocated with percentages)
7. **Expected Outcomes and Evaluation** (metrics, measurement methods)
8. **Sustainability Plan** (how program continues after grant period)
9. **Conclusion** (compelling close, call to action)

The proposal should:
- Be data-driven with specific impact metrics
- Align with {funder}'s priorities and requirements
- Demonstrate Per Scholas's proven track record
- Be compelling, professional, and ready for submission
- Include specific numbers and measurable outcomes

Write the complete proposal now:"""

    try:
        print(f"[Claude API] Generating proposal for '{opportunity_title[:50]}...'")
        start_time = time.time()
        
        # Call Claude API with claude-sonnet-4-20250514 (good balance of quality and speed)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        elapsed = time.time() - start_time
        print(f"[Claude API] Proposal generated in {elapsed:.1f}s")
        
        # Extract content from response
        content = ""
        for block in response.content:
            if hasattr(block, 'text'):
                content += block.text
        
        if not content:
            return {
                'success': False,
                'content': None,
                'error': 'Claude API returned empty response'
            }
        
        print(f"[Claude API] Generated {len(content)} chars of proposal content")
        
        return {
            'success': True,
            'content': content,
            'error': None,
            'model': response.model,
            'usage': {
                'input_tokens': response.usage.input_tokens,
                'output_tokens': response.usage.output_tokens
            }
        }
        
    except anthropic.AuthenticationError as e:
        print(f"[Claude API] Authentication error: {e}")
        return {
            'success': False,
            'content': None,
            'error': f'Authentication failed. Token may be expired or invalid: {str(e)}'
        }
    except anthropic.RateLimitError as e:
        print(f"[Claude API] Rate limit error: {e}")
        return {
            'success': False,
            'content': None,
            'error': f'Rate limit exceeded: {str(e)}'
        }
    except anthropic.APIError as e:
        print(f"[Claude API] API error: {e}")
        return {
            'success': False,
            'content': None,
            'error': f'Claude API error: {str(e)}'
        }
    except Exception as e:
        print(f"[Claude API] Unexpected error: {e}")
        return {
            'success': False,
            'content': None,
            'error': f'Unexpected error: {str(e)}'
        }


def create_claude_api_session(prompt: str, session_type: str = "fundraising", timeout: int = 300) -> Dict[str, Any]:
    """
    Create a Claude API session (compatible interface with create_gemini_cli_session).
    
    This function provides a drop-in replacement for create_gemini_cli_session,
    using the Claude API instead of subprocess CLI calls.
    
    Args:
        prompt: The prompt to send to Claude
        session_type: Type of session (for logging)
        timeout: Timeout in seconds (used for API timeout)
    
    Returns:
        Dict with 'success', 'output', 'error', and 'session_type'
    """
    client = get_claude_client()
    
    if not client:
        return {
            'success': False,
            'output': '',
            'error': 'Claude API credentials not configured',
            'session_type': session_type
        }
    
    try:
        print(f"[Claude API Session] Starting {session_type} session...")
        print(f"[Claude API Session] Prompt length: {len(prompt)} chars")
        start_time = time.time()
        
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8000,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        elapsed = time.time() - start_time
        
        # Extract content from response
        output = ""
        for block in response.content:
            if hasattr(block, 'text'):
                output += block.text
        
        print(f"[Claude API Session] Completed in {elapsed:.1f}s")
        print(f"[Claude API Session] Output length: {len(output)} chars")
        
        return {
            'success': True,
            'output': output,
            'error': None,
            'session_type': session_type
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"[Claude API Session] FAILED - Error: {error_msg}")
        return {
            'success': False,
            'output': '',
            'error': error_msg,
            'session_type': session_type
        }


# Export functions for use in proposals.py
__all__ = ['generate_proposal_content', 'create_claude_api_session', 'get_claude_client', 'PER_SCHOLAS_CONTEXT']

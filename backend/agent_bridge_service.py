"""
Agent Bridge Service — Routes chat to Clawdbot agents on Hetzner.

Each organization gets their own persistent FundFish agent with:
- Isolated workspace
- Conversation memory
- Tool access (grants API, proposals, etc.)
"""

import os
import logging
import aiohttp
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AgentBridgeService:
    """Routes messages to FundFish agents on Hetzner"""
    
    def __init__(self):
        self.bridge_url = os.environ.get(
            'AGENT_BRIDGE_URL',
            'http://46.225.82.130:9090'
        )
        self.bridge_token = os.environ.get(
            'AGENT_BRIDGE_TOKEN',
            'dytto-agent-token-v1'
        )
        logger.info(f"AgentBridgeService initialized. Bridge: {self.bridge_url}")

    async def send_message(
        self,
        org_id: str,
        message: str,
        org_name: Optional[str] = None,
        org_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a message to the org's FundFish agent.
        
        Auto-provisions on first message if agent doesn't exist.
        Uses agent_type: "fundfish" for proper routing.
        """
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.bridge_token}'
                }

                payload = {
                    'message': message,
                    'user_id': org_id,
                    'agent_type': 'fundfish',  # Routes to FundFish templates
                }
                
                # Include context for auto-provisioning
                if org_name:
                    payload['user_name'] = org_name
                if org_context:
                    payload['user_context'] = org_context

                async with session.post(
                    f'{self.bridge_url}/chat',
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        reply = data.get('reply')
                        no_response = data.get('no_response', False)
                        agent_id = data.get('agent_id', 'unknown')
                        
                        if not reply or no_response:
                            logger.info(f"Agent {agent_id} had no reply for org {org_id}")
                            return {
                                "response": None,
                                "agent_id": agent_id,
                                "no_response": True
                            }
                        
                        logger.info(f"Agent {agent_id} reply for org {org_id}: {len(reply)} chars")
                        return {
                            "response": reply,
                            "agent_id": agent_id
                        }
                    else:
                        error_text = await resp.text()
                        logger.error(f"Agent error for org {org_id}: {resp.status} — {error_text}")
                        raise Exception(f"Agent returned {resp.status}")

        except Exception as e:
            logger.error(f"Agent bridge failed for org {org_id}: {e}")
            raise


# Singleton
_agent_bridge: Optional[AgentBridgeService] = None


def get_agent_bridge() -> AgentBridgeService:
    """Get or create agent bridge singleton"""
    global _agent_bridge
    if _agent_bridge is None:
        _agent_bridge = AgentBridgeService()
    return _agent_bridge

"""
Workflow API client for handling AI Bot Service integration.
Manages command sending, streaming response handling, and session lifecycle.
"""

import aiohttp
import asyncio
import json
import discord
from typing import Callable, Optional, Dict, Any, AsyncIterator
from config_loader import Config
from core.workflow_views import WorkflowStreamView


class WorkflowAPIClient:
    """Handles communication with the Workflow API."""
    
    def __init__(self):
        self.base_url = Config.WORKFLOW_API_BASE_URL
        self.active_sessions: Dict[str, WorkflowStreamView] = {}  # session_id -> view
    
    async def start_new_request(
        self, 
        user_query: str, 
        guild_id: str,
        memory_user_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Send a new request to the Workflow API and return the session_id.
        Raises exception if the API call fails.
        """
        url = f"{self.base_url}/api/workflow/commands"
        payload = {
            "type": "new_request",
            "user_query": user_query,
            "guild_id": guild_id
        }
        if memory_user_id:
            payload["memory_user_id"] = memory_user_id
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        session_id = data.get("session_id")
                        return session_id
                    else:
                        raise Exception(f"API returned status {resp.status}")
            except Exception as e:
                raise Exception(f"Failed to start workflow request: {e}")
    
    async def send_input_response(
        self,
        session_id: str,
        request_id: str,
        approved: Optional[bool] = None,
        value: Optional[str] = None
    ) -> bool:
        """
        Send an input response to the Workflow API.
        """
        url = f"{self.base_url}/api/workflow/commands"
        payload = {
            "type": "input",
            "session_id": session_id,
            "request_id": request_id
        }
        if approved is not None:
            payload["approved"] = approved
        if value is not None:
            payload["value"] = value
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload) as resp:
                    return resp.status == 200
            except Exception as e:
                print(f"Failed to send input response: {e}")
                return False
    
    async def stream_session_output(
        self,
        session_id: str,
        on_event: Callable[[Dict[str, Any]], None]
    ) -> bool:
        """
        Stream and process events from the session's output stream (SSE format).
        Calls on_event callback for each event received.
        Returns True if stream completed successfully.
        """
        url = f"{self.base_url}/api/workflow/sessions/{session_id}/stream"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=None)) as resp:
                    if resp.status != 200:
                        raise Exception(f"Stream returned status {resp.status}")
                    
                    # Read the stream line by line (SSE format)
                    event_data = {}
                    
                    async for line in resp.content:
                        # Decode line and strip
                        line_str = line.decode('utf-8', errors='ignore').rstrip()
                        
                        if not line_str:  # Empty line signals end of event
                            if event_data and 'data' in event_data:
                                try:
                                    # Parse the data field as JSON
                                    event_obj = json.loads(event_data['data'])
                                    on_event(event_obj)
                                except json.JSONDecodeError as e:
                                    print(f"Failed to parse event JSON: {e}")
                                event_data = {}
                        elif line_str.startswith('event: '):
                            event_data['event'] = line_str[7:]
                        elif line_str.startswith('data: '):
                            event_data['data'] = line_str[6:]
                        elif line_str.startswith('id: '):
                            event_data['id'] = line_str[4:]
                    
                    return True
        except asyncio.TimeoutError:
            raise Exception("Stream timeout")
        except Exception as e:
            raise Exception(f"Stream error: {e}")
    
    def store_session(self, session_id: str, view: WorkflowStreamView):
        """Store a session view for later reference."""
        self.active_sessions[session_id] = view
    
    def get_session(self, session_id: str) -> Optional[WorkflowStreamView]:
        """Retrieve a stored session view."""
        return self.active_sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """Remove a session from active tracking."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]


# Global instance
workflow_client = WorkflowAPIClient()

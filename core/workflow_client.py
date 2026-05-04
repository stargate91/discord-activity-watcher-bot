"""
Workflow API client for handling AI Bot Service integration.
Manages command sending, streaming response handling, and session lifecycle.
"""

import aiohttp
import asyncio
import json
import discord
from typing import Callable, Optional, Dict, Any
from config_loader import Config
from core.logger import log
from core.workflow_views import WorkflowStreamView


def _truncate_for_log(value: Any, limit: int = 4000) -> Any:
    """Keep workflow logs readable without dropping structure."""
    if isinstance(value, str):
        if len(value) <= limit:
            return value
        return f"{value[:limit]}... [truncated {len(value) - limit} chars]"
    if isinstance(value, dict):
        return {str(k): _truncate_for_log(v, limit) for k, v in value.items()}
    if isinstance(value, list):
        return [_truncate_for_log(item, limit) for item in value]
    return value


def _format_for_log(value: Any) -> str:
    """Serialize workflow payloads safely for the logger."""
    try:
        return json.dumps(_truncate_for_log(value), ensure_ascii=False)
    except Exception:
        return repr(value)


def _extract_text_payload(value: Any) -> Optional[str]:
    """Pull the most likely markdown/text payload out of a response body."""
    if isinstance(value, str):
        text = value.strip()
        return text or None

    if isinstance(value, list):
        for item in value:
            extracted = _extract_text_payload(item)
            if extracted:
                return extracted
        return None

    if isinstance(value, dict):
        priority_keys = (
            "markdown",
            "summary",
            "content",
            "text",
            "message",
            "result",
            "response",
            "data",
        )
        for key in priority_keys:
            if key in value:
                extracted = _extract_text_payload(value.get(key))
                if extracted:
                    return extracted

        for item in value.values():
            extracted = _extract_text_payload(item)
            if extracted:
                return extracted

    return None


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

        log.info(
            f"WorkflowAPIClient: start_new_request -> POST {url} payload={_format_for_log(payload)}"
        )
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload) as resp:
                    response_text = await resp.text()
                    log.info(
                        f"WorkflowAPIClient: start_new_request <- status={resp.status} "
                        f"body={_format_for_log(response_text)}"
                    )
                    if resp.status == 200:
                        data = json.loads(response_text) if response_text else {}
                        session_id = data.get("session_id")
                        log.info(
                            f"WorkflowAPIClient: start_new_request session_id={session_id}"
                        )
                        return session_id
                    else:
                        raise Exception(f"API returned status {resp.status}")
            except Exception as e:
                log.error(
                    f"WorkflowAPIClient: start_new_request failed payload={_format_for_log(payload)} error={e}",
                    exc_info=True
                )
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

        log.info(
            f"WorkflowAPIClient: send_input_response -> POST {url} payload={_format_for_log(payload)}"
        )
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload) as resp:
                    response_text = await resp.text()
                    log.info(
                        f"WorkflowAPIClient: send_input_response <- status={resp.status} "
                        f"body={_format_for_log(response_text)}"
                    )
                    return resp.status == 200
            except Exception as e:
                log.error(
                    f"WorkflowAPIClient: send_input_response failed payload={_format_for_log(payload)} error={e}",
                    exc_info=True
                )
                return False

    async def fetch_daily_summary(
        self,
        guild_id: Optional[str] = None,
        hours: Optional[int] = None,
        message_limit: Optional[int] = None,
    ) -> str:
        """
        Fetch the rendered daily summary markdown from the Workflow API.
        Supports plain text/markdown responses and simple JSON wrappers.
        """
        url = f"{self.base_url}/api/daily/summary"
        payload = {}
        if guild_id:
            payload["guild_id"] = guild_id
        if hours is not None:
            payload["hours"] = hours
        if message_limit is not None:
            payload["message_limit"] = message_limit

        headers = {
            "Accept": "application/json, text/markdown, text/plain"
        }
        timeout = aiohttp.ClientTimeout(total=60)

        log.info(
            f"WorkflowAPIClient: fetch_daily_summary start url={url} "
            f"payload={_format_for_log(payload)}"
        )

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            try:
                log.info(
                    f"WorkflowAPIClient: fetch_daily_summary -> POST {url} "
                    f"params={_format_for_log(payload)}"
                )
                async with session.post(url, params=payload) as resp:
                    response_text = await resp.text()
                    content_type = (resp.headers.get("Content-Type") or "").lower()
                    log.info(
                        f"WorkflowAPIClient: fetch_daily_summary <- method=POST "
                        f"status={resp.status} content_type={content_type or None} "
                        f"body={_format_for_log(response_text)}"
                    )

                    if resp.status != 200:
                        raise Exception(f"API returned status {resp.status} for POST")

                    summary_text: Optional[str] = None
                    if "application/json" in content_type:
                        try:
                            summary_text = _extract_text_payload(
                                json.loads(response_text) if response_text else {}
                            )
                        except json.JSONDecodeError as exc:
                            raise Exception(f"Invalid JSON in daily summary response: {exc}")
                    else:
                        summary_text = response_text.strip()

                    if not summary_text:
                        raise Exception("Daily summary response was empty")

                    return summary_text
            except Exception as e:
                log.error(
                    f"WorkflowAPIClient: fetch_daily_summary failed "
                    f"params={_format_for_log(payload)} error={e}",
                    exc_info=True
                )
                raise Exception(f"Failed to fetch daily summary: {e}")

    async def fetch_daily_recommendation(
        self,
        guild_id: Optional[str] = None,
        hours: Optional[int] = None,
        message_limit: Optional[int] = None,
    ) -> str:
        """
        Fetch the rendered daily summary markdown from the Workflow API.
        Supports plain text/markdown responses and simple JSON wrappers.
        """
        url = f"{self.base_url}/api/daily/summary_recommendations"
        payload = {}
        if guild_id:
            payload["guild_id"] = guild_id
        if hours is not None:
            payload["hours"] = hours
        if message_limit is not None:
            payload["message_limit"] = message_limit

        headers = {
            "Accept": "application/json, text/markdown, text/plain"
        }
        timeout = aiohttp.ClientTimeout(total=60)

        log.info(
            f"WorkflowAPIClient: fetch_daily_summary_recommendation start url={url} "
            f"payload={_format_for_log(payload)}"
        )

        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            try:
                log.info(
                    f"WorkflowAPIClient: fetch_daily_summary_recommendation -> POST {url} "
                    f"params={_format_for_log(payload)}"
                )
                async with session.post(url, params=payload) as resp:
                    response_text = await resp.text()
                    content_type = (resp.headers.get("Content-Type") or "").lower()
                    log.info(
                        f"WorkflowAPIClient: fetch_daily_summary_recommendation <- method=POST "
                        f"status={resp.status} content_type={content_type or None} "
                        f"body={_format_for_log(response_text)}"
                    )

                    if resp.status != 200:
                        raise Exception(f"API returned status {resp.status} for POST")

                    summary_text: Optional[str] = None
                    if "application/json" in content_type:
                        try:
                            summary_text = _extract_text_payload(
                                json.loads(response_text) if response_text else {}
                            )
                        except json.JSONDecodeError as exc:
                            raise Exception(f"Invalid JSON in daily summary response: {exc}")
                    else:
                        summary_text = response_text.strip()

                    if not summary_text:
                        raise Exception("Daily summary recommendation response was empty")

                    return summary_text
            except Exception as e:
                log.error(
                    f"WorkflowAPIClient: fetch_daily_summary_recommendation failed "
                    f"params={_format_for_log(payload)} error={e}",
                    exc_info=True
                )
                raise Exception(f"Failed to fetch daily summary: {e}")
      
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
        log.info(
            f"WorkflowAPIClient: stream_session_output -> GET {url} session_id={session_id} "
            f"base_url={self.base_url} configured_base_url={Config.WORKFLOW_API_BASE_URL}"
        )
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=None)) as resp:
                    response_headers = {
                        "content_type": resp.headers.get("Content-Type"),
                        "content_length": resp.headers.get("Content-Length"),
                        "transfer_encoding": resp.headers.get("Transfer-Encoding"),
                        "connection": resp.headers.get("Connection"),
                        "cache_control": resp.headers.get("Cache-Control"),
                    }
                    log.info(
                        f"WorkflowAPIClient: stream_session_output connected session_id={session_id} "
                        f"status={resp.status} real_url={resp.real_url} headers={_format_for_log(response_headers)}"
                    )

                    if str(resp.real_url) != url:
                        log.warning(
                            f"WorkflowAPIClient: stream_session_output redirected session_id={session_id} "
                            f"expected_url={url} real_url={resp.real_url}"
                        )

                    content_type = (resp.headers.get("Content-Type") or "").lower()
                    if "text/event-stream" not in content_type:
                        log.warning(
                            f"WorkflowAPIClient: stream_session_output unexpected content-type "
                            f"session_id={session_id} content_type={content_type or None}"
                        )

                    if resp.status != 200:
                        raise Exception(f"Stream returned status {resp.status}")
                    
                    # Read the stream line by line (SSE format)
                    event_data = {"data": []}
                    raw_line_count = 0
                    blank_line_count = 0
                    data_line_count = 0
                    event_count = 0

                    def has_pending_event_data() -> bool:
                        return bool(
                            event_data.get("data")
                            or event_data.get("event")
                            or event_data.get("id")
                        )

                    def try_emit_pending_event(source: str) -> None:
                        nonlocal event_data, event_count

                        if not event_data.get("data"):
                            if has_pending_event_data():
                                log.info(
                                    f"WorkflowAPIClient: pending stream event without data "
                                    f"session_id={session_id} source={source} "
                                    f"event={event_data.get('event')} id={event_data.get('id')}"
                                )
                            event_data = {"data": []}
                            return

                        raw_data = "\n".join(event_data["data"])
                        try:
                            event_obj = json.loads(raw_data)
                            event_count += 1
                            log.info(
                                f"WorkflowAPIClient: stream_event session_id={session_id} "
                                f"source={source} event={event_data.get('event')} id={event_data.get('id')} "
                                f"payload={_format_for_log(event_obj)}"
                            )
                            on_event(event_obj)
                        except json.JSONDecodeError as e:
                            log.error(
                                f"WorkflowAPIClient: failed to parse stream event session_id={session_id} "
                                f"source={source} event={event_data.get('event')} id={event_data.get('id')} "
                                f"raw={_format_for_log(raw_data)} error={e}"
                            )
                        finally:
                            event_data = {"data": []}
                    
                    async for line in resp.content:
                        # Decode line and strip
                        line_str = line.decode('utf-8', errors='ignore').rstrip()
                        raw_line_count += 1
                        log.info(
                            f"WorkflowAPIClient: stream_line session_id={session_id} "
                            f"line_no={raw_line_count} raw={_format_for_log(line_str)}"
                        )
                        
                        if not line_str:  # Empty line signals end of event
                            blank_line_count += 1
                            try_emit_pending_event(source="blank_line")
                        elif line_str.startswith('event: '):
                            if has_pending_event_data():
                                log.warning(
                                    f"WorkflowAPIClient: new event line arrived before blank-line terminator "
                                    f"session_id={session_id} previous_event={event_data.get('event')} "
                                    f"previous_id={event_data.get('id')}"
                                )
                                try_emit_pending_event(source="next_event_line")
                            event_data['event'] = line_str[7:]
                            log.info(
                                f"WorkflowAPIClient: stream_field session_id={session_id} "
                                f"field=event value={_format_for_log(event_data['event'])}"
                            )
                        elif line_str.startswith('data: '):
                            data_line_count += 1
                            event_data.setdefault("data", []).append(line_str[6:])
                            log.info(
                                f"WorkflowAPIClient: stream_field session_id={session_id} "
                                f"field=data chunk={_format_for_log(line_str[6:])}"
                            )
                        elif line_str.startswith('id: '):
                            event_data['id'] = line_str[4:]
                            log.info(
                                f"WorkflowAPIClient: stream_field session_id={session_id} "
                                f"field=id value={_format_for_log(event_data['id'])}"
                            )
                        else:
                            log.info(
                                f"WorkflowAPIClient: stream_line non_sse session_id={session_id} "
                                f"line_no={raw_line_count} raw={_format_for_log(line_str)}"
                            )

                    if has_pending_event_data():
                        try_emit_pending_event(source="eof")

                    log.info(
                        f"WorkflowAPIClient: stream_session_output eof session_id={session_id} "
                        f"raw_lines={raw_line_count} blank_lines={blank_line_count} "
                        f"data_lines={data_line_count} parsed_events={event_count}"
                    )

                    if raw_line_count == 0:
                        log.warning(
                            f"WorkflowAPIClient: stream_session_output ended without any bytes "
                            f"session_id={session_id} real_url={resp.real_url}"
                        )
                    elif event_count == 0:
                        log.warning(
                            f"WorkflowAPIClient: stream_session_output ended without parsed events "
                            f"session_id={session_id} raw_lines={raw_line_count} real_url={resp.real_url}"
                        )

                    log.info(
                        f"WorkflowAPIClient: stream_session_output completed session_id={session_id}"
                    )
                    
                    return True
        except asyncio.TimeoutError:
            log.error(f"WorkflowAPIClient: stream_session_output timeout session_id={session_id}")
            raise Exception("Stream timeout")
        except Exception as e:
            log.error(
                f"WorkflowAPIClient: stream_session_output failed session_id={session_id} error={e}",
                exc_info=True
            )
            raise Exception(f"Stream error: {e}")
    
    def store_session(self, session_id: str, view: WorkflowStreamView):
        """Store a session view for later reference."""
        self.active_sessions[session_id] = view
        log.info(f"WorkflowAPIClient: stored active session session_id={session_id}")
    
    def get_session(self, session_id: str) -> Optional[WorkflowStreamView]:
        """Retrieve a stored session view."""
        return self.active_sessions.get(session_id)
    
    def remove_session(self, session_id: str):
        """Remove a session from active tracking."""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
            log.info(f"WorkflowAPIClient: removed active session session_id={session_id}")


# Global instance
workflow_client = WorkflowAPIClient()

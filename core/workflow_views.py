"""
Workflow API streaming view components for the AI Bot integration.
Handles real-time streaming output, input requests, and session state.
"""

import discord
import json
import os
import asyncio
from typing import Optional, List, Dict, Any, Callable
from discord.ui import LayoutView, Container, Section, TextDisplay, Separator, ActionRow, Button
from config_loader import Config
from core.logger import log


class WorkflowStreamView(discord.ui.LayoutView):
    """Manages the streaming output from the Workflow API in a real-time editable embed."""
    
    def __init__(self, guild: discord.Guild, session_id: str):
        super().__init__()
        self.guild = guild
        self.session_id = session_id
        self.is_closed = False
        self.output_text = ""
        self.input_state = "hidden"
        self.input_request: Optional[Dict[str, Any]] = None
        self.input_prompt_text: Optional[str] = None
        self.input_button_row: Optional[discord.ui.ActionRow] = None
        self.message: Optional[discord.Message] = None
        self.session_status = "initializing"
        self.user_query = ""
        self.close_reason: Optional[str] = None
        
        # Build initial container
        self._build_container()

    def has_input_ui(self) -> bool:
        """Return whether the approval button row is currently visible."""
        return self.input_state == "awaiting_response" and self.input_button_row is not None

    def has_input_section(self) -> bool:
        """Return whether any input-related UI should be rendered."""
        return self.input_state != "hidden"

    def _hide_input_section(self):
        """Clear any input-related UI from the view."""
        self.input_state = "hidden"
        self.input_request = None
        self.input_prompt_text = None
        self.input_button_row = None
    
    def _build_container(self):
        """Build the main container with current state."""
        container = discord.ui.Container(accent_color=discord.Color(Config.COLOR_PRIMARY))
        
        # Header with session info
        container.add_item(discord.ui.TextDisplay(
            f"# 🤖 AI Workflow Session\n`Session ID: {self.session_id}`"
        ))
        container.add_item(discord.ui.Separator())
        
        # Session started info (will be updated)
        session_text = f"**Status:** {self.session_status}"
        if self.user_query:
            session_text += f"\n**Query:** {self.user_query}"
        container.add_item(discord.ui.TextDisplay(f"## Session Info\n{session_text}"))
        
        container.add_item(discord.ui.Separator())
        
        # Output section
        if self.output_text:
            # Truncate if too long for Discord
            output_display = self.output_text[-2000:] if len(self.output_text) > 2000 else self.output_text
            container.add_item(discord.ui.TextDisplay(f"## Output\n{output_display}"))
        else:
            container.add_item(discord.ui.TextDisplay("*(Waiting for output...)*"))
        
        # Input section (will be added if needed)
        if self.has_input_section():
            container.add_item(discord.ui.Separator())
            if self.input_prompt_text:
                container.add_item(discord.ui.TextDisplay(self.input_prompt_text))
            if self.has_input_ui():
                container.add_item(self.input_button_row)
        
        # Status footer
        if self.is_closed:
            container.add_item(discord.ui.Separator())
            footer_text = "🔴 **AI Session Closed**"
            if self.close_reason:
                footer_text += f"\n{self.close_reason}"
            else:
                footer_text += "\nThe workflow has completed."
            container.add_item(discord.ui.TextDisplay(
                footer_text
            ))
        
        self.clear_items()
        self.add_item(container)
    
    def set_session_started(self, status: str, user_query: str):
        """Update the view when session starts."""
        self.session_status = status
        self.user_query = user_query
    
    def add_output_text(self, text: str):
        """Append text to the output section (streaming update)."""
        self.output_text += text
    
    def set_input_request(self, request_data: Dict[str, Any]):
        """Create an input selection interface with yes/no buttons."""
        self._hide_input_section()
        self.input_request = request_data
        
        # Build input section
        debug_mode = os.getenv("DISABLE_DEBUG_AI", "0") == "0"
        
        prompt = request_data.get("prompt", "User input required")
        input_kind = request_data.get("input_kind", "text")
        
        input_text = f"## ❓ Input Needed\n**Type:** {input_kind}\n**Prompt:** {prompt}"
        
        # Show metadata and options only in debug mode
        if debug_mode:
            metadata = request_data.get("metadata", {})
            options = request_data.get("options", [])
            
            if metadata:
                input_text += f"\n\n**Metadata:**\n```json\n{json.dumps(metadata, indent=2, ensure_ascii=False)}\n```"
            
            if options:
                input_text += f"\n\n**Options:**\n"
                for opt in options:
                    opt_str = opt.get("value", opt.get("label", "?"))
                    input_text += f"• {opt_str}\n"
        
        self.input_prompt_text = input_text
        
        # Create button row for yes/no
        button_row = discord.ui.ActionRow()
        
        btn_yes = WorkflowInputButton(
            label="✅ Yes",
            style=discord.ButtonStyle.success,
            custom_id=f"workflow_input:{self.session_id}:yes",
            session_id=self.session_id,
            request_id=request_data.get("request_id"),
            value="yes"
        )
        btn_no = WorkflowInputButton(
            label="❌ No",
            style=discord.ButtonStyle.danger,
            custom_id=f"workflow_input:{self.session_id}:no",
            session_id=self.session_id,
            request_id=request_data.get("request_id"),
            value="no"
        )
        
        button_row.add_item(btn_yes)
        button_row.add_item(btn_no)
        
        self.input_state = "awaiting_response"
        self.input_button_row = button_row
        log.info(
            f"WorkflowStreamView: input UI shown session_id={self.session_id} "
            f"request_id={request_data.get('request_id')} input_kind={input_kind}"
        )

    def mark_input_sent(self):
        """Replace the input buttons with a waiting state after a response was sent."""
        self.input_request = None
        self.input_state = "response_sent"
        self.input_prompt_text = "## ⏳ Input Sent\nWaiting for the workflow to continue..."
        self.input_button_row = None
        log.info(f"WorkflowStreamView: input UI hidden after send session_id={self.session_id}")
    
    def close_session(self, reason: Optional[str] = "Connection closed to AI Bot Service", status: str = "closed"):
        """Mark the session as closed."""
        self.session_status = status
        self.is_closed = True
        self._hide_input_section()
        self.close_reason = reason
        if reason:
            self.add_output_text(f"\n\n---\n**Closed:** {reason}")
        log.info(
            f"WorkflowStreamView: session closed session_id={self.session_id} "
            f"status={status} reason={reason}"
        )
    
    async def update_message(self):
        """Rebuild and update the Discord message."""
        if self.message:
            self._build_container()
            try:
                await self.message.edit(view=self)
                log.info(
                    f"WorkflowStreamView: updated message session_id={self.session_id} "
                    f"message_id={self.message.id} output_len={len(self.output_text)} closed={self.is_closed}"
                )
            except discord.HTTPException as e:
                log.error(
                    f"WorkflowStreamView: failed to update message session_id={self.session_id} "
                    f"message_id={self.message.id if self.message else None} error={e}",
                    exc_info=True
                )


class WorkflowInputButton(discord.ui.Button):
    """Button for handling workflow input responses."""
    
    def __init__(self, *args, session_id: str, request_id: str, value: str, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_id = session_id
        self.request_id = request_id
        self.value = value
    
    async def callback(self, interaction: discord.Interaction):
        """Handle the button click and send input response to API."""
        from core.workflow_client import workflow_client
        
        try:
            await interaction.response.defer(ephemeral=True)
            log.info(
                f"WorkflowInputButton: clicked session_id={self.session_id} "
                f"request_id={self.request_id} value={self.value} user_id={interaction.user.id}"
            )
            
            # Send the input response
            approved = self.value == "yes"
            success = await workflow_client.send_input_response(
                session_id=self.session_id,
                request_id=self.request_id,
                approved=approved
            )
            
            if success:
                log.info(
                    f"WorkflowInputButton: input response sent session_id={self.session_id} "
                    f"request_id={self.request_id} approved={approved}"
                )
                await interaction.followup.send(
                    f"✅ Response sent: {self.label}",
                    ephemeral=True
                )
            else:
                log.warning(
                    f"WorkflowInputButton: input response failed session_id={self.session_id} "
                    f"request_id={self.request_id} approved={approved}"
                )
                await interaction.followup.send(
                    f"❌ Failed to send response",
                    ephemeral=True
                )
        except Exception as e:
            log.error(
                f"WorkflowInputButton: callback error session_id={self.session_id} "
                f"request_id={self.request_id} error={e}",
                exc_info=True
            )
            await interaction.followup.send(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )

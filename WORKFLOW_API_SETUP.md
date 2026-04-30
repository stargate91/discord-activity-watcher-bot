# AI Workflow Integration - Setup & Usage Guide

## Overview

The Discord Activity Watcher Bot now integrates with an AI Workflow API service running on HTTP port 8000. This allows administrators to submit tasks to an AI service and receive real-time streaming output directly in Discord.

## Installation

### 1. Install Required Dependencies

Run the following command to install the new HTTP client library:

```bash
pip install aiohttp
```

Or if you're updating your environment:

```bash
pip install -r requirements.txt
```

### 2. Configure the API Endpoint

Edit `config.json` and ensure the workflow section is present:

```json
{
  "workflow": {
    "api_base_url": "http://localhost:8000"
  }
}
```

Change `http://localhost:8000` to your actual API server URL if it's running elsewhere.

### 3. Start the Bot

The bot will automatically load the AI Admin cog with the new `/ai_admin` command.

## Usage

### Command: `/ai_admin`

**Access Level:** Admin role required (or guild administrator)  
**Channel:** Must be executed in the admin channel (configured in `config.json`)

**Flow:**
1. User executes `/ai_admin`
2. A modal appears requesting the AI task query
3. User enters their request (10-500 characters)
4. The bot sends the request to the Workflow API and creates a streaming view
5. Real-time output from the AI service appears in the Discord message
6. If the API requests user input, the bot detects whether it is a Yes/No approval or a text response and shows the matching UI

### Example Query

```
Analyze the gaming preferences of our top 10 members and suggest community events
```

## API Integration

### Supported Event Types

The bot handles the following event types from the Workflow API:

| Event Type | Description |
|-----------|-------------|
| `session_started` | Session initialized with status and query |
| `output` | Text output from the AI service |
| `input_needed` | API requests approval or another user response (buttons or text modal) |
| `cancelled` | Session cancelled by the API |
| `error` | An error occurred during processing |
| `completed` | Session completed normally |

### Event Examples

#### Session Started
```json
{
  "type": "session_started",
  "status": "running",
  "user_query": "Your request...",
  "guild_id": "123456789"
}
```

#### Text Output
```json
{
  "type": "output",
  "text": "Processing data... 🔄\n"
}
```

#### Input Needed
```json
{
  "type": "input_needed",
  "request_id": "req_123",
  "input_kind": "approval",
  "prompt": "Continue with analysis?",
  "metadata": {},
  "options": [],
  "allow_free_text": false
}
```

#### Text Input Needed
```json
{
  "type": "input_needed",
  "request_id": "req_456",
  "input_kind": "text",
  "prompt": "Which playlist should I use?",
  "metadata": {},
  "options": [],
  "allow_free_text": true
}
```

## Architecture

### Components

1. **AdminCog** (`cogs/admin.py`)
   - Provides `/ai_admin` slash command
   - Handles modal submission
   - Manages streaming view updates

2. **WorkflowAPIClient** (`core/workflow_client.py`)
   - HTTP communication with the Workflow API
   - Sends new requests and input responses
   - Handles SSE (Server-Sent Events) streaming

3. **WorkflowStreamView** (`core/workflow_views.py`)
   - Displays streaming output in a Discord embed
   - Manages UI state (session info, output, approval buttons, text response modal)
   - Handles user interactions for both boolean confirmations and text input

## Debug Mode

Set the environment variable to show/hide debug information:

```bash
# Debug mode enabled (show metadata and options)
DISABLE_DEBUG_AI=0

# Debug mode disabled (hide debug details)
DISABLE_DEBUG_AI=1
```

In debug mode, input request metadata and available options are displayed in the Discord message.

## Error Handling

If the API is unreachable or returns an error:
- An error message is sent to the user
- The view shows the session as closed with the error reason
- The bot logs the error for troubleshooting

## Limitations

- Maximum output text displayed: 2000 characters (Discord embed limit)
- Stream timeout: No limit (configurable via `aiohttp.ClientTimeout`)
- Sessions must complete within a reasonable timeframe
- Unicode and emoji content is fully supported in output

## Troubleshooting

### "Failed to get session_id from API"
- Ensure the Workflow API is running and accessible at the configured URL
- Check that the API endpoint `/api/workflow/commands` accepts POST requests

### Stream not updating
- The bot uses asyncio tasks in the background to stream output
- Very large responses may take time to appear
- Check bot permissions in the channel

### Input controls not working
- Ensure the response controls are visible in the Discord message
- For text input, click the response button and submit the modal
- User must click within the 15-minute interaction timeout window
- Check bot logs for detailed error messages

---

**Last Updated:** April 2026

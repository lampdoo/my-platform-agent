# Basic Platform-Hosted Agent

A simple FastAPI chat agent for WSO2 Agent Manager.

## Endpoint

POST /chat

## Request

```json
{
  "message": "Hello",
  "session_id": "session-1",
  "context": {}
}

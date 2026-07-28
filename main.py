import os
import traceback
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel, Field


app = FastAPI(
    title="MCP-Enabled Platform-Hosted Agent",
    version="1.5.0",
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    response: str


def get_mcp_urls() -> list[str]:
    raw_urls = os.environ.get(
        "SIMPLE_TEST_MCP_URL",
        "",
    )

    return [
        url.strip()
        for url in raw_urls.split(",")
        if url.strip()
    ]


def get_mcp_api_key() -> str:
    return os.environ.get(
        "SIMPLE_TEST_MCP_API_KEY",
        "",
    ).strip()


def create_mcp_client() -> MultiServerMCPClient:
    mcp_urls = get_mcp_urls()
    mcp_api_key = get_mcp_api_key()

    if not mcp_urls:
        raise RuntimeError(
            "SIMPLE_TEST_MCP_URL is not configured"
        )

    if not mcp_api_key:
        raise RuntimeError(
            "SIMPLE_TEST_MCP_API_KEY is not configured"
        )

    server_configs: dict[str, dict[str, Any]] = {
        f"mcp_server_{index}": {
            "url": url,
            "transport": "streamable_http",
            "headers": {
                "X-API-Key": mcp_api_key,
                "Authorization": "",
            },
        }
        for index, url in enumerate(mcp_urls)
    }

    return MultiServerMCPClient(server_configs)


async def load_mcp_tools() -> list[Any]:
    client = create_mcp_client()
    return await client.get_tools()


async def call_mcp_tool(
    tool_name: str,
    arguments: dict[str, Any],
) -> Any:
    tools = await load_mcp_tools()

    selected_tool = next(
        (
            tool
            for tool in tools
            if tool.name == tool_name
        ),
        None,
    )

    if selected_tool is None:
        available_tools = [
            tool.name
            for tool in tools
        ]

        raise RuntimeError(
            f"MCP tool '{tool_name}' was not found. "
            f"Available tools: {available_tools}"
        )

    return await selected_tool.ainvoke(arguments)


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "status": "Agent is running",
        "version": "1.5.0",
        "mcp_url_configured": bool(get_mcp_urls()),
        "mcp_api_key_configured": bool(get_mcp_api_key()),
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "healthy",
    }


@app.get("/mcp/config")
def mcp_config() -> dict[str, Any]:
    """
    Confirms that WSO2 injected the MCP configuration.
    The actual API key is never returned.
    """
    return {
        "urls": get_mcp_urls(),
        "url_configured": bool(get_mcp_urls()),
        "api_key_configured": bool(get_mcp_api_key()),
        "api_key_header": "X-API-Key",
        "transport": "streamable_http",
    }


@app.get("/mcp/tools")
async def list_mcp_tools() -> dict[str, Any]:
    try:
        tools = await load_mcp_tools()

        return {
            "count": len(tools),
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                }
                for tool in tools
            ],
        }

    except Exception as exc:
        traceback.print_exception(
            type(exc),
            exc,
            exc.__traceback__,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to load MCP tools: "
                f"{repr(exc)}"
            ),
        ) from exc


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
) -> ChatResponse:
    user_message = request.message.strip()
    normalized_message = user_message.lower()

    try:
        if "add" in normalized_message:
            result = await call_mcp_tool(
                tool_name="add_numbers",
                arguments={
                    "a": 10,
                    "b": 25,
                },
            )

            return ChatResponse(
                response=f"MCP add_numbers result: {result}"
            )

        if "greet" in normalized_message:
            result = await call_mcp_tool(
                tool_name="greet",
                arguments={
                    "name": "Ahmed",
                },
            )

            return ChatResponse(
                response=f"MCP greet result: {result}"
            )

        return ChatResponse(
            response=(
                "Ask me to add numbers or greet someone "
                "to test the configured MCP server."
            )
        )

    except Exception as exc:
        traceback.print_exception(
            type(exc),
            exc,
            exc.__traceback__,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "MCP invocation failed: "
                f"{repr(exc)}"
            ),
        ) from exc


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
    )

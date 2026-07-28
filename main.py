import os
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from langchain_mcp_adapters.client import MultiServerMCPClient
from pydantic import BaseModel, Field


app = FastAPI(
    title="MCP-Enabled Platform-Hosted Agent",
    version="1.1.0",
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    response: str


def create_mcp_client() -> MultiServerMCPClient:
    raw_urls = os.environ.get("SIMPLE_TEST_MCP_URL", "")
    mcp_urls = [url.strip() for url in raw_urls.split(",") if url.strip()]

    mcp_api_key = os.environ.get(
        "SIMPLE_TEST_MCP_API_KEY",
        "",
    ).strip()

    if not mcp_urls:
        raise RuntimeError("SIMPLE_TEST_MCP_URL is not configured")

    server_configs: dict[str, dict[str, Any]] = {}

    for index, url in enumerate(mcp_urls):
        headers: dict[str, str] = {}

        if mcp_api_key:
            headers["API-Key"] = mcp_api_key

        server_configs[f"simple_test_mcp_{index}"] = {
            "url": url,
            "transport": "http",
            "headers": headers,
        }

    return MultiServerMCPClient(server_configs)


async def call_mcp_tool(
    tool_name: str,
    arguments: dict[str, Any],
) -> Any:
    client = create_mcp_client()
    tools = await client.get_tools()

    selected_tool = next(
        (tool for tool in tools if tool.name == tool_name),
        None,
    )

    if selected_tool is None:
        available_tools = [tool.name for tool in tools]
        raise RuntimeError(
            f"MCP tool '{tool_name}' was not found. "
            f"Available tools: {available_tools}"
        )

    return await selected_tool.ainvoke(arguments)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "Agent is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    user_message = request.message.strip()
    normalized_message = user_message.lower()

    try:
        if "add" in normalized_message:
            result = await call_mcp_tool(
                "add_numbers",
                {
                    "a": 10,
                    "b": 25,
                },
            )

            return ChatResponse(
                response=f"MCP add_numbers result: {result}"
            )

        if "greet" in normalized_message:
            result = await call_mcp_tool(
                "greet",
                {
                    "name": "Ahmed",
                },
            )

            return ChatResponse(
                response=f"MCP greet result: {result}"
            )

        return ChatResponse(
            response=(
                "Ask me to 'add' two numbers or 'greet' someone "
                "to test the configured MCP server."
            )
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"MCP invocation failed: {exc}",
        ) from exc


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
    )

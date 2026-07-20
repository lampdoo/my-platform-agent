from typing import Any

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field


app = FastAPI(
    title="Basic Platform-Hosted Agent",
    version="1.0.0",
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    response: str


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "Agent is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    user_message = request.message.strip()

    reply = (
        f"You said: {user_message}. "
        "I am a basic Python agent hosted on WSO2 Agent Manager."
    )

    return ChatResponse(response=reply)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
    )

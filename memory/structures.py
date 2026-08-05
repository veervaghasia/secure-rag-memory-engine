from datetime import datetime, timezone
from typing import Literal, Optional, Any, Dict
from pydantic import BaseModel, Field

class ChatMessage(BaseModel):
    """
    Data Transfer Object (DTO) representing a single message turn.
    Pure data container-no database logic included.
    """
    role: Literal["system", "user", "assistant"] = Field(
        ...,
        description="The message sender role adhering to LiteLLM standard."
    )
    content: str = Field(
        ...,
        description="Text contents of the user query or assistant response."
    )
    session_id: str = Field(
        default="default_session",
        description="Unique identifier for the current user chat session."
    )
    user_id: str = Field(
        default="default_user",
        description="Owner ID of the chat turn for metadata access checks."
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of when the message was recorded."
    )

    def to_llm_dict(self) -> Dict[str, str]:
        """
        Helper method converting the DTO into standard LiteLLM format.
        """
        return {
            "role": self.role,
            "content": self.content
        }
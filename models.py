from pydantic import BaseModel, Field
from typing import Optional


class TranscriptRequest(BaseModel):
    video_url: str = Field(..., description="YouTube video URL")
    language: str = Field(default="en", description="Language code for the transcript")
    filename: Optional[str] = Field(default=None, description="Custom filename (optional)")


class TranscriptResponse(BaseModel):
    success: bool
    video_id: str
    filename: str
    transcript: str
    message: str

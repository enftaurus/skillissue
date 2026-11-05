from typing import List, Optional
from pydantic import BaseModel, Field

class TtsRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=12000, description="Text to synthesize into speech (cleaned and truncated server-side)")
    voice: Optional[str] = Field("en-US-ChristopherNeural", description="Voice ID to use for synthesis")
    rate: Optional[str] = Field("+0%", description="Speech speed adjustment percentage (e.g. +5% or -10%)")
    pitch: Optional[str] = Field("+0Hz", description="Speech pitch adjustment")

class SttResponse(BaseModel):
    text: str = Field(..., description="Transcribed text from speech input")
    language: Optional[str] = Field("en", description="Detected or configured language")
    duration_seconds: Optional[float] = Field(None, description="Audio duration in seconds")
    delivery: Optional[dict] = Field(None, description="Spoken delivery metrics (pace, fillers, hedges, pauses)")

class VoiceOption(BaseModel):
    id: str
    name: str
    gender: str
    accent: str
    provider: str
    description: str
    available: bool = True
    unavailable_reason: Optional[str] = None

class VoiceListResponse(BaseModel):
    voices: List[VoiceOption]
    default_voice: str

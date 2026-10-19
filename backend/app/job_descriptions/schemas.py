from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

class JobDescriptionCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    company: Optional[str] = ""
    raw_text: str = Field(min_length=20)

class JobDescriptionUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    extracted_role: Optional[str] = None
    extracted_skills: Optional[List[str]] = None
    extracted_requirements: Optional[List[str]] = None

class JobDescriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    company: str
    raw_text: str
    extracted_role: str
    extracted_skills: List[str]
    extracted_requirements: List[str]
    created_at: datetime

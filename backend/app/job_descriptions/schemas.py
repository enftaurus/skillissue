from datetime import datetime
from typing import Annotated, List, Optional
from pydantic import BaseModel, ConfigDict, Field

class JobDescriptionCreate(BaseModel):
    # Bounds mirror the String(200) columns (overlong values used to 500 as a Postgres DataError);
    # only the first 5000 chars of raw_text reach the model, 50k is plenty for any real posting.
    title: str = Field(min_length=2, max_length=200)
    company: Optional[str] = Field(default="", max_length=200)
    raw_text: str = Field(min_length=20, max_length=50_000)

class JobDescriptionUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=200)
    company: Optional[str] = Field(default=None, max_length=200)
    extracted_role: Optional[str] = Field(default=None, max_length=200)
    extracted_skills: Optional[List[Annotated[str, Field(max_length=200)]]] = Field(default=None, max_length=100)
    extracted_requirements: Optional[List[Annotated[str, Field(max_length=1000)]]] = Field(default=None, max_length=100)
    extracted_experience: Optional[str] = Field(default=None, pattern="^(|fresher|junior|mid|senior)$")

class JobDescriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    company: str
    raw_text: str
    extracted_role: str
    extracted_skills: List[str]
    extracted_requirements: List[str]
    extracted_experience: str = ""
    created_at: datetime

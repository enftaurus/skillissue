from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict

class ResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    file_name: str
    extracted_skills: List[str]
    projects_context: List[Dict[str, Any]]
    created_at: datetime

class ResumeDetailResponse(ResumeResponse):
    extracted_text: str

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    target_role: Optional[str] = "Software Engineer"
    years_experience: Optional[float] = 0.0
    daily_study_minutes: Optional[int] = 45

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    user_id: str
    email: str

class RefreshTokenRequest(BaseModel):
    refresh_token: Optional[str] = None

class LogoutResponse(BaseModel):
    status: str = "logged_out"
    message: str = "Session successfully revoked"

class UserProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    target_role: str
    years_experience: float
    daily_study_minutes: int
    bio: Optional[str] = None

class UserProfileUpdate(BaseModel):
    target_role: Optional[str] = None
    years_experience: Optional[float] = None
    daily_study_minutes: Optional[int] = None
    bio: Optional[str] = None

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    is_active: bool
    created_at: datetime
    profile: Optional[UserProfileResponse] = None

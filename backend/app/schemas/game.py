from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    username: str = Field(min_length=2, max_length=40, pattern=r"^[\w .'-]+$")
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class QuestCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    category: str = "PERSONAL"
    attribute: str | None = Field(default=None, min_length=1, max_length=20)
    difficulty: str = "MEDIUM"


class SettingsUpdate(BaseModel):
    sound_enabled: bool | None = None
    reduced_motion: bool | None = None

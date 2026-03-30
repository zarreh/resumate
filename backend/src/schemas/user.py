"""User response schemas."""

import uuid

from pydantic import BaseModel, EmailStr


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    name: str

    model_config = {"from_attributes": True}

from typing import List, Optional, Any
from pydantic import BaseModel, Field
from enum import StrEnum

class BookNode(BaseModel):
    name: str
    id: str
    children: List['BookNode'] = Field(default_factory=list)
    py: Optional[str] = None
    guide: Optional[str] = None
    tests: List[Any] = Field(default_factory=list)
    isExample: Optional[bool] = False
    typ: Optional[str] = "py"  # "py" | "parsons" | "canvas"
    isAssessment: Optional[bool] = False
    # isLong: Optional[bool] = False
    # bookLink: Optional[str] = ""
    # sol: Optional[Any] = None
    # additionalFiles: Optional[List[Any]] = Field(default_factory=list)

BOOK_NODE_FIELDS = set(BookNode.model_fields.keys())

class AuthProvider(StrEnum):
    MSAL = "MSAL"
    GOOGLE = "GOOGLE"

class ServerSettings(BaseModel):
    is_debug: bool
    auth_provider: Optional[AuthProvider]

    google_client_id: Optional[str]
    utils_pwd: Optional[str]


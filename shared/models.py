from enum import StrEnum
from typing import Any, List, Optional

from pydantic import BaseModel, Field

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

class ClassModel(BaseModel):
    name: str
    active: Optional[bool] = None
    books: Optional[List[str]] = None
    join_code: Optional[str] = None
    disabled_books: Optional[List[str]] = None
    students: List[str]

class AuthProvider(StrEnum):
    MSAL = "MSAL"
    GOOGLE = "GOOGLE"

class AIProvider(StrEnum):
    GEMINI = "GEMINI"

class ServerSettings(BaseModel):
    is_debug: bool
    admin_accounts: List[str]

    site_url: Optional[str]
    ws_url: Optional[str]
    server_dir: str
    auth_provider: Optional[AuthProvider]
    can_edit_books_folder: Optional[bool]

    google_client_id: Optional[str]
    msal_client_id: Optional[str]
    msal_tenant_id: Optional[str]

    utils_pwd: Optional[str]
    jwt_sercret_key: Optional[str]
    fernet_key: Optional[str]

    # AI
    ai_provider: Optional[AIProvider]
    gemini_api_key: Optional[str]

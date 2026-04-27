from pydantic import BaseModel, Field
from typing import Optional, Any, Dict, List
from datetime import datetime, date
from uuid import UUID


class PolicyBase(BaseModel):
    name: str
    issuing_body: Optional[str] = None
    doc_type: Optional[str] = None
    policy_level: Optional[str] = None
    policy_subject: Optional[str] = None
    effective_date: Optional[date] = None
    deadline: Optional[date] = None
    consultation_contact: Optional[str] = None
    consultation_phone: Optional[str] = None
    consultation_website: Optional[str] = None


class PolicyCreate(PolicyBase):
    pass


class PolicyUpdate(BaseModel):
    name: Optional[str] = None
    issuing_body: Optional[str] = None
    doc_type: Optional[str] = None
    policy_level: Optional[str] = None
    policy_subject: Optional[str] = None
    effective_date: Optional[date] = None
    deadline: Optional[date] = None
    consultation_contact: Optional[str] = None
    consultation_phone: Optional[str] = None
    consultation_website: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None


class PolicyResponse(PolicyBase):
    id: UUID
    status: str
    version: int
    structured_data: Dict[str, Any]
    raw_text: Optional[str] = None
    upload_time: datetime
    uploader_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PolicyListItem(BaseModel):
    id: UUID
    name: str
    issuing_body: Optional[str] = None
    doc_type: Optional[str] = None
    policy_level: Optional[str] = None
    status: str
    upload_time: datetime
    uploader_id: Optional[UUID] = None
    deadline: Optional[date] = None

    class Config:
        from_attributes = True


class PolicyStructuredDataResponse(BaseModel):
    id: UUID
    name: str
    doc_type: Optional[str] = None
    policy_level: Optional[str] = None
    policy_subject: Optional[str] = None
    effective_date: Optional[date] = None
    deadline: Optional[date] = None
    consultation: Dict[str, str]
    structured_data: Dict[str, Any]

    class Config:
        from_attributes = True


class PolicyUploadResponse(BaseModel):
    id: UUID
    name: str
    status: str
    doc_type: Optional[str] = None
    policy_level: Optional[str] = None
    message: str


class FieldDefinitionResponse(BaseModel):
    id: UUID
    field_key: str
    field_label: Optional[str] = None
    field_type: Optional[str] = None
    policy_id: Optional[UUID] = None
    usage_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class ChatLogResponse(BaseModel):
    id: UUID
    session_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    question: str
    answer: Optional[str] = None
    model_provider: Optional[str] = None
    model_name: Optional[str] = None
    tokens_used: Optional[int] = None
    response_time_ms: Optional[int] = None
    cited_policies: List[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class ChatAskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    session_id: Optional[UUID] = None
    model_provider: Optional[str] = None


class ChatAskResponse(BaseModel):
    answer: str
    session_id: UUID
    cited_policies: List[Dict[str, Any]] = []


class ChatHistoryResponse(BaseModel):
    id: UUID
    session_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    question: str
    answer: Optional[str] = None
    cited_policies: List[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class KGNodeResponse(BaseModel):
    id: UUID
    node_type: str
    name: str
    policy_id: Optional[UUID] = None
    node_data: Dict[str, Any]

    class Config:
        from_attributes = True


class KGEdgeResponse(BaseModel):
    id: UUID
    source_id: UUID
    target_id: UUID
    relation: str
    source_policy_id: Optional[UUID] = None
    target_policy_id: Optional[UUID] = None

    class Config:
        from_attributes = True


class KGGraphResponse(BaseModel):
    nodes: List[KGNodeResponse]
    edges: List[KGEdgeResponse]


class KGSubgraphResponse(BaseModel):
    nodes: List[KGNodeResponse]
    edges: List[KGEdgeResponse]
    policy: PolicyResponse


class AttachmentResponse(BaseModel):
    id: UUID
    policy_id: Optional[UUID] = None
    filename: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_policies: int
    active_policies: int
    parsing_policies: int
    failed_policies: int
    total_users: int
    total_chats: int
    chats_today: int
    chats_this_week: int
    parse_success_rate: float

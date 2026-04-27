import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Date, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default="user")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    policies = relationship("Policy", back_populates="uploader")
    chat_logs = relationship("ChatLog", back_populates="user")
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="uploader")


class Policy(Base):
    __tablename__ = "policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(500), nullable=False)
    issuing_body = Column(String(500), nullable=True)
    file_path = Column(String(1000), nullable=True)
    upload_time = Column(DateTime, default=datetime.utcnow)
    status = Column(String(20), default="parsing")
    version = Column(Integer, default=1)
    doc_type = Column(String(100), nullable=True)
    policy_level = Column(String(50), nullable=True)
    policy_subject = Column(String(500), nullable=True)
    effective_date = Column(Date, nullable=True)
    deadline = Column(Date, nullable=True)
    consultation_contact = Column(String(500), nullable=True)
    consultation_phone = Column(String(100), nullable=True)
    consultation_website = Column(String(500), nullable=True)
    structured_data = Column(JSON, nullable=False, default=dict)
    raw_text = Column(Text, nullable=True)
    raw_text_updated_at = Column(DateTime, nullable=True)
    uploader_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    uploader = relationship("User", back_populates="policies")
    field_definitions = relationship("PolicyFieldDefinition", back_populates="policy", cascade="all, delete-orphan")
    kg_nodes = relationship("KGNode", back_populates="policy", cascade="all, delete-orphan")
    kg_edges_source = relationship("KGEdge", foreign_keys="KGEdge.source_policy_id", back_populates="source_policy")
    kg_edges_target = relationship("KGEdge", foreign_keys="KGEdge.target_policy_id", back_populates="target_policy")
    attachments = relationship("Attachment", back_populates="policy", cascade="all, delete-orphan")


class PolicyFieldDefinition(Base):
    __tablename__ = "policy_field_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    field_key = Column(String(100), nullable=False)
    field_label = Column(String(200), nullable=True)
    field_type = Column(String(50), nullable=True)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), nullable=True)
    description = Column(Text, nullable=True)
    extraction_model = Column(String(50), nullable=True)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    policy = relationship("Policy", back_populates="field_definitions")

    __table_args__ = (
        Index("idx_field_def_policy_key", "policy_id", "field_key", unique=True),
    )


class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)
    model_provider = Column(String(50), nullable=True)
    model_name = Column(String(100), nullable=True)
    tokens_used = Column(Integer, nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    cited_policies = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="chat_logs")
    session = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        Index("idx_chat_logs_user", "user_id"),
        Index("idx_chat_logs_session", "session_id"),
    )


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name = Column(String(255), nullable=False, default="新会话")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatLog", back_populates="session", cascade="all, delete-orphan", order_by="ChatLog.created_at")

    __table_args__ = (
        Index("idx_chat_sessions_user", "user_id"),
    )


class KGNode(Base):
    __tablename__ = "kg_nodes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    node_type = Column(String(50), nullable=False)
    name = Column(String(500), nullable=False)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), nullable=True)
    node_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    policy = relationship("Policy", back_populates="kg_nodes")
    edges_out = relationship("KGEdge", foreign_keys="KGEdge.source_id", back_populates="source_node", cascade="all, delete-orphan")
    edges_in = relationship("KGEdge", foreign_keys="KGEdge.target_id", back_populates="target_node", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_kg_nodes_policy", "policy_id"),
        Index("idx_kg_nodes_type", "node_type"),
    )


class KGEdge(Base):
    __tablename__ = "kg_edges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("kg_nodes.id", ondelete="CASCADE"), nullable=True)
    target_id = Column(UUID(as_uuid=True), ForeignKey("kg_nodes.id", ondelete="CASCADE"), nullable=True)
    relation = Column(String(50), nullable=False)
    source_policy_id = Column(UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), nullable=True)
    target_policy_id = Column(UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), nullable=True)
    edge_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    source_node = relationship("KGNode", foreign_keys=[source_id], back_populates="edges_out")
    target_node = relationship("KGNode", foreign_keys=[target_id], back_populates="edges_in")
    source_policy = relationship("Policy", foreign_keys=[source_policy_id], back_populates="kg_edges_source")
    target_policy = relationship("Policy", foreign_keys=[target_policy_id], back_populates="kg_edges_target")

    __table_args__ = (
        Index("idx_kg_edges_source", "source_id"),
        Index("idx_kg_edges_target", "target_id"),
        Index("idx_kg_edges_source_policy", "source_policy_id"),
    )


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id = Column(UUID(as_uuid=True), ForeignKey("policies.id", ondelete="CASCADE"), nullable=True)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    description = Column(Text, nullable=True)
    uploader_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    policy = relationship("Policy", back_populates="attachments")
    uploader = relationship("User", back_populates="attachments")

    __table_args__ = (
        Index("idx_attachments_policy", "policy_id"),
    )

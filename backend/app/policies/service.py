import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, update
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.policies.models import Policy, ChatLog, KGNode, KGEdge, Attachment, User
from app.policies.schemas import PolicyUpdate


class PolicyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_policies(self, status: Optional[str] = None, skip: int = 0, limit: int = 50) -> List[Policy]:
        query = select(Policy).order_by(Policy.upload_time.desc())
        if status:
            query = query.where(Policy.status == status)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_policy(self, policy_id: UUID) -> Optional[Policy]:
        result = await self.db.execute(select(Policy).where(Policy.id == policy_id))
        return result.scalar_one_or_none()

    async def create_policy(self, name: str, uploader_id: Optional[UUID] = None, file_path: Optional[str] = None) -> Policy:
        policy = Policy(
            name=name,
            uploader_id=uploader_id,
            file_path=file_path,
            status="parsing",
        )
        self.db.add(policy)
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def update_policy(self, policy_id: UUID, data: PolicyUpdate) -> Optional[Policy]:
        policy = await self.get_policy(policy_id)
        if not policy:
            return None
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(policy, key, value)
        policy.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def update_status(self, policy_id: UUID, status: str) -> Optional[Policy]:
        policy = await self.get_policy(policy_id)
        if not policy:
            return None
        policy.status = status
        policy.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def update_structured_data(
        self,
        policy_id: UUID,
        structured_data: Dict[str, Any],
        doc_type: Optional[str] = None,
        policy_level: Optional[str] = None,
        issuing_body: Optional[str] = None,
        policy_subject: Optional[str] = None,
        effective_date=None,
        deadline=None,
        consultation_contact: Optional[str] = None,
        consultation_phone: Optional[str] = None,
        consultation_website: Optional[str] = None,
    ) -> Optional[Policy]:
        policy = await self.get_policy(policy_id)
        if not policy:
            return None
        policy.structured_data = structured_data
        policy.status = "active"
        if doc_type:
            policy.doc_type = doc_type
        if policy_level:
            policy.policy_level = policy_level
        if issuing_body:
            policy.issuing_body = issuing_body
        if policy_subject:
            policy.policy_subject = policy_subject
        if effective_date:
            policy.effective_date = effective_date
        if deadline:
            policy.deadline = deadline
        if consultation_contact:
            policy.consultation_contact = consultation_contact
        if consultation_phone:
            policy.consultation_phone = consultation_phone
        if consultation_website:
            policy.consultation_website = consultation_website
        policy.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(policy)
        return policy

    async def delete_policy(self, policy_id: UUID) -> bool:
        policy = await self.get_policy(policy_id)
        if not policy:
            return False
        await self.db.delete(policy)
        await self.db.commit()
        return True

    async def search_policies(self, keyword: str, limit: int = 10) -> List[Policy]:
        pattern = f"%{keyword}%"
        query = (
            select(Policy)
            .where(Policy.status == "active")
            .where(Policy.name.ilike(pattern) | Policy.policy_subject.ilike(pattern))
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_all_active_structured(self, limit: int = 20) -> List[Policy]:
        query = (
            select(Policy)
            .where(Policy.status == "active")
            .order_by(Policy.updated_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_timeline_policies(self) -> List[Policy]:
        query = (
            select(Policy)
            .where(Policy.status == "active")
            .where(Policy.deadline.isnot(None))
            .order_by(Policy.deadline.asc())
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_log(
        self,
        question: str,
        answer: str,
        user_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        model_provider: Optional[str] = None,
        model_name: Optional[str] = None,
        tokens_used: Optional[int] = None,
        response_time_ms: Optional[int] = None,
        cited_policies: Optional[List[Dict]] = None,
    ) -> ChatLog:
        log = ChatLog(
            user_id=user_id,
            session_id=session_id,
            question=question,
            answer=answer,
            model_provider=model_provider,
            model_name=model_name,
            tokens_used=tokens_used,
            response_time_ms=response_time_ms,
            cited_policies=cited_policies or [],
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def get_logs_by_user(self, user_id: UUID, skip: int = 0, limit: int = 50) -> List[ChatLog]:
        query = (
            select(ChatLog)
            .where(ChatLog.user_id == user_id)
            .order_by(ChatLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_all_logs(self, skip: int = 0, limit: int = 50, user_id: Optional[UUID] = None) -> List[ChatLog]:
        query = select(ChatLog).order_by(ChatLog.created_at.desc())
        if user_id:
            query = query.where(ChatLog.user_id == user_id)
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_chats_today(self) -> int:
        today = datetime.utcnow().date()
        result = await self.db.execute(
            select(func.count(ChatLog.id)).where(
                func.date(ChatLog.created_at) == today
            )
        )
        return result.scalar() or 0

    async def get_chats_this_week(self) -> int:
        week_ago = datetime.utcnow() - timedelta(days=7)
        result = await self.db.execute(
            select(func.count(ChatLog.id)).where(ChatLog.created_at >= week_ago)
        )
        return result.scalar() or 0


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(self, skip: int = 0, limit: int = 50) -> List[User]:
        query = select(User).order_by(User.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_user(self, user_id: UUID) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_user_role(self, user_id: UUID, role: str) -> Optional[User]:
        user = await self.get_user(user_id)
        if not user:
            return None
        user.role = role
        user.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete_user(self, user_id: UUID) -> bool:
        user = await self.get_user(user_id)
        if not user:
            return False
        await self.db.delete(user)
        await self.db.commit()
        return True

    async def count_users(self) -> int:
        result = await self.db.execute(select(func.count(User.id)))
        return result.scalar() or 0


class KGService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_full_graph(self) -> tuple[List[KGNode], List[KGEdge]]:
        nodes_result = await self.db.execute(select(KGNode))
        edges_result = await self.db.execute(select(KGEdge))
        return list(nodes_result.scalars().all()), list(edges_result.scalars().all())

    async def get_policy_subgraph(self, policy_id: UUID) -> tuple[List[KGNode], List[KGEdge]]:
        nodes_result = await self.db.execute(
            select(KGNode).where(KGNode.policy_id == policy_id)
        )
        edges_result = await self.db.execute(
            select(KGEdge).where(
                (KGEdge.source_policy_id == policy_id) | (KGEdge.target_policy_id == policy_id)
            )
        )
        return list(nodes_result.scalars().all()), list(edges_result.scalars().all())

    async def query_by_question(self, question: str, policy_ids: Optional[List[UUID]] = None) -> tuple[List[KGNode], List[KGEdge]]:
        if policy_ids:
            nodes_result = await self.db.execute(
                select(KGNode).where(KGNode.policy_id.in_(policy_ids))
            )
        else:
            nodes_result = await self.db.execute(select(KGNode))
        edges_result = await self.db.execute(select(KGEdge))
        return list(nodes_result.scalars().all()), list(edges_result.scalars().all())

    async def create_node(self, node_type: str, name: str, policy_id: Optional[UUID] = None, node_data: Optional[Dict] = None) -> KGNode:
        node = KGNode(
            node_type=node_type,
            name=name,
            policy_id=policy_id,
            node_data=node_data or {},
        )
        self.db.add(node)
        await self.db.commit()
        await self.db.refresh(node)
        return node

    async def create_edge(self, source_id: UUID, target_id: UUID, relation: str, source_policy_id: Optional[UUID] = None, target_policy_id: Optional[UUID] = None, edge_data: Optional[Dict] = None) -> KGEdge:
        edge = KGEdge(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            source_policy_id=source_policy_id,
            target_policy_id=target_policy_id,
            edge_data=edge_data or {},
        )
        self.db.add(edge)
        await self.db.commit()
        await self.db.refresh(edge)
        return edge

    async def build_graph_from_policy(self, policy_id: UUID, structured_data: Dict[str, Any], policy_name: str) -> None:
        existing = await self.db.execute(
            select(KGNode).where(KGNode.policy_id == policy_id)
        )
        if existing.scalars().first():
            return

        policy_node = await self.create_node(
            node_type="Policy",
            name=policy_name,
            policy_id=policy_id,
            node_data={"policy_id": str(policy_id)},
        )

        field_type_map = {
            "申报对象": "ApplicantObject",
            "申报条件": "Condition",
            "申报材料": "Material",
            "支持标准": "Subsidy",
            "补贴标准": "Subsidy",
            "申报时间": "TimelineNode",
            "子政策": "SubPolicy",
        }

        for field_key, field_value in structured_data.items():
            node_type = field_type_map.get(field_key, "CustomField")

            if isinstance(field_value, list):
                for item in field_value:
                    if isinstance(item, str) and item.strip():
                        await self.create_node(
                            node_type=node_type,
                            name=item[:200],
                            policy_id=policy_id,
                            node_data={"field_key": field_key, "source_field": field_key},
                        )
            elif isinstance(field_value, dict):
                for sub_key, sub_value in field_value.items():
                    label = f"{field_key}: {sub_key} = {sub_value}"
                    await self.create_node(
                        node_type=node_type,
                        name=label[:200],
                        policy_id=policy_id,
                        node_data={"field_key": field_key, "sub_key": sub_key, "value": str(sub_value)},
                    )
            elif isinstance(field_value, str) and field_value.strip():
                await self.create_node(
                    node_type=node_type,
                    name=field_value[:200],
                    policy_id=policy_id,
                    node_data={"field_key": field_key},
                )


class AttachmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_attachments(self, policy_id: Optional[UUID] = None) -> List[Attachment]:
        query = select(Attachment)
        if policy_id:
            query = query.where(Attachment.policy_id == policy_id)
        result = await self.db.execute(query.order_by(Attachment.created_at.desc()))
        return list(result.scalars().all())

    async def create_attachment(
        self,
        filename: str,
        file_path: str,
        uploader_id: Optional[UUID] = None,
        policy_id: Optional[UUID] = None,
        description: Optional[str] = None,
    ) -> Attachment:
        att = Attachment(
            filename=filename,
            file_path=file_path,
            uploader_id=uploader_id,
            policy_id=policy_id,
            description=description,
        )
        self.db.add(att)
        await self.db.commit()
        await self.db.refresh(att)
        return att

    async def delete_attachment(self, attachment_id: UUID) -> bool:
        result = await self.db.execute(select(Attachment).where(Attachment.id == attachment_id))
        att = result.scalar_one_or_none()
        if not att:
            return False
        await self.db.delete(att)
        await self.db.commit()
        return True

import uuid
import time
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from app.extraction.llm_providers import get_llm_provider
from app.policies.models import Policy, ChatLog


SYSTEM_PROMPT_ANSWER = """你是一个专业的政策问答助手。你的职责是根据提供的政策结构化数据，准确回答用户的问题。

回答原则：
1. 答案必须严格基于提供的政策结构化数据，不要编造信息
2. 如果提供的数据中包含相关政策信息，请基于这些信息给出准确回答
3. 如果数据中没有相关信息，请明确告知用户，而不是猜测
4. 回答应该清晰、有条理，适当使用列表和结构化格式
5. 回答中应引用具体的政策名称和数据来源
6. 对于涉及金额、比例、时间等具体数据的信息，请确保准确引用
7. 可以参考政策原始文本中的相关内容来补充说明
8. 如果当前问题与之前的对话历史相关，请结合历史上下文综合回答

在回答完成后，请在cited_policies中列出你参考了哪些政策，并简述引用理由。"""

SYSTEM_PROMPT_ROUTE = """给定用户的提问，判断应该查询哪些政策：

1. 如果问题明确提到了具体政策名称（如"专精特新政策"），直接匹配该政策
2. 如果问题涉及政策类型（如"补贴"、"人才"、"税收优惠"），匹配相关类型的所有政策
3. 如果问题是通用性问题（如"有什么扶持政策"），返回与问题关键词最相关的政策（最多5个）
4. 如果问题提到具体地区（如"深圳"、"北京"），优先匹配该地区的政策
5. 如果问题提到具体行业（如"制造业"、"科技企业"），优先匹配相关行业政策

返回JSON格式：
{
  "intent": "specific_policy|policy_type|general|regional|industry",
  "keywords": ["关键词1", "关键词2"],
  "matched_policy_names": ["政策名称1", "政策名称2"],
  "reasoning": "判断理由"
}"""


class ChatService:
    def __init__(self, db):
        self.db = db

    async def answer_question(
        self,
        question: str,
        user_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
        model_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        import time
        start_time = time.time()

        provider = get_llm_provider(model_provider)

        intent_result = await self._route_question(question, provider)
        matched_policies = await self._get_matched_policies(intent_result)
        cited = self._build_cited_policies(matched_policies, intent_result)

        history_str = ""
        if session_id:
            from sqlalchemy import select
            from app.policies.models import ChatLog
            result = await self.db.execute(
                select(ChatLog)
                .where(ChatLog.session_id == session_id)
                .order_by(ChatLog.created_at.desc())
                .limit(6)
            )
            history_logs = list(result.scalars().all()[::-1])
            history_parts = []
            for log in history_logs:
                history_parts.append(f"用户：{log.question}")
                history_parts.append(f"助手：{log.answer}")
            history_str = "\n".join(history_parts)

        context = self._build_context(question, history_str, matched_policies, intent_result)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_ANSWER},
            {"role": "user", "content": context},
        ]
        answer = await provider.generate(messages)

        elapsed_ms = int((time.time() - start_time) * 1000)

        chat_log = ChatLog(
            user_id=user_id,
            session_id=session_id,
            question=question,
            answer=answer,
            model_provider=provider.provider_name,
            model_name=provider.model_name,
            response_time_ms=elapsed_ms,
            cited_policies=cited,
        )
        self.db.add(chat_log)
        await self.db.commit()

        return {
            "answer": answer,
            "cited_policies": cited,
            "response_time_ms": elapsed_ms,
            "model_provider": provider.provider_name,
            "model_name": provider.model_name,
        }

    async def _route_question(self, question: str, provider) -> Dict[str, Any]:
        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT_ROUTE}, {"role": "user", "content": question}]
            result = await provider.generate_json(messages)
            return result
        except Exception:
            return {
                "intent": "general",
                "keywords": question.split(),
                "matched_policy_names": [],
                "reasoning": "默认通用查询",
            }

    async def _get_matched_policies(self, intent: Dict[str, Any]) -> List[Any]:
        from sqlalchemy import select
        from app.policies.models import Policy

        matched = []
        query = select(Policy).where(Policy.status == "active")

        if intent.get("matched_policy_names"):
            names = intent["matched_policy_names"]
            for name in names[:3]:
                result = await self.db.execute(
                    select(Policy).where(Policy.name.ilike(f"%{name}%"))
                )
                policy = result.scalar_one_or_none()
                if policy and policy not in matched:
                    matched.append(policy)

        if not matched:
            keywords = intent.get("keywords", [])
            if keywords:
                for kw in keywords[:2]:
                    result = await self.db.execute(
                        select(Policy)
                        .where(Policy.status == "active")
                        .where(
                            Policy.name.ilike(f"%{kw}%")
                            | Policy.policy_subject.ilike(f"%{kw}%")
                            | Policy.doc_type.ilike(f"%{kw}%")
                        )
                        .limit(3)
                    )
                    for policy in result.scalars().all():
                        if policy not in matched:
                            matched.append(policy)

        if not matched:
            result = await self.db.execute(
                select(Policy)
                .where(Policy.status == "active")
                .order_by(Policy.updated_at.desc())
                .limit(5)
            )
            for policy in result.scalars().all():
                if policy not in matched:
                    matched.append(policy)

        return matched

    def _build_context(self, question: str, history_str: str, policies: List[Any], intent: Dict[str, Any]) -> str:
        if not policies:
            return "（当前数据库中没有匹配的政策数据）"

        context_parts = []

        context_parts.append("【用户当前问题】")
        context_parts.append(question)

        if history_str:
            context_parts.append(f"\n{'='*60}\n")
            context_parts.append("【对话历史】")
            context_parts.append(history_str)

        context_parts.append(f"\n{'='*60}\n")
        context_parts.append("【政策上下文】")
        for i, policy in enumerate(policies, 1):
            context_parts.append(f"\n{'='*60}\n")
            context_parts.append(f"【政策 {i}】{policy.name}")
            if policy.issuing_body:
                context_parts.append(f"发文单位：{policy.issuing_body}")
            if policy.doc_type:
                context_parts.append(f"政策类型：{policy.doc_type}")
            if policy.policy_level:
                context_parts.append(f"政策级别：{policy.policy_level}")
            if policy.effective_date:
                context_parts.append(f"生效日期：{policy.effective_date}")
            if policy.deadline:
                context_parts.append(f"申报截止日期：{policy.deadline}")
            context_parts.append(f"\n结构化数据：")

            sd = policy.structured_data or {}
            if sd:
                context_parts.append(self._format_structured_data(sd))
            else:
                context_parts.append("（暂无结构化数据）")

            if policy.raw_text:
                context_parts.append(f"\n相关原文片段：{policy.raw_text[:500]}...")

        return "\n".join(context_parts)

    def _format_structured_data(self, sd: Dict[str, Any], indent: int = 0) -> str:
        parts = []
        prefix = "  " * indent
        for key, value in sd.items():
            if isinstance(value, list):
                parts.append(f"{prefix}{key}：")
                for item in value[:10]:
                    if isinstance(item, dict):
                        parts.append(self._format_structured_data(item, indent + 1))
                    else:
                        parts.append(f"{prefix}  - {item}")
            elif isinstance(value, dict):
                parts.append(f"{prefix}{key}：")
                parts.append(self._format_structured_data(value, indent + 1))
            else:
                parts.append(f"{prefix}{key}：{value}")
        return "\n".join(parts)

    def _build_cited_policies(self, policies: List[Any], intent: Dict[str, Any]) -> List[Dict[str, Any]]:
        cited = []
        for policy in policies:
            cited.append({
                "policy_id": str(policy.id),
                "policy_name": policy.name,
                "reason": f"关键词匹配：{', '.join(intent.get('keywords', []))}",
            })
        return cited

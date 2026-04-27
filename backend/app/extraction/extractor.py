import json
import re
from datetime import datetime, date
from typing import Any, Dict, Optional
from uuid import UUID

from app.extraction.llm_providers import get_llm_provider, LLMProvider
from app.config import get_settings

settings = get_settings()

# 顶层字段名，不应出现在 structured_data 中
TOP_LEVEL_FIELDS = {
    "policy_name", "issuing_body", "policy_level", "policy_subject",
    "effective_date", "deadline",
    "consultation_contact", "consultation_phone", "consultation_website",
    "doc_type", "doc_type_reason",
}

# structured_data 中应该过滤掉的垃圾字段
GARBAGE_FIELDS = {
    "原始内容摘要", "文档长度", "policy_name", "issuing_body",
    "policy_level", "policy_subject", "effective_date", "deadline",
    "consultation_contact", "consultation_phone", "consultation_website",
    "doc_type", "doc_type_reason", "structured_data",
}


SYSTEM_PROMPT_EXTRACT = """你是一个专业的政府政策文件结构化提取专家。

请从以下政策文本中提取关键信息，返回纯JSON格式。

重要规则：
1. 只在 structured_data 中放入政策的具体内容字段（申报对象、申报条件、申报材料、支持内容、补贴标准等）
2. 政策的基本信息（policy_name、issuing_body等）放在顶层，不要重复放入 structured_data
3. 不要添加"原始内容摘要"、"文档长度"等无意义字段
4. 如果文档有多个子政策（如针对不同类型企业的不同支持措施），每个子政策提取为 structured_data 中的一个条目，包含：子政策名称、申报对象、支持内容/补贴标准、申报条件、申报材料、时间节点
5. deadline 字段必须填写具体的截止日期（YYYY-MM-DD格式），如果申报时间是一个范围，填范围的最后一天截止日期；如果只有开始时间则以开始时间为准；如果申报时间不确定，填null

返回格式（必须是有效JSON，不要有任何其他文字）：
{
  "policy_name": "政策完整名称",
  "issuing_body": "发文机关全称",
  "policy_level": "国家级/省级/市级/区级",
  "policy_subject": "政策主题/关键词",
  "effective_date": "YYYY-MM-DD或null",
  "deadline": "YYYY-MM-DD（申报截止日期，如果申报时间是范围填最后一天，申报时间不确定填null）",
  "consultation_contact": "联系人（无则null）",
  "consultation_phone": "联系电话（无则null）",
  "consultation_website": "咨询网站（无则null）",
  "structured_data": {
    // === 分项支持措施（必填，即使只有一条）===
    "分项支持措施": [
      {
        "子政策名称": "支持措施名称，如：跨境电商平台奖励",
        "申报对象": "符合条件的企业或主体",
        "支持内容": "具体支持内容，如：给予平台企业最高100万元奖励",
        "申报条件": "申报需要满足的条件",
        "申报材料": "需要提交的材料清单",
        "申报时间": "申报时间节点（如有）",
        "备注": "其他补充说明（如有）"
      },
      ...
    ],
    // === 通用申报信息 ===
    "申报对象": ["可申报的企业/主体列表"],
    "申报条件": ["申报条件1", "申报条件2"],
    "申报材料": ["材料1", "材料2"],
    "申报时间": "申报起止时间（如有）",
    "联系方式": "其他补充联系方式（如有）"
  }
}

如果没有找到任何分项支持措施，请从文档中提取所有申报相关内容放入 structured_data。
请严格按JSON格式输出，只输出JSON，不要有任何其他文字。"""


class PolicyExtractor:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self._provider = provider

    @property
    def provider(self) -> LLMProvider:
        if self._provider is None:
            return get_llm_provider(settings.llm_provider)
        return self._provider

    async def extract(self, raw_text: str, policy_id: UUID) -> Dict[str, Any]:
        if len(raw_text) < 50:
            return self._empty_result(policy_id)

        # 根据文档长度调整截取长度，最多15K字符
        if len(raw_text) <= 8000:
            truncated = raw_text
        else:
            truncated = raw_text[:15000]
            truncated += f"\n\n[文档共{len(raw_text)}字符，已截取前15000字符]"

        try:
            messages = [{"role": "system", "content": SYSTEM_PROMPT_EXTRACT}, {"role": "user", "content": truncated}]
            result = await self.provider.generate_json(messages)
            return self._normalize_result(result)
        except json.JSONDecodeError:
            text_result = await self.provider.generate(messages)
            return self._parse_text_result(text_result)
        except Exception as e:
            return self._fallback_extract(truncated)

    def _normalize_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """规范化提取结果，清理垃圾字段"""
        # 1. 分离顶层字段和 structured_data
        top_level = {}
        sd = result.get("structured_data") or {}

        for key in TOP_LEVEL_FIELDS:
            if key in result:
                top_level[key] = result.pop(key)

        # 2. 清理 structured_data 中的垃圾字段
        if isinstance(sd, dict):
            cleaned_sd = {}
            for key, value in sd.items():
                # 跳过顶层字段的残留
                if key in TOP_LEVEL_FIELDS:
                    top_level[key] = top_level.get(key) or value
                    continue
                # 跳过垃圾字段
                if key in GARBAGE_FIELDS:
                    continue
                # 跳过纯摘要/元数据字段（包含特定关键词的）
                if self._is_garbage_field(key, value):
                    continue
                cleaned_sd[key] = value
            sd = cleaned_sd

        # 3. 如果有分项支持措施，验证并规范化每一项
        if "分项支持措施" in sd:
            sd["分项支持措施"] = self._normalize_sub_policies(sd["分项支持措施"])

        # 4. 处理日期
        result["effective_date"] = self._parse_date(top_level.get("effective_date") or result.get("effective_date"))
        top_deadline = self._parse_date(top_level.get("deadline") or result.get("deadline"))
        # 如果顶层 deadline 为空，尝试从 structured_data 的申报时间字段中提取
        if not top_deadline:
            top_deadline = self._extract_deadline_from_structured(sd)
        result["deadline"] = top_deadline

        # 5. 构建最终结果
        out = {
            "policy_name": top_level.get("policy_name") or result.get("policy_name"),
            "issuing_body": top_level.get("issuing_body") or result.get("issuing_body"),
            "policy_level": top_level.get("policy_level") or result.get("policy_level"),
            "policy_subject": top_level.get("policy_subject") or result.get("policy_subject"),
            "effective_date": result["effective_date"],
            "deadline": result["deadline"],
            "consultation_contact": top_level.get("consultation_contact") or result.get("consultation_contact"),
            "consultation_phone": top_level.get("consultation_phone") or result.get("consultation_phone"),
            "consultation_website": top_level.get("consultation_website") or result.get("consultation_website"),
            "structured_data": sd,
        }

        return out

    def _is_garbage_field(self, key: str, value: Any) -> bool:
        """判断字段是否为垃圾字段"""
        # 包含这些关键词的通常是摘要/元数据
        garbage_keywords = ["摘要", "原文", "文档", "长度", "字数", "概述", "目录"]
        for kw in garbage_keywords:
            if kw in key:
                return True
        # 值为纯文本摘要（超过200字符且不含结构化信息）
        if isinstance(value, str) and len(value) > 200:
            # 检查是否像摘要（包含"根据"、"本政策"、"文件"等词）
            if re.search(r"根据.{0,20}(?:政策|文件|指南|办法|通知)", value):
                return True
            if "结构化" in value or "可机读" in value or "JSON格式" in value:
                return True
        # 空值或空列表
        if value is None or value == "":
            return True
        if isinstance(value, list) and len(value) == 0:
            return True
        return False

    def _normalize_sub_policies(self, sub_policies: Any) -> list:
        """规范化分项支持措施"""
        if not isinstance(sub_policies, list):
            return []
        normalized = []
        for sp in sub_policies:
            if not isinstance(sp, dict):
                continue
            # 提取关键字段
            item = {}
            # 子政策名称 - 尝试多个可能的key
            for name_key in ["子政策名称", "支持措施名称", "措施名称", "名称", "name"]:
                if sp.get(name_key):
                    item["子政策名称"] = sp[name_key]
                    break
            # 申报对象
            for obj_key in ["申报对象", "适用对象", "支持对象", "对象"]:
                if sp.get(obj_key):
                    item["申报对象"] = sp[obj_key]
                    break
            # 支持内容
            for content_key in ["支持内容", "支持措施", "补贴标准", "奖励标准", "奖励内容", "内容", "标准"]:
                if sp.get(content_key):
                    item["支持内容"] = sp[content_key]
                    break
            # 申报条件
            for cond_key in ["申报条件", "申报要求", "条件", "requirements"]:
                if sp.get(cond_key):
                    item["申报条件"] = sp[cond_key]
                    break
            # 申报材料
            for mat_key in ["申报材料", "材料清单", "材料", "materials"]:
                if sp.get(mat_key):
                    item["申报材料"] = sp[mat_key]
                    break
            # 申报时间
            for time_key in ["申报时间", "申报截止", "时间节点", "timeline"]:
                if sp.get(time_key):
                    item["申报时间"] = sp[time_key]
                    break
            # 备注
            for note_key in ["备注", "说明", "补充", "note"]:
                if sp.get(note_key):
                    item["备注"] = sp[note_key]
                    break
            # 只有包含有意义内容的才保留
            if any(v for k, v in item.items() if k != "备注"):
                normalized.append(item)
        return normalized

    def _parse_text_result(self, text: str) -> Dict[str, Any]:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        try:
            result = json.loads(text)
            return self._normalize_result(result)
        except json.JSONDecodeError:
            # 尝试提取 JSON 块
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                try:
                    result = json.loads(match.group())
                    return self._normalize_result(result)
                except json.JSONDecodeError:
                    pass
            return self._fallback_extract(text)

    def _parse_date(self, date_str: Any) -> Optional[date]:
        if not date_str:
            return None
        if isinstance(date_str, (datetime, date)):
            if isinstance(date_str, datetime):
                return date_str.date()
            return date_str
        s = str(date_str).strip()

        # 1. 尝试处理日期范围（包含"至"或"~"分隔的两个日期），取最后一个作为截止日期
        full_date_re = re.compile(r"\d{4}[-年]\d{1,2}[-月]\d{1,2}[日]?")
        found = list(full_date_re.findall(s))
        if len(found) >= 2:
            last = found[-1]
            normalized = re.sub(r"(\d{4})[-年](\d{1,2})[-月](\d{1,2})日?", r"\1-\2-\3", last)
            try:
                return datetime.strptime(normalized, "%Y-%m-%d").date()
            except ValueError:
                pass

        # 2. 单一日期：直接用匹配到的原始子串
        m = re.search(r"\d{4}[-年]\d{1,2}[-月]\d{1,2}[日]?", s)
        if m:
            normalized = re.sub(r"(\d{4})[-年](\d{1,2})[-月](\d{1,2})日?", r"\1-\2-\3", m.group())
            try:
                return datetime.strptime(normalized, "%Y-%m-%d").date()
            except ValueError:
                pass

        m = re.search(r"\d{4}[-年]\d{1,2}[-月]", s)
        if m:
            normalized = re.sub(r"(\d{4})[-年](\d{1,2})[-月]", r"\1-\2", m.group())
            try:
                return datetime.strptime(normalized, "%Y-%m").date()
            except ValueError:
                pass

        m = re.search(r"\d{4}年", s)
        if m:
            try:
                return datetime.strptime(m.group()[:4], "%Y").date()
            except ValueError:
                pass

        return None

    def _extract_deadline_from_structured(self, sd: Dict[str, Any]) -> Optional[date]:
        """从 structured_data 的申报时间字段中智能提取截止日期"""
        deadline_keys = ["申报时间", "申报截止", "申报截止日期", "申报开始", "申报期限"]
        # 1. 检查顶层申报时间字段
        for key in deadline_keys:
            if key not in sd:
                continue
            val = sd[key]
            parsed = self._try_parse_deadline_value(val)
            if parsed:
                return parsed
        # 2. 检查分项支持措施中的申报时间
        if "分项支持措施" in sd and isinstance(sd["分项支持措施"], list):
            for sp in sd["分项支持措施"]:
                if isinstance(sp, dict) and "申报时间" in sp:
                    parsed = self._try_parse_deadline_value(sp["申报时间"])
                    if parsed:
                        return parsed
        return None

    def _try_parse_deadline_value(self, val: Any) -> Optional[date]:
        """从字段值中尝试解析截止日期"""
        if isinstance(val, str) and val.strip():
            parsed = self._parse_date(val)
            if parsed:
                return parsed
        if isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    parsed = self._parse_date(item)
                    if parsed:
                        return parsed
        if isinstance(val, dict):
            for v in val.values():
                if isinstance(v, str):
                    parsed = self._parse_date(v)
                    if parsed:
                        return parsed
        return None

    def _fallback_extract(self, text: str) -> Dict[str, Any]:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return {
            "policy_name": lines[0][:200] if lines else "政策文件",
            "issuing_body": None,
            "policy_level": None,
            "policy_subject": None,
            "effective_date": None,
            "deadline": None,
            "consultation_contact": None,
            "consultation_phone": None,
            "consultation_website": None,
            "structured_data": {
                "原始内容": text[:2000] + ("..." if len(text) > 2000 else ""),
            },
        }

    def _empty_result(self, policy_id: UUID) -> Dict[str, Any]:
        return {
            "policy_name": None,
            "issuing_body": None,
            "policy_level": None,
            "policy_subject": None,
            "effective_date": None,
            "deadline": None,
            "consultation_contact": None,
            "consultation_phone": None,
            "consultation_website": None,
            "structured_data": {},
        }

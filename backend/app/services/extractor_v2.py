import json
import re
import uuid
from typing import Any
from app.services.llm import structured_extraction, chat_completion

DOC_TYPE_SYSTEM_PROMPT = """你是一个专业的政府政策文件结构分析专家。

你的任务是根据政策文档的内容，判断这份文档属于哪种类型，并提取文档的章节大纲。

请仔细阅读文本，判断文档类型：

文档类型定义：
- 综合性政策（type: "comprehensive"）: 申报通知、支持办法、管理办法等，涉及多个方面的政策
- 单一补贴（type: "subsidy"）: 主要聚焦于某一项补贴/资助，补贴标准明确
- 认定类（type: "certification"）: 主要聚焦于资质认定、评定、评审，如高新技术企业认定、科技型中小企业评价
- 人才类（type: "talent"）: 主要聚焦于人才引进、培养、激励政策
- 税收优惠（type: "tax"）: 主要涉及税收减免、抵扣等优惠
- 科技类（type: "tech"）: 主要涉及科技项目、研发费用、科技成果等
- 金融支持（type: "finance"）: 涉及贷款、融资、担保等金融支持
- 用地支持（type: "land"）: 涉及土地、场地、房租优惠
- 其他（type: "other"）: 无法归入以上类型的政策

章节识别：识别文档的主要章节标题和内容概要。

请严格按以下JSON格式输出，不要有任何额外文字：
{
  "doc_type": "comprehensive/subsidy/certification/talent/tax/tech/finance/land/other",
  "doc_type_reason": "判断理由",
  "policy_level": "国家级/省级/市级/区级/其他",
  "outline": [
    {"section_title": "章节标题", "content_preview": "该章节核心内容摘要（50字以内）", "section_index": 0},
    ...
  ],
  "custom_fields": [
    {"name": "字段名", "description": "这个字段提取什么信息", "source_section": "来源章节"},
    ...
  ],
  "has_attachments": true/false,
  "attachment_hints": ["附件提示信息"]
}"""


EXTRACTION_SYSTEM_PROMPT_TEMPLATE = """你是一个专业的政府政策文件结构化提取专家。

当前分析的文档类型是：{doc_type}（{doc_type_reason}）
政策级别：{policy_level}

请从以下政策文本中提取关键信息，返回标准JSON格式。

{dynamic_fields_instruction}

基础提取要求：
1. 所有日期请格式化为 YYYY-MM-DD，如果只有年份则填YYYY-01-01，如果只有年月则填YYYY-MM-01
2. 金额数字请保留原始数值，注明单位（万元/元/比例等）
3. 条件描述请完整保留原文措辞
4. 如果某字段在文本中找不到对应信息，该字段返回null或空列表，不要编造
5. 识别并提取所有申报对象、支持标准、申报条件、申报材料、时间节点
6. 如果文档有多个子政策/多条措施（如支持不同类型企业、不同补贴标准），请分别提取

{dynamic_schema_instruction}

请严格按JSON格式输出，只输出JSON，不要有任何其他文字："""


BASE_FIELDS_INSTRUCTION = """基础通用字段（必须提取）：
- policy_name: 政策完整名称
- issuing_body: 发文机关全称
- effective_date: 政策生效日期
- deadline: 申报截止日期（如有）
- summary: 政策核心内容摘要（200字以内）
- eligible_objects: 申报对象列表（每个对象需包含名称和简要说明）
- support_standards: 支持标准/补贴标准列表
- application_conditions: 申报条件列表
- application_materials: 申报材料列表
- application_method: 申报方式说明
- consultation: 联系方式（包含contact和website）
- time_nodes: 时间节点列表
- key_requirements: 关键要求/特别注意事项列表"""


TYPE_SPECIFIC_INSTRUCTIONS = {
    "comprehensive": """
【综合性政策额外要求】
- 识别文档中包含的多个子政策或措施
- 分别列出每个子政策的申报对象和补贴标准
- 识别各子政策之间的关系（并行/包含/补充）
""",
    "subsidy": """
【单一补贴政策额外要求】
- 明确补贴类型（研发补贴/设备补贴/贷款贴息等）
- 明确补贴计算方式（固定金额/比例/一事一议）
- 识别补贴上限和下限
- 识别补贴发放方式（先到先得/评审发放/一次性发放）
""",
    "certification": """
【认定类政策额外要求】
- 明确认定等级或类别（如国家级/省级/AAA级等）
- 列出完整的认定条件（分项列出）
- 识别认定有效期和复审要求
- 识别认定后可享受的优惠政策
""",
    "talent": """
【人才类政策额外要求】
- 识别人才层次/类别（如高层次人才/青年人才/技能人才）
- 列出各层次人才的认定标准
- 识别各类人才的专项支持政策（科研经费/住房补贴/子女入学等）
- 识别人才服务窗口或专人对接机制
""",
    "tax": """
【税收优惠政策额外要求】
- 明确优惠类型（免税/减半征收/加计扣除/税前扣除等）
- 明确适用税种（增值税/企业所得税/个人所得税等）
- 识别优惠计算方式或比例
- 识别优惠申请方式和时间要求
""",
    "tech": """
【科技类政策额外要求】
- 识别支持的科技项目类别（研发项目/成果转化/平台建设等）
- 明确研发费用的归集范围和比例要求
- 识别科技评价指标体系
- 识别产学研合作的相关要求
""",
    "finance": """
【金融支持政策额外要求】
- 明确支持的贷款类型（信用贷款/抵押贷款/担保贷款等）
- 识别贷款额度和期限
- 明确贴息比例或担保费补贴标准
- 识别申请条件和流程
""",
    "land": """
【用地支持政策额外要求】
- 明确支持方式（低价出让/租金减免/免费使用等）
- 识别用地规模和条件
- 识别入驻园区或载体要求
- 识别申请流程和审核标准
""",
    "other": """
【其他类型政策】
- 根据实际内容灵活提取关键信息
- 识别该政策最核心的3-5个要点
- 列出申报条件和享受优惠的主要群体
"""
}


def _build_dynamic_instruction(doc_type: str, custom_fields: list) -> str:
    type_instruction = TYPE_SPECIFIC_INSTRUCTIONS.get(doc_type, TYPE_SPECIFIC_INSTRUCTIONS["other"])

    dynamic_instruction = ""
    if custom_fields:
        dynamic_instruction = "\n【本文件特有字段】\n"
        for cf in custom_fields:
            dynamic_instruction += f"- {cf['name']}: {cf['description']}（来源：{cf['source_section']}）\n"

    return BASE_FIELDS_INSTRUCTION + type_instruction + dynamic_instruction


def _analyze_document_structure(text: str) -> dict:
    """阶段1: 分析文档结构，识别文档类型和章节大纲"""
    sample_text = text[:8000]

    result = structured_extraction(
        prompt=f"请分析以下政策文档的结构和类型：\n\n{sample_text}",
        system_prompt=DOC_TYPE_SYSTEM_PROMPT,
        json_schema={}
    )

    if result.get("error"):
        return {
            "doc_type": "comprehensive",
            "doc_type_reason": "无法自动识别，使用默认类型",
            "policy_level": "未知",
            "outline": [],
            "custom_fields": [],
            "has_attachments": False,
            "attachment_hints": []
        }

    return result


def _extract_base_info(text: str, doc_info: dict) -> dict:
    """阶段2a: 提取基础通用信息"""
    dynamic_instruction = _build_dynamic_instruction(
        doc_info.get("doc_type", "comprehensive"),
        doc_info.get("custom_fields", [])
    )

    system_prompt = EXTRACTION_SYSTEM_PROMPT_TEMPLATE.format(
        doc_type=doc_info.get("doc_type", "comprehensive"),
        doc_type_reason=doc_info.get("doc_type_reason", ""),
        policy_level=doc_info.get("policy_level", "未知"),
        dynamic_fields_instruction=dynamic_instruction,
        dynamic_schema_instruction=""
    )

    sample_text = text[:15000]

    result = structured_extraction(
        prompt=f"请提取以下政策文件的关键信息：\n\n{sample_text}",
        system_prompt=system_prompt,
        json_schema={}
    )

    return result


def _extract_sub_policies(text: str, doc_info: dict) -> list[dict]:
    """阶段2b: 提取文档中的多个子政策/措施（如果存在）"""
    sub_policies_text = text[:20000]

    messages = [
        {"role": "system", "content": """你是一个专业的政府政策文件分析专家。
这份政策文档可能包含多个子政策或多项措施。请识别并提取每个子政策的详细信息。

对于每个子政策/措施，请提取：
- sub_policy_name: 子政策/措施的名称
- target_objects: 该子政策面向的对象
- support_content: 支持内容（补贴金额/优惠措施等）
- conditions: 该子政策的申报条件
- materials: 该子政策需要的申报材料
- timeline: 时间节点（如有）
- relationship: 与其他子政策的关系（独立/递进/并行）

如果没有多个子政策，请返回单个对象的列表。

请严格按JSON格式输出：
{
  "sub_policies": [
    {...}, ...
  ]
}"""},
        {"role": "user", "content": f"请分析以下政策文档中的子政策或多项措施：\n\n{sub_policies_text}"}
    ]

    response = chat_completion(messages, temperature=0.1)
    content = response.choices[0].message.content

    match = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
    if match:
        content = match.group(1).strip()

    try:
        start = content.index("{")
        end = content.rindex("}") + 1
        data = json.loads(content[start:end])
        return data.get("sub_policies", [])
    except (ValueError, json.JSONDecodeError):
        return []


def _extract_by_sections(text: str, doc_info: dict, outline: list) -> list[dict]:
    """阶段2c: 逐章节提取（针对章节结构清晰的文档）"""
    if len(outline) < 3:
        return []

    section_results = []

    for section in outline[:8]:
        section_title = section.get("section_title", "")
        if not section_title:
            continue

        section_text = _find_section_text(text, section_title)
        if len(section_text) < 50:
            continue

        dynamic_instruction = _build_dynamic_instruction(
            doc_info.get("doc_type", "comprehensive"),
            doc_info.get("custom_fields", [])
        )

        messages = [
            {"role": "system", "content": f"""你是一个专业的政府政策文件结构化提取专家。
当前提取的章节是：{section_title}
政策类型：{doc_info.get('doc_type', 'comprehensive')}
政策级别：{doc_info.get('policy_level', '未知')}

请从这一章节中提取与该章节主题相关的所有结构化信息。
{dynamic_instruction}

请严格按JSON格式输出，只输出JSON："""},
            {"role": "user", "content": f"请从以下章节文本中提取信息：\n\n{section_text[:6000]}"}
        ]

        result = structured_extraction(
            prompt="",
            system_prompt="\n".join([m["content"] for m in messages if m["role"] == "system"]),
            json_schema={}
        )

        if not result.get("error"):
            result["_section_source"] = section_title
            section_results.append(result)

    return section_results


def _find_section_text(text: str, section_title: str) -> str:
    """在原文中查找指定章节的完整文本"""
    lines = text.split("\n")

    start_idx = -1
    for i, line in enumerate(lines):
        if section_title in line or line.strip().startswith(section_title[:4]):
            start_idx = i
            break

    if start_idx == -1:
        return ""

    result_lines = []
    for line in lines[start_idx:]:
        result_lines.append(line)
        if len("\n".join(result_lines)) > 3000:
            break

    return "\n".join(result_lines)


def _merge_and_deduplicate(results: list[dict]) -> dict:
    """合并多个提取结果，去重"""
    if not results:
        return {}

    merged = {}

    for result in results:
        if result.get("error"):
            continue

        for key, value in result.items():
            if key.startswith("_") or key == "error":
                continue

            if value is None or value == "":
                continue

            if key not in merged:
                merged[key] = value
            else:
                merged[key] = _merge_field(key, merged[key], value)

    return merged


def _merge_field(key: str, existing: Any, new: Any) -> Any:
    """根据字段类型合并值"""
    if isinstance(existing, list) and isinstance(new, list):
        if key in ["eligible_objects", "application_conditions", "application_materials",
                   "key_requirements", "time_nodes", "support_standards"]:
            seen = set()
            combined = []
            for item in (existing + new):
                item_key = str(item)
                if item_key not in seen:
                    seen.add(item_key)
                    combined.append(item)
            return combined
        else:
            return existing if existing else new
    else:
        return existing if existing else new


class PolicyExtractorV2:
    """
    灵活政策解析器 - LLM原生解析，不依赖RAG分块

    核心思路：
    1. 阶段1: 用LLM分析文档结构，识别文档类型和章节大纲
    2. 阶段2a: 提取基础通用字段
    3. 阶段2b: 识别并提取多个子政策（如有）
    4. 阶段2c: 逐章节精确提取（可选，针对章节结构清晰的文档）
    5. 合并+去重+构建图谱节点
    """

    def __init__(self):
        self.phase1_model = None
        self.phase2_model = None

    def extract(self, raw_text: str, policy_id: str = None) -> dict:
        """
        对一份政策文档进行完整解析

        Args:
            raw_text: 文档原始文本
            policy_id: 政策ID（用于关联）

        Returns:
            dict: 包含提取结果的字典
        """
        if not raw_text or len(raw_text.strip()) < 100:
            return {"error": "文本内容不足", "data": {}}

        doc_id = policy_id or str(uuid.uuid4())

        doc_info = _analyze_document_structure(raw_text)
        doc_type = doc_info.get("doc_type", "comprehensive")

        base_result = _extract_base_info(raw_text, doc_info)
        base_result["_section_source"] = "全文提取"

        sub_policies = _extract_sub_policies(raw_text, doc_info)

        outline = doc_info.get("outline", [])
        section_results = _extract_by_sections(raw_text, doc_info, outline) if outline else []

        all_results = [base_result] + section_results
        merged = _merge_and_deduplicate(all_results)

        merged["policy_id"] = doc_id
        merged["doc_type"] = doc_type
        merged["doc_type_reason"] = doc_info.get("doc_type_reason", "")
        merged["policy_level"] = doc_info.get("policy_level", "未知")
        merged["sub_policies"] = sub_policies
        merged["has_attachments"] = doc_info.get("has_attachments", False)
        merged["attachment_hints"] = doc_info.get("attachment_hints", [])
        merged["confidence"] = self._calculate_confidence(merged, sub_policies)

        return merged

    def _calculate_confidence(self, merged: dict, sub_policies: list) -> float:
        """计算提取置信度"""
        score = 0.0

        base_fields = ["policy_name", "issuing_body"]
        for field in base_fields:
            if merged.get(field):
                score += 0.15

        list_fields = ["eligible_objects", "application_conditions", "application_materials"]
        for field in list_fields:
            val = merged.get(field)
            if isinstance(val, list) and len(val) > 0:
                score += 0.1

        if merged.get("support_standards"):
            score += 0.1

        if merged.get("time_nodes"):
            score += 0.05

        if sub_policies:
            score += 0.1

        return min(score, 1.0)

    def extract_to_graph_nodes(self, extracted: dict) -> dict:
        """
        将提取结果转换为知识图谱节点

        Returns:
            dict: 包含 nodes 和 edges 的字典
        """
        nodes = []
        edges = []
        policy_id = extracted.get("policy_id", str(uuid.uuid4()))

        policy_node = {
            "id": policy_id,
            "type": "Policy",
            "name": extracted.get("policy_name", ""),
            "issuing_body": extracted.get("issuing_body", ""),
            "policy_type": extracted.get("doc_type", ""),
            "policy_level": extracted.get("policy_level", ""),
            "effective_date": extracted.get("effective_date", ""),
            "deadline": extracted.get("deadline", ""),
            "summary": extracted.get("summary", ""),
        }
        nodes.append(policy_node)

        for obj in (extracted.get("eligible_objects") or []):
            if isinstance(obj, dict):
                obj_name = obj.get("name") or str(obj)
                obj_desc = obj.get("description", "")
            else:
                obj_name = str(obj)
                obj_desc = ""
            node_id = f"{policy_id}_obj_{uuid.uuid4().hex[:8]}"
            nodes.append({
                "id": node_id,
                "type": "ApplicantObject",
                "name": obj_name,
                "description": obj_desc,
                "policy_id": policy_id,
            })
            edges.append({
                "source": policy_id,
                "target": node_id,
                "relation": "APPLIES_TO",
            })

        for condition in (extracted.get("application_conditions") or []):
            node_id = f"{policy_id}_cond_{uuid.uuid4().hex[:8]}"
            cond_text = condition.get("content") if isinstance(condition, dict) else str(condition)
            nodes.append({
                "id": node_id,
                "type": "Condition",
                "name": cond_text[:200],
                "policy_id": policy_id,
            })
            edges.append({
                "source": policy_id,
                "target": node_id,
                "relation": "REQUIRES",
            })

        for material in (extracted.get("application_materials") or []):
            node_id = f"{policy_id}_mat_{uuid.uuid4().hex[:8]}"
            mat_text = material.get("name") if isinstance(material, dict) else str(material)
            nodes.append({
                "id": node_id,
                "type": "Material",
                "name": mat_text[:200],
                "policy_id": policy_id,
            })
            edges.append({
                "source": policy_id,
                "target": node_id,
                "relation": "NEEDS",
            })

        for std in (extracted.get("support_standards") or []):
            if not isinstance(std, dict):
                continue
            node_id = f"{policy_id}_sub_{uuid.uuid4().hex[:8]}"
            nodes.append({
                "id": node_id,
                "type": "Subsidy",
                "name": std.get("type", ""),
                "amount": std.get("amount", ""),
                "max_amount": std.get("max_amount", ""),
                "unit": std.get("unit", ""),
                "policy_id": policy_id,
            })
            edges.append({
                "source": policy_id,
                "target": node_id,
                "relation": "PROVIDES",
            })

        for node in (extracted.get("time_nodes") or []):
            if not isinstance(node, dict):
                continue
            node_id = f"{policy_id}_time_{uuid.uuid4().hex[:8]}"
            nodes.append({
                "id": node_id,
                "type": "TimelineNode",
                "date": node.get("date", ""),
                "node_type": node.get("type", ""),
                "description": node.get("description", ""),
                "policy_id": policy_id,
            })
            edges.append({
                "source": policy_id,
                "target": node_id,
                "relation": "HAS_TIMELINE",
            })

        for sp in (extracted.get("sub_policies") or []):
            sp_name = sp.get("sub_policy_name", "") or sp.get("name", "")
            if not sp_name:
                continue
            sp_id = f"{policy_id}_subpol_{uuid.uuid4().hex[:8]}"
            nodes.append({
                "id": sp_id,
                "type": "SubPolicy",
                "name": sp_name,
                "target_objects": sp.get("target_objects", ""),
                "support_content": sp.get("support_content", ""),
                "policy_id": policy_id,
            })
            edges.append({
                "source": policy_id,
                "target": sp_id,
                "relation": "CONTAINS_SUB",
            })

        return {"nodes": nodes, "edges": edges}

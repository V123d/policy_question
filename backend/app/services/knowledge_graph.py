import json
import uuid
import re
from pathlib import Path
from typing import Any, Optional
from app.services.llm import chat_completion


class PolicyKnowledgeGraph:
    """
    政策知识图谱 - 基于 NetworkX 构建主文件与附件之间的关系

    核心能力:
    1. 从结构化提取结果构建图谱节点和边
    2. 支持附件与主政策的自动关联
    3. 基于用户问题的实体识别和多跳查询
    4. 图谱持久化（JSON快照）和恢复
    """

    def __init__(self):
        self.attachment_dir = Path(__file__).resolve().parent.parent.parent.parent / "data" / "attachments"
        self.attachment_dir.mkdir(parents=True, exist_ok=True)
        self._graph_data = {"nodes": [], "edges": []}
        self._loaded = False

    def load_from_db(self, nodes: list[dict], edges: list[dict]) -> None:
        """从数据库加载图谱数据"""
        self._graph_data = {"nodes": nodes or [], "edges": edges or []}
        self._loaded = True

    def add_policy_nodes(self, nodes: list[dict], edges: list[dict]) -> None:
        """添加政策节点和边到图谱"""
        existing_node_ids = {n["id"] for n in self._graph_data["nodes"]}
        for node in nodes:
            if node["id"] not in existing_node_ids:
                self._graph_data["nodes"].append(node)
                existing_node_ids.add(node["id"])

        existing_edge_ids = set()
        for edge in self._graph_data["edges"]:
            edge_key = f"{edge['source']}_{edge['target']}_{edge['relation']}"
            existing_edge_ids.add(edge_key)

        for edge in edges:
            edge_key = f"{edge['source']}_{edge['target']}_{edge['relation']}"
            if edge_key not in existing_edge_ids:
                self._graph_data["edges"].append(edge)

    def remove_policy(self, policy_id: str) -> None:
        """删除某个政策相关的所有节点和边"""
        self._graph_data["nodes"] = [
            n for n in self._graph_data["nodes"]
            if n.get("policy_id") != policy_id and n["id"] != policy_id
        ]
        self._graph_data["edges"] = [
            e for e in self._graph_data["edges"]
            if e["source"] != policy_id and e["target"] != policy_id
        ]

    def get_policy_subgraph(self, policy_id: str) -> dict:
        """获取某个政策的完整子图"""
        subgraph_nodes = [n for n in self._graph_data["nodes"]
                         if n["id"] == policy_id or n.get("policy_id") == policy_id]
        node_ids = {n["id"] for n in subgraph_nodes}

        subgraph_edges = []
        for e in self._graph_data["edges"]:
            if e["source"] in node_ids or e["target"] in node_ids:
                subgraph_edges.append(e)
                node_ids.add(e["source"])
                node_ids.add(e["target"])

        full_nodes = [n for n in self._graph_data["nodes"] if n["id"] in node_ids]

        return {"nodes": full_nodes, "edges": subgraph_edges}

    def get_full_graph(self) -> dict:
        """获取完整图谱"""
        return self._graph_data

    def query_by_question(self, question: str) -> dict:
        """
        根据用户问题进行图谱检索

        步骤:
        1. LLM识别问题中的实体(申报对象/政策类型/金额/时间等)
        2. 在图谱中匹配相关节点
        3. 返回关联的政策及其子图
        """
        entity_result = self._extract_entities(question)
        entities = entity_result.get("entities", [])
        query_intent = entity_result.get("intent", "")

        if not entities:
            return {
                "matched_policies": [],
                "matched_nodes": [],
                "entities": [],
                "intent": query_intent,
                "context": ""
            }

        matched_nodes = []
        matched_policy_ids = set()

        for entity in entities:
            entity_type = entity.get("type", "")
            entity_value = entity.get("value", "")

            if not entity_value:
                continue

            for node in self._graph_data["nodes"]:
                node_type = node.get("type", "")
                node_name = node.get("name", "")

                if entity_type == "ApplicantObject":
                    if node_type == "ApplicantObject" and entity_value in node_name:
                        matched_nodes.append(node)
                        matched_policy_ids.add(node.get("policy_id"))

                elif entity_type == "PolicyType":
                    if node_type == "Policy" and entity_value in node.get("policy_type", ""):
                        matched_nodes.append(node)
                        matched_policy_ids.add(node["id"])

                elif entity_type == "PolicyLevel":
                    if node_type == "Policy" and entity_value in node.get("policy_level", ""):
                        matched_nodes.append(node)
                        matched_policy_ids.add(node["id"])

                elif entity_type == "Money":
                    if node_type == "Subsidy":
                        amount_str = str(node.get("amount", "")) + str(node.get("max_amount", ""))
                        if entity_value in amount_str or entity_value in node_name:
                            matched_nodes.append(node)
                            matched_policy_ids.add(node.get("policy_id"))

                elif entity_type == "Time":
                    if node_type == "TimelineNode":
                        if entity_value in node.get("date", ""):
                            matched_nodes.append(node)
                            matched_policy_ids.add(node.get("policy_id"))

                elif entity_type == "SubsidyType":
                    if node_type == "Subsidy" and entity_value in node_name:
                        matched_nodes.append(node)
                        matched_policy_ids.add(node.get("policy_id"))

                elif entity_type == "Condition":
                    if node_type == "Condition" and entity_value in node.get("name", ""):
                        matched_nodes.append(node)
                        matched_policy_ids.add(node.get("policy_id"))

        matched_policies = []
        for pid in matched_policy_ids:
            policy_node = next((n for n in self._graph_data["nodes"] if n["id"] == pid), None)
            if policy_node:
                subgraph = self.get_policy_subgraph(pid)
                matched_policies.append({
                    "policy": policy_node,
                    "subgraph": subgraph
                })

        if not matched_policies:
            keyword = entities[0].get("value", "") if entities else ""
            for node in self._graph_data["nodes"]:
                if node["type"] == "Policy" and keyword in node.get("name", ""):
                    subgraph = self.get_policy_subgraph(node["id"])
                    matched_policies.append({"policy": node, "subgraph": subgraph})
                    break

        return {
            "matched_policies": matched_policies,
            "matched_nodes": matched_nodes[:20],
            "entities": entities,
            "intent": query_intent,
            "context": self._build_context(matched_policies)
        }

    def query_by_policy(self, policy_id: str) -> dict:
        """查询某个政策的完整信息"""
        subgraph = self.get_policy_subgraph(policy_id)
        nodes = subgraph["nodes"]
        edges = subgraph["edges"]

        policy_node = next((n for n in nodes if n["id"] == policy_id), None)

        applicant_objects = [n for n in nodes if n["type"] == "ApplicantObject"]
        conditions = [n for n in nodes if n["type"] == "Condition"]
        materials = [n for n in nodes if n["type"] == "Material"]
        subsidies = [n for n in nodes if n["type"] == "Subsidy"]
        timeline_nodes = [n for n in nodes if n["type"] == "TimelineNode"]
        sub_policies = [n for n in nodes if n["type"] == "SubPolicy"]
        attachments = [n for n in nodes if n["type"] == "Attachment"]

        return {
            "policy": policy_node,
            "applicant_objects": applicant_objects,
            "conditions": conditions,
            "materials": materials,
            "subsidies": subsidies,
            "timeline_nodes": timeline_nodes,
            "sub_policies": sub_policies,
            "attachments": attachments,
            "edges": edges
        }

    def link_attachment(
        self,
        attachment_info: dict,
        parent_policy_id: Optional[str] = None
    ) -> dict:
        """
        将附件与主政策关联

        Args:
            attachment_info: 附件信息 {filename, description, file_path}
            parent_policy_id: 已知的主政策ID（可选）

        Returns:
            关联结果，包含创建的节点和边
        """
        attachment_id = str(uuid.uuid4())
        description = attachment_info.get("description", "")
        filename = attachment_info.get("filename", "")

        attachment_node = {
            "id": attachment_id,
            "type": "Attachment",
            "name": filename,
            "description": description,
            "file_path": attachment_info.get("file_path", ""),
            "parent_policy_id": parent_policy_id,
        }

        edges = []

        if parent_policy_id:
            edges.append({
                "source": parent_policy_id,
                "target": attachment_id,
                "relation": "HAS_ATTACHMENT"
            })
        elif description or filename:
            matched_policy = self._find_related_policy(description + " " + filename)
            if matched_policy:
                attachment_node["parent_policy_id"] = matched_policy["id"]
                edges.append({
                    "source": matched_policy["id"],
                    "target": attachment_id,
                    "relation": "HAS_ATTACHMENT"
                })

        self._graph_data["nodes"].append(attachment_node)
        for edge in edges:
            self._graph_data["edges"].append(edge)

        return {
            "attachment_node": attachment_node,
            "edges": edges,
            "linked": parent_policy_id is not None or len(edges) > 0
        }

    def _find_related_policy(self, text: str) -> Optional[dict]:
        """通过文本匹配找到相关政策"""
        text_lower = text.lower()

        for node in self._graph_data["nodes"]:
            if node["type"] != "Policy":
                continue

            policy_name = node.get("name", "").lower()
            if policy_name in text_lower or text_lower in policy_name:
                return node

        keywords = ["认定", "补贴", "资助", "奖励", "优惠", "支持", "申报", "科技", "人才", "创新"]
        for keyword in keywords:
            if keyword in text:
                for node in self._graph_data["nodes"]:
                    if node["type"] == "Policy" and keyword in node.get("name", ""):
                        return node

        return None

    def _extract_entities(self, question: str) -> dict:
        """使用LLM从问题中提取实体"""
        messages = [
            {"role": "system", "content": """你是一个政策问答系统的实体识别专家。
从用户问题中提取以下类型的实体：

- ApplicantObject: 申报对象，如"科技型中小企业"、"高新技术企业"、"个体工商户"等
- PolicyType: 政策类型，如"补贴"、"认定"、"奖励"、"税收优惠"、"人才政策"等
- PolicyLevel: 政策级别，如"国家级"、"省级"、"市级"、"区县级"等
- Money: 涉及的资金金额，如"50万元"、"100万"等
- Time: 时间信息，如"2024年"、"3月份"、"上半年"等
- SubsidyType: 补贴类型，如"研发补贴"、"设备补贴"、"贷款贴息"、"房租补贴"等
- Condition: 申报条件关键词，如"研发费用"、"营业收入"、"知识产权"等

请按以下JSON格式输出：
{
  "entities": [
    {"type": "实体类型", "value": "实体值", "position": "问题中的原文"},
    ...
  ],
  "intent": "用户意图概括，如'查询补贴政策'、'了解申报条件'等"
}

如果某类型实体不存在，可以省略该实体的列表项。"""},
            {"role": "user", "content": question}
        ]

        response = chat_completion(messages, temperature=0.1)
        content = response.choices[0].message.content

        match = re.search(r"```(?:json)?\s*(.*?)```", content, re.DOTALL)
        if match:
            content = match.group(1).strip()

        try:
            start = content.index("{")
            end = content.rindex("}") + 1
            return json.loads(content[start:end])
        except (ValueError, json.JSONDecodeError):
            return {"entities": [], "intent": ""}

    def _build_context(self, matched_policies: list[dict]) -> str:
        """将匹配的政策构建为问答上下文"""
        if not matched_policies:
            return ""

        context_parts = []

        for item in matched_policies:
            policy = item.get("policy", {})
            subgraph = item.get("subgraph", {})
            nodes = subgraph.get("nodes", [])
            edges = subgraph.get("edges", [])

            part = [f"【{policy.get('name', '未知政策')}】"]
            part.append(f"发文机关: {policy.get('issuing_body', '未知')}")
            part.append(f"政策类型: {policy.get('policy_type', '未知')}")

            applicant_objects = [n for n in nodes if n["type"] == "ApplicantObject"]
            if applicant_objects:
                obj_names = "、".join(n["name"] for n in applicant_objects[:5])
                part.append(f"申报对象: {obj_names}")

            subsidies = [n for n in nodes if n["type"] == "Subsidy"]
            if subsidies:
                sub_parts = []
                for s in subsidies[:5]:
                    amount = s.get("amount", "") or s.get("max_amount", "")
                    unit = s.get("unit", "")
                    name = s.get("name", "")
                    sub_parts.append(f"{name}{amount}{unit}".strip())
                part.append(f"支持标准: {'；'.join(sub_parts)}")

            conditions = [n for n in nodes if n["type"] == "Condition"]
            if conditions:
                cond_names = "；".join(n["name"][:50] for n in conditions[:5])
                part.append(f"申报条件: {cond_names}")

            materials = [n for n in nodes if n["type"] == "Material"]
            if materials:
                mat_names = "、".join(n["name"] for n in materials[:5])
                part.append(f"申报材料: {mat_names}")

            timeline = [n for n in nodes if n["type"] == "TimelineNode"]
            if timeline:
                timeline_str = "；".join(f"{n.get('date','')}{n.get('node_type','')}" for n in timeline[:5])
                part.append(f"时间节点: {timeline_str}")

            attachments = [n for n in nodes if n["type"] == "Attachment"]
            if attachments:
                att_names = "、".join(n["name"] for n in attachments)
                part.append(f"相关附件: {att_names}")

            context_parts.append("\n".join(part))

        return "\n\n---\n\n".join(context_parts)

    def to_json(self) -> str:
        """序列化为JSON字符串"""
        return json.dumps(self._graph_data, ensure_ascii=False, indent=2)

    def from_json(self, json_str: str) -> None:
        """从JSON字符串恢复"""
        try:
            self._graph_data = json.loads(json_str)
            self._loaded = True
        except json.JSONDecodeError:
            self._graph_data = {"nodes": [], "edges": []}

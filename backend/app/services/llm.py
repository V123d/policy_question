import dashscope
from dashscope import TextEmbedding, Generation
from app.config import settings

dashscope.api_key = settings.DASHSCOPE_API_KEY


def get_embedding(text: str, model: str = None) -> list[float]:
    model = model or settings.EMBEDDING_MODEL
    text = text.replace("\n", " ")[:8000]

    response = TextEmbedding.call(model=model, input=text)

    if response.status_code != 200:
        raise RuntimeError(f"嵌入调用失败: {response.message}")

    embedding = response.output["embeddings"][0]["embedding"]
    return embedding


def chat_completion(
    messages: list[dict],
    model: str = None,
    temperature: float = 0.3,
    stream: bool = False
):
    model = model or settings.LLM_MODEL

    if stream:
        return _stream_response(model, messages, temperature)
    else:
        response = Generation.call(
            model=model,
            messages=messages,
            temperature=temperature,
            stream=False,
            result_format="message",
            max_tokens=4096,
            stop=["```", "\n\n---\n\n问题", "根据您提供的政策文本片段", "[来源："],
        )

        if response.status_code != 200:
            raise RuntimeError(f"LLM 调用失败: {response.message}")

        content = ""
        if response.output and hasattr(response.output, "choices") and response.output.choices:
            msg = response.output.choices[0].message
            content = getattr(msg, "content", "") or ""
            if isinstance(content, dict):
                content = content.get("content", "") or ""

        class FakeResponse:
            def __init__(self, c):
                self.choices = [self._Choice(c)]

            class _Choice:
                def __init__(self, c):
                    self.message = self._Message(c)

                class _Message:
                    def __init__(self, c):
                        self.content = c

        return FakeResponse(content)


def _stream_response(model: str, messages: list[dict], temperature: float):
    gen = Generation.call(
        model=model,
        messages=messages,
        temperature=temperature,
        stream=True,
        result_format="message",
        max_tokens=4096,
        stop=["```", "\n\n---\n\n问题", "根据您提供的政策文本片段", "[来源："],
    )

    class ChunkIterator:
        def __init__(self, gen):
            self.gen = gen
            self._last_content = ""
            self.chunk_class = type("Chunk", (), {
                "choices": [type("Choice", (), {
                    "delta": type("Delta", (), {"content": ""})()
                })()]
            })

        def __iter__(self):
            return self

        def __next__(self):
            try:
                rsp = next(self.gen)
                if rsp is None or rsp.status_code != 200:
                    raise StopIteration

                chunk = self.chunk_class()
                raw_content = ""
                if rsp.output and hasattr(rsp.output, "choices") and rsp.output.choices:
                    msg = rsp.output.choices[0].message
                    raw = getattr(msg, "content", "") or ""
                    if isinstance(raw, dict):
                        raw = raw.get("content", "") or ""
                    raw_content = raw

                delta = raw_content[len(self._last_content):]
                self._last_content = raw_content
                chunk.choices[0].delta.content = delta
                return chunk
            except StopIteration:
                raise
            except Exception:
                raise StopIteration

    return ChunkIterator(gen)


def structured_extraction(prompt: str, system_prompt: str, json_schema: dict):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt}
    ]

    response = Generation.call(
        model=settings.LLM_MODEL,
        messages=messages,
        temperature=0.1,
        result_format="message"
    )

    if response.status_code != 200:
        raise RuntimeError(f"LLM 调用失败: {response.message}")

    content = ""
    if response.output and hasattr(response.output, "choices") and response.output.choices:
        msg = response.output.choices[0].message
        raw = getattr(msg, "content", "") or ""
        if isinstance(raw, dict):
            raw = raw.get("content", "") or ""
        content = raw

    if not content or not content.strip():
        return {"error": "LLM 返回内容为空"}

    import json, re
    text = content.strip()

    # 尝试从 markdown 代码块中提取 JSON
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 如果仍然不是纯 JSON，尝试在文本中找 JSON 对象
        try:
            # 找第一个 { 到最后一个 } 之间的内容
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return {"error": f"无法解析 LLM 返回为 JSON: {text[:200]}"}


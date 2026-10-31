"""Thin Muse Spark client: one JSON-in/JSON-out call through Meta's OpenAI-compatible API."""

import base64
import json
import re

from .models import ModelResponseError

DEFAULT_BASE_URL = "https://api.meta.ai/v1"
DEFAULT_MODEL = "muse-spark-1.3"
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_json_object(text: str) -> dict:
    cleaned = _FENCE.sub("", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end < start:
        raise ModelResponseError("Model output contained no JSON object")
    try:
        value = json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError as error:
        raise ModelResponseError(f"Model output was not valid JSON: {error}") from error
    if not isinstance(value, dict):
        raise ModelResponseError("Model output JSON was not an object")
    return value


class MuseClient:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL,
                 base_url: str = DEFAULT_BASE_URL, client=None):
        if client is None:
            from openai import OpenAI
            client = OpenAI(base_url=base_url, api_key=api_key)
        self._client = client
        self.model = model

    def generate_json(self, instructions: str, payload: dict,
                      images: list[bytes] | None = None) -> dict:
        content = json.dumps(payload, ensure_ascii=False)
        if images:
            parts = [{"type": "input_text", "text": content}]
            parts += [{"type": "input_image",
                       "image_url": f"data:image/jpeg;base64,{base64.b64encode(image).decode()}"}
                      for image in images]
            content = [{"role": "user", "content": parts}]
        try:
            response = self._client.responses.create(
                model=self.model, instructions=instructions, input=content)
        except Exception as error:
            raise ModelResponseError(f"Muse Spark request failed: {error}") from error
        return parse_json_object(response.output_text)

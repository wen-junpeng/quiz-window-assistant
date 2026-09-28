from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from .prompt import SYSTEM_PROMPT


class ApiError(RuntimeError):
    """A user-facing API configuration or request failure."""


@dataclass(frozen=True)
class ApiSettings:
    base_url: str
    api_key: str
    model: str

    def validate(self) -> None:
        if not self.base_url.strip():
            raise ApiError("请填写 API 地址")
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ApiError("API 地址必须使用有效的 HTTP/HTTPS 地址")
        if not self.api_key.strip():
            raise ApiError("请填写 API Key")
        if not self.model.strip():
            raise ApiError("请填写模型名")


def normalize_endpoint(base_url: str) -> str:
    cleaned = base_url.strip().rstrip("/")
    if cleaned.endswith("/chat/completions"):
        return cleaned
    return f"{cleaned}/chat/completions"


def build_payload(
    settings: ApiSettings, image_data_url: str, instruction: str
) -> dict:
    supplement = instruction.strip() or "请识别并解答截图中的全部明确题目。"
    return {
        "model": settings.model.strip(),
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": supplement},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_data_url},
                    },
                ],
            },
        ],
    }


def _remote_message(response: httpx.Response) -> str:
    try:
        value = response.json().get("error", {}).get("message", "")
    except (ValueError, AttributeError):
        value = ""
    return str(value).strip()[:240]


def solve_question(
    settings: ApiSettings,
    image_data_url: str,
    instruction: str,
    transport: httpx.BaseTransport | None = None,
) -> str:
    settings.validate()
    try:
        with httpx.Client(
            transport=transport,
            timeout=httpx.Timeout(90.0, connect=10.0),
        ) as client:
            response = client.post(
                normalize_endpoint(settings.base_url),
                headers={"Authorization": f"Bearer {settings.api_key}"},
                json=build_payload(settings, image_data_url, instruction),
            )
    except httpx.TimeoutException as exc:
        raise ApiError("请求超时，请稍后重试") from exc
    except httpx.HTTPError as exc:
        raise ApiError("无法连接 API 服务") from exc

    if response.status_code in {401, 403}:
        raise ApiError("API Key 无效或无权限")
    if response.status_code == 429:
        raise ApiError("请求过于频繁，请稍后重试")
    if response.status_code in {400, 422}:
        detail = _remote_message(response) or "模型可能不支持图片输入"
        raise ApiError(detail)
    if response.status_code >= 500:
        raise ApiError(f"服务暂时不可用（HTTP {response.status_code}）")
    if response.is_error:
        raise ApiError(f"API 请求失败（HTTP {response.status_code}）")

    try:
        text = response.json()["choices"][0]["message"]["content"].strip()
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise ApiError("API 返回格式无法识别") from exc
    if not text:
        raise ApiError("模型返回了空响应")
    return text

from __future__ import annotations

import io
import mimetypes
import tempfile
import time
from pathlib import Path

from google import genai
from google.genai import errors, types
from PIL import Image

from app_config import get_app_config_value

VISION_MODELS = (
    "models/gemini-2.5-flash-lite",
)
VISION_MAX_DIMENSION = 1024
VISION_MAX_INLINE_BYTES = 5_500_000


def _build_image_part(image_path: Path) -> types.Part:
    mime_type, _ = mimetypes.guess_type(str(image_path))
    if not mime_type:
        mime_type = "image/png"

    with Image.open(image_path) as img:
        work = img.copy()
    if work.mode not in {"RGB", "L"}:
        work = work.convert("RGB")

    if max(work.size) > VISION_MAX_DIMENSION:
        work.thumbnail((VISION_MAX_DIMENSION, VISION_MAX_DIMENSION), Image.Resampling.LANCZOS)

    png_buffer = io.BytesIO()
    work.save(png_buffer, format="PNG", optimize=True)
    png_bytes = png_buffer.getvalue()
    if len(png_bytes) <= VISION_MAX_INLINE_BYTES:
        return types.Part.from_bytes(data=png_bytes, mime_type="image/png")

    jpg_buffer = io.BytesIO()
    rgb = work.convert("RGB") if work.mode != "RGB" else work
    rgb.save(jpg_buffer, format="JPEG", quality=88, optimize=True)
    return types.Part.from_bytes(data=jpg_buffer.getvalue(), mime_type="image/jpeg")


def _vision_prompt(query: str) -> str:
    user_query = (query or "Bu görüntüdeki nesne nedir?").strip()
    return (
        "Aşağıdaki kameradan çekilmiş görüntüde kullanıcının elindeki ana nesneyi kısa ve net olarak Türkçe yaz.\n"
        "Yanıt sadece ana nesne adını ve gerekiyorsa çok kısa bir açıklamayı içersin.\n"
        f"Kullanıcı sorusu: {user_query}"
    )


def _extract_response_text(response) -> str:
    text = str(getattr(response, "text", "") or "").strip()
    if text:
        return text

    candidates = getattr(response, "candidates", None) or []
    chunks: list[str] = []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            part_text = str(getattr(part, "text", "") or "").strip()
            if part_text:
                chunks.append(part_text)
    return "\n".join(chunk for chunk in chunks if chunk).strip()


def _is_transient_vision_error(exc: Exception) -> bool:
    if isinstance(exc, (errors.ServerError, TimeoutError)):
        return True
    message = str(exc or "").lower()
    transient_markers = (
        "503", "429", "deadline", "timed out", "timeout",
        "unavailable", "service unavailable", "internal error",
        "busy", "overloaded", "resource exhausted", "try again later",
        "backend error", "connection reset",
    )
    return any(marker in message for marker in transient_markers)


def _is_quota_vision_error(exc: Exception) -> bool:
    message = str(exc or "").lower()
    quota_markers = (
        "quota", "rate limit", "resource exhausted",
        "too many requests", "quota exceeded", "limit exceeded", "billing",
    )
    return any(marker in message for marker in quota_markers)


def _friendly_vision_error(exc: Exception) -> str:
    if _is_quota_vision_error(exc):
        return "Gemini vision isteği kota veya hız limitine takıldı. Biraz bekleyip tekrar dene ya da API planını kontrol et."
    if _is_transient_vision_error(exc):
        return "Gemini vision servisi şu anda yoğun veya geçici olarak ulaşılamıyor. Biraz sonra tekrar dene."
    return f"Gemini vision isteği başarısız oldu: {exc}"


def _analyze_with_gemini(query: str, image_path: Path) -> str:
    api_key = str(get_app_config_value("gemini_api_key", "") or "").strip()
    if not api_key:
        return "Gemini API anahtarı eksik olduğu için kamera analizi yapılamadı."

    prompt = _vision_prompt(query)
    client = genai.Client(api_key=api_key)
    image_part = _build_image_part(image_path)
    retry_delays = (0.9,)
    last_error: Exception | None = None

    for model_name in VISION_MODELS:
        for attempt, delay in enumerate(retry_delays, start=1):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        types.Part.from_text(text=prompt),
                        image_part,
                    ],
                    config=types.GenerateContentConfig(temperature=0.0, max_output_tokens=100),
                )
                merged = _extract_response_text(response)
                if merged:
                    return merged
                raise RuntimeError("Gemini geçerli bir görüntü analizi metni döndürmedi.")
            except Exception as exc:
                last_error = exc
                if attempt < len(retry_delays) and _is_transient_vision_error(exc):
                    time.sleep(delay)
                    continue
                if _is_transient_vision_error(exc):
                    break
                raise RuntimeError(_friendly_vision_error(exc)) from exc

    assert last_error is not None
    raise RuntimeError(_friendly_vision_error(last_error))


def identify_camera_object(image_path: str | Path, query: str = "Bu ne?") -> str:
    path = Path(image_path)
    if not path.exists():
        return "Kamera görüntüsü kaydedilemedi veya dosya bulunamadı."
    try:
        return _analyze_with_gemini(query, path)
    except Exception as exc:
        return f"Kamera görüntüsü alındı ama analiz yapılamadı: {exc}"

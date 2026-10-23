"""Model selection that survives provider retirements (Groq retired llama-3.3-70b-versatile on 2026-08-16;
Gemini 2.5 models were scheduled for shutdown on 2026-10-16). Pure functions so they are easy to test."""
import re

GROQ_PREF = ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.6-27b"]
GEMINI_PREF = ["gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest", "gemini-3-flash-preview", "gemini-2.5-flash"]


def pick_groq_model(ids: list[str]) -> str | None:
    for p in GROQ_PREF:
        if p in ids:
            return p
    chat = [i for i in ids if not re.search(r"whisper|tts|guard|embed|orpheus", i)]
    return next((i for i in chat if re.search(r"gpt-oss|qwen|llama", i)), chat[0] if chat else None)


def pick_gemini_model(names: list[str]) -> str | None:
    names = [n.replace("models/", "") for n in names]
    for p in GEMINI_PREF:
        if p in names:
            return p
    flash = [n for n in names if re.fullmatch(r"gemini-[\d.]+-flash", n)]
    flash.sort(key=lambda n: float(n.split("-")[1]), reverse=True)
    if flash:
        return flash[0]
    return next((n for n in names if "gemini" in n and not re.search(r"image|live|tts|audio|embed", n)), None)


def is_model_error(exc: Exception) -> bool:
    status = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)
    text = str(exc).lower()
    return status in (400, 404) or "not found" in text or "decommission" in text or "404" in text

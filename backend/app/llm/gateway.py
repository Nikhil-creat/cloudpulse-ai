"""Dual-engine LLM gateway: Groq (fast tools/chat) + Gemini (deep reasoning/multimodal/long context).

Features: task-aware routing, per-provider circuit breaker, latency timeout + failover,
streaming (failover until first token), token/cost tracking, Redis semantic cache.
"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, Protocol

from app.core.config import get_settings

Message = dict  # {"role": "system|user|assistant", "content": str}

# USD per 1M tokens (input, output). Keep in config/DB in production; values here are placeholders.
PRICES = {"groq": (0.59, 0.79), "gemini": (0.30, 2.50)}
ROUTES = {
    "chat": ("groq", "gemini"),
    "tool_call": ("groq", "gemini"),
    "reasoning": ("gemini", "groq"),
    "long_context": ("gemini", "groq"),
    "multimodal": ("gemini",),
}


def count_tokens(text: str) -> int:
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        return max(1, len(text) // 4)


@dataclass
class LLMResult:
    text: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: int = 0
    cache_hit: bool = False
    failover: bool = False
    cost_usd: float = 0.0


class Provider(Protocol):
    name: str
    model: str
    async def complete(self, messages: list[Message], **kw) -> str: ...
    def stream(self, messages: list[Message], **kw) -> AsyncIterator[str]: ...


class GroqProvider:
    name = "groq"

    def __init__(self, api_key: str, model: str):
        from groq import AsyncGroq
        self.client, self.model = AsyncGroq(api_key=api_key), model

    async def complete(self, messages, **kw) -> str:
        r = await self.client.chat.completions.create(model=self.model, messages=messages,
                                                      temperature=kw.get("temperature", 0.2))
        return r.choices[0].message.content or ""

    async def stream(self, messages, **kw):
        s = await self.client.chat.completions.create(model=self.model, messages=messages, stream=True,
                                                      temperature=kw.get("temperature", 0.2))
        async for ch in s:
            if ch.choices and ch.choices[0].delta.content:
                yield ch.choices[0].delta.content


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.genai, self.model = genai, model

    def _split(self, messages):
        system = "\n".join(m["content"] for m in messages if m["role"] == "system") or None
        contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [m["content"]]}
                    for m in messages if m["role"] != "system"]
        return self.genai.GenerativeModel(self.model, system_instruction=system), contents

    async def complete(self, messages, **kw) -> str:
        model, contents = self._split(messages)
        r = await model.generate_content_async(contents)
        return r.text

    async def stream(self, messages, **kw):
        model, contents = self._split(messages)
        async for chunk in await model.generate_content_async(contents, stream=True):
            if chunk.text:
                yield chunk.text


@dataclass
class Breaker:
    cooldown: float
    failures: int = 0
    open_until: float = 0.0

    def available(self) -> bool:
        return time.monotonic() >= self.open_until

    def fail(self):
        self.failures += 1
        self.open_until = time.monotonic() + self.cooldown * min(self.failures, 4)

    def ok(self):
        self.failures, self.open_until = 0, 0.0


class AllProvidersFailed(RuntimeError):
    pass


@dataclass
class LLMGateway:
    providers: dict
    cache: Optional[object] = None
    on_usage: Optional[object] = None  # async callable(LLMResult, task, user)
    timeout: float = field(default_factory=lambda: get_settings().llm_timeout_s)
    cooldown: float = field(default_factory=lambda: get_settings().breaker_cooldown_s)

    def __post_init__(self):
        self.breakers = {n: Breaker(self.cooldown) for n in self.providers}

    def _order(self, task: str):
        names = [n for n in ROUTES.get(task, ROUTES["chat"]) if n in self.providers]
        live = [n for n in names if self.breakers[n].available()]
        return live or names  # if everything is tripped, still try in order

    @staticmethod
    def _cost(provider: str, pt: int, ct: int) -> float:
        pi, po = PRICES.get(provider, (0, 0))
        return round((pt * pi + ct * po) / 1_000_000, 6)

    @staticmethod
    def _prompt_text(messages) -> str:
        return "\n".join(m["content"] for m in messages)

    async def complete(self, messages, task="chat", use_cache=True, user=None, **kw) -> LLMResult:
        key = self._prompt_text(messages)
        if use_cache and self.cache:
            hit = await self.cache.get(task, key)
            if hit:
                res = LLMResult(cache_hit=True, **hit)
                await self._track(res, task, user)
                return res
        errors, first = [], True
        for name in self._order(task):
            p, t0 = self.providers[name], time.monotonic()
            try:
                text = await asyncio.wait_for(p.complete(messages, **kw), self.timeout)
            except Exception as e:  # rate limit, timeout, 5xx
                self.breakers[name].fail()
                errors.append(f"{name}: {type(e).__name__}")
                first = False
                continue
            self.breakers[name].ok()
            pt, ct = count_tokens(key), count_tokens(text)
            res = LLMResult(text, name, p.model, pt, ct, int((time.monotonic() - t0) * 1000),
                            failover=not first, cost_usd=self._cost(name, pt, ct))
            if use_cache and self.cache:
                await self.cache.put(task, key, {k: v for k, v in res.__dict__.items()
                                                  if k not in ("cache_hit", "latency_ms")}
                                     | {"latency_ms": 0})
            await self._track(res, task, user)
            return res
        raise AllProvidersFailed("; ".join(errors) or "no providers configured")

    async def stream(self, messages, task="chat", user=None, **kw) -> AsyncIterator[str]:
        """Fail over until the first token arrives; after that errors propagate."""
        errors, first = [], True
        prompt = self._prompt_text(messages)
        for name in self._order(task):
            p, t0, buf = self.providers[name], time.monotonic(), []
            agen = p.stream(messages, **kw).__aiter__()
            try:
                chunk = await asyncio.wait_for(agen.__anext__(), self.timeout)
            except StopAsyncIteration:
                self.breakers[name].ok()
                return
            except Exception as e:
                self.breakers[name].fail()
                errors.append(f"{name}: {type(e).__name__}")
                first = False
                continue
            self.breakers[name].ok()
            buf.append(chunk)
            yield chunk
            async for chunk in agen:
                buf.append(chunk)
                yield chunk
            text = "".join(buf)
            pt, ct = count_tokens(prompt), count_tokens(text)
            await self._track(LLMResult(text, name, p.model, pt, ct, int((time.monotonic() - t0) * 1000),
                                        failover=not first, cost_usd=self._cost(name, pt, ct)), task, user)
            return
        raise AllProvidersFailed("; ".join(errors) or "no providers configured")

    async def _track(self, res: LLMResult, task: str, user):
        if self.on_usage:
            try:
                await self.on_usage(res, task, user)
            except Exception:
                pass


def build_gateway(redis, on_usage=None) -> LLMGateway:
    from app.llm.cache import SemanticCache
    s = get_settings()
    providers = {}
    if s.groq_api_key:
        providers["groq"] = GroqProvider(s.groq_api_key, s.groq_model)
    if s.gemini_api_key:
        providers["gemini"] = GeminiProvider(s.gemini_api_key, s.gemini_model)
    cache = SemanticCache(redis, threshold=s.cache_threshold, ttl=s.cache_ttl_s) if redis else None
    return LLMGateway(providers, cache, on_usage)

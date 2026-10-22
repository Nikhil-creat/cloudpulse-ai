import pytest
from app.llm.cache import HashingEmbedder, SemanticCache
from app.llm.gateway import AllProvidersFailed, LLMGateway


class Fake:
    def __init__(self, name, fail=False, text="ok"):
        self.name, self.model, self.fail, self.text = name, f"{name}-m", fail, text

    async def complete(self, messages, **kw):
        if self.fail:
            raise RuntimeError("429")
        return self.text

    async def stream(self, messages, **kw):
        if self.fail:
            raise RuntimeError("429")
        for w in self.text.split():
            yield w


class FakeRedis:
    def __init__(self): self.kv, self.lists = {}, {}
    async def set(self, k, v, ex=None): self.kv[k] = v
    async def mget(self, keys): return [self.kv.get(k) for k in keys]
    async def lpush(self, k, v): self.lists.setdefault(k, []).insert(0, v)
    async def ltrim(self, k, a, b): self.lists[k] = self.lists.get(k, [])[a:b + 1]
    async def lrange(self, k, a, b): return self.lists.get(k, [])[a:b + 1]


MSG = [{"role": "user", "content": "list idle ec2 instances in us-east-1"}]


@pytest.mark.asyncio
async def test_failover_to_gemini():
    gw = LLMGateway({"groq": Fake("groq", fail=True), "gemini": Fake("gemini", text="hello")})
    r = await gw.complete(MSG, task="chat", use_cache=False)
    assert r.provider == "gemini" and r.failover


@pytest.mark.asyncio
async def test_reasoning_prefers_gemini():
    gw = LLMGateway({"groq": Fake("groq"), "gemini": Fake("gemini")})
    assert (await gw.complete(MSG, task="reasoning", use_cache=False)).provider == "gemini"


@pytest.mark.asyncio
async def test_all_fail():
    gw = LLMGateway({"groq": Fake("groq", fail=True)})
    with pytest.raises(AllProvidersFailed):
        await gw.complete(MSG, use_cache=False)


@pytest.mark.asyncio
async def test_semantic_cache_hit():
    gw = LLMGateway({"groq": Fake("groq", text="cached answer")}, cache=SemanticCache(FakeRedis(), threshold=0.9))
    await gw.complete(MSG)
    again = await gw.complete(MSG)
    assert again.cache_hit and again.text == "cached answer"


@pytest.mark.asyncio
async def test_stream_failover():
    gw = LLMGateway({"groq": Fake("groq", fail=True), "gemini": Fake("gemini", text="a b c")})
    assert [c async for c in gw.stream(MSG)] == ["a", "b", "c"]


def test_embedder_similarity():
    e = HashingEmbedder()
    assert float(e.embed("scan s3 buckets") @ e.embed("scan s3 buckets")) > 0.99

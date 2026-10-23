from prometheus_client import Counter, Histogram

LLM_REQUESTS = Counter("cp_llm_requests_total", "LLM requests", ["provider", "task", "cache", "failover"])
LLM_LATENCY = Histogram("cp_llm_latency_seconds", "LLM latency", ["provider"], buckets=(.2, .5, 1, 2, 5, 10, 20))
LLM_COST = Counter("cp_llm_cost_usd_total", "Estimated LLM spend", ["provider"])
LLM_TOKENS = Counter("cp_llm_tokens_total", "Tokens", ["provider", "kind"])
GUARD_BLOCKS = Counter("cp_guard_blocks_total", "Prompts blocked by the LLM firewall", ["reason"])
PLANS = Counter("cp_plans_total", "Execution plans", ["event"])

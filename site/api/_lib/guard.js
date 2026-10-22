'use strict';
// LLM firewall (server side): prompt-injection screening + secret redaction.
const INJECTION = [
  /ignore (all |any |the )?(previous|prior|above|earlier) (instructions|rules|prompts?)/i,
  /(reveal|print|show|repeat) (me )?(your |the )?(system|hidden|initial) (prompt|instructions)/i,
  /you are now (dan|in developer mode|unrestricted)/i,
  /(without|bypass|disable) (any )?(restrictions|guardrails|safety|approval)/i,
  /apply .{0,30}(without|skip).{0,20}(approval|review)/i,
  /<\/?\s*(system|assistant)\s*>/i,
];
const SECRETS = {
  groq_key: /\bgsk_[A-Za-z0-9]{20,}\b/g,
  google_key: /\bAIza[0-9A-Za-z_\-]{35}\b/g,
  aws_access_key: /\bAKIA[0-9A-Z]{16}\b/g,
  private_key: /-----BEGIN [A-Z ]*PRIVATE KEY-----/g,
  jwt: /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/g,
  email: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g,
};
function redact(text) {
  const found = [];
  let out = text;
  for (const [name, rx] of Object.entries(SECRETS)) {
    rx.lastIndex = 0;
    if (rx.test(out)) { found.push(name); rx.lastIndex = 0; out = out.replace(rx, `[REDACTED:${name}]`); }
    rx.lastIndex = 0;
  }
  return { text: out, found };
}
const injected = (t) => INJECTION.some((r) => r.test(t));
module.exports = { redact, injected };

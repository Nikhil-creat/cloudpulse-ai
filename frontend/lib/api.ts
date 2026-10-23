export const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function login(email: string, password: string, otp?: string): Promise<string> {
  const r = await fetch(`${API}/api/auth/token`, { method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded", ...(otp ? { "X-OTP": otp } : {}) },
    body: new URLSearchParams({ username: email, password }) });
  if (!r.ok) throw new Error("Login failed");
  return (await r.json()).access_token;
}

export async function* streamChat(token: string, message: string) {
  const r = await fetch(`${API}/api/chat`, { method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ message, session_id: "web" }) });
  const reader = r.body!.getReader(); const dec = new TextDecoder(); let buf = "";
  while (true) {
    const { value, done } = await reader.read(); if (done) break;
    buf += dec.decode(value, { stream: true });
    let i; while ((i = buf.indexOf("\n\n")) >= 0) {
      const block = buf.slice(0, i); buf = buf.slice(i + 2);
      const ev = /event: (.*)/.exec(block)?.[1]; const data = /data: (.*)/.exec(block)?.[1];
      if (ev && data) yield { event: ev, data: JSON.parse(data) };
    }
  }
}

export async function planAction(token: string, id: string, action: "approve" | "reject") {
  const r = await fetch(`${API}/api/plans/${id}/${action}`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
  if (!r.ok) throw new Error((await r.json()).detail ?? "Request failed");
}

export async function get<T>(token: string, path: string): Promise<T> {
  const r = await fetch(`${API}${path}`, { headers: { Authorization: `Bearer ${token}` } });
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
}

export async function post<T>(token: string, path: string, body?: unknown): Promise<T> {
  const r = await fetch(`${API}${path}`, { method: "POST",
    headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
  if (!r.ok) throw new Error((await r.json()).detail ?? `${path}: ${r.status}`);
  return r.json();
}

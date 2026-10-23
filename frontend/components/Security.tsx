"use client";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { post } from "@/lib/api";

export default function Security({ token }: { token: string }) {
  const [info, setInfo] = useState<{ secret: string; otpauth_uri: string } | null>(null); const [code, setCode] = useState(""); const [msg, setMsg] = useState("");
  return (
    <div className="max-w-md space-y-3 text-sm">
      <h2 className="text-base font-medium">Two-factor authentication</h2>
      <p className="text-muted">Add the secret to an authenticator app (Google Authenticator, Authy, 1Password), then confirm with a code.</p>
      {!info ? <Button onClick={async () => setInfo(await post(token, "/api/auth/totp/enroll"))}>Set up TOTP</Button> : (
        <>
          <code className="block break-all rounded border border-white/15 p-3">{info.secret}</code>
          <input value={code} onChange={e => setCode(e.target.value)} maxLength={6} inputMode="numeric" placeholder="6-digit code" aria-label="One-time code" className="h-10 w-full rounded-md border border-white/20 bg-transparent px-3" />
          <Button onClick={async () => { try { await post(token, "/api/auth/totp/verify", { code }); setMsg("MFA enabled. Next sign-in will ask for a code."); } catch (e) { setMsg((e as Error).message); } }}>Confirm</Button>
        </>)}
      {msg && <p className="text-muted">{msg}</p>}
    </div>);
}

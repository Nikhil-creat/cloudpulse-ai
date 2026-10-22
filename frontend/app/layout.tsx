import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "CloudPulse AI — Autonomous Cloud Operations", description: "Multi-cloud FinOps, security auto-remediation and AI observability." };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en"><body>
      <header className="flex items-center justify-between border-b border-white/10 px-6 py-4">
        <span className="text-[15px] font-semibold tracking-tight">CloudPulse<span className="font-normal">.ai</span></span>
        <nav className="flex gap-4 text-sm text-muted"><a href="/">Console</a><a href="/docs">API docs</a></nav>
      </header>
      {children}
      <footer className="border-t border-white/10 px-6 py-6 text-xs text-muted">
        CloudPulse AI · Built by Nikhil Chary Sriramoju · <a className="underline" href="https://github.com/Nikhil-creat">GitHub</a>
      </footer>
    </body></html>
  );
}

import React, { useState } from "react";
import { ShieldCheck, Lock, AlertCircle } from "lucide-react";
import { useAuth } from "../api/AuthContext.jsx";

export default function Login() {
  const { signIn, status } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [failed, setFailed] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setFailed(false);
    const ok = await signIn(username, password);
    if (!ok) setFailed(true);
  }

  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden bg-graphite-900">
      {/* Faint blueprint/schematic motif -- grounds the login screen in the
          plant/industrial subject matter without being literal or busy. */}
      <svg
        className="absolute inset-0 h-full w-full opacity-[0.06]"
        viewBox="0 0 800 600"
        preserveAspectRatio="xMidYMid slice"
        aria-hidden="true"
      >
        <defs>
          <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#8B93A0" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width="800" height="600" fill="url(#grid)" />
        <circle cx="220" cy="180" r="70" fill="none" stroke="#8B93A0" strokeWidth="1" />
        <circle cx="220" cy="180" r="34" fill="none" stroke="#8B93A0" strokeWidth="1" />
        <path d="M220 110 L220 60 M220 250 L220 300 M150 180 L100 180 M290 180 L340 180" stroke="#8B93A0" strokeWidth="1" />
        <path d="M500 400 h160 v90 h-160 z" fill="none" stroke="#8B93A0" strokeWidth="1" />
        <path d="M500 430 h160 M500 460 h160" stroke="#8B93A0" strokeWidth="1" />
        <path d="M60 420 L200 420 L200 500" fill="none" stroke="#8B93A0" strokeWidth="1" />
      </svg>

      <form
        onSubmit={handleSubmit}
        className="relative z-10 w-full max-w-sm rounded-md border border-graphite-600 bg-graphite-800/90 p-8 shadow-2xl backdrop-blur-sm"
      >
        <div className="mb-6 flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-sm bg-amber-500/15 text-amber-500">
            <ShieldCheck size={20} strokeWidth={1.75} />
          </div>
          <div>
            <h1 className="text-base font-medium leading-tight text-ink-100">Sovereign Workbench</h1>
            <p className="font-mono text-[11px] text-ink-500">on-premise · access controlled</p>
          </div>
        </div>

        <label className="mb-3 block">
          <span className="mb-1.5 block text-xs text-ink-300">Username</span>
          <input
            className="w-full rounded-sm border border-graphite-600 bg-graphite-900 px-3 py-2 text-sm text-ink-100 outline-none focus-visible:border-amber-500"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </label>

        <label className="mb-5 block">
          <span className="mb-1.5 block text-xs text-ink-300">Password</span>
          <div className="relative">
            <input
              type="password"
              className="w-full rounded-sm border border-graphite-600 bg-graphite-900 px-3 py-2 pr-9 text-sm text-ink-100 outline-none focus-visible:border-amber-500"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
            <Lock size={14} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-ink-700" />
          </div>
        </label>

        {failed && (
          <div className="mb-4 flex items-start gap-2 rounded-sm border border-alert-500/40 bg-alert-500/10 px-3 py-2 text-xs text-alert-400">
            <AlertCircle size={14} className="mt-0.5 shrink-0" />
            <span>Incorrect username or password.</span>
          </div>
        )}

        <button
          type="submit"
          disabled={status === "loading"}
          className="w-full rounded-sm bg-amber-500 py-2 text-sm font-medium text-graphite-950 transition-colors hover:bg-amber-400 disabled:opacity-60"
        >
          {status === "loading" ? "Verifying…" : "Sign in"}
        </button>

        <p className="mt-5 text-center font-mono text-[11px] text-ink-700">
          Credentials never leave this network. No external auth provider.
        </p>
      </form>
    </div>
  );
}

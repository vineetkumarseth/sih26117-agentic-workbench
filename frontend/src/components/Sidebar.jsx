import React from "react";
import { ShieldCheck, FileStack, LogOut } from "lucide-react";
import { useAuth } from "../api/AuthContext.jsx";

export default function Sidebar({ health, onOpenDocuments, documentCount, onOpenAdmin }) {
  const { user, signOut } = useAuth();
  const onPremise = health?.on_premise_only;

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col border-r border-graphite-600 bg-graphite-800">
      <div className="flex items-center gap-2.5 px-4 py-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-sm bg-amber-500/15 text-amber-500">
          <ShieldCheck size={17} strokeWidth={1.75} />
        </div>
        <div className="leading-tight">
          <p className="text-sm font-medium text-ink-100">Sovereign Workbench</p>
          <p className="font-mono text-[10px] text-ink-500">SIH26117</p>
        </div>
      </div>

      <div className="mx-3 mb-4 flex items-center gap-2 rounded-sm border border-graphite-600 bg-graphite-900 px-3 py-2">
        <span
          className={`h-1.5 w-1.5 shrink-0 rounded-full ${
            onPremise ? "animate-pulse-dot bg-teal-500" : "bg-alert-500"
          }`}
        />
        <div className="min-w-0">
          <p className="text-[11px] text-ink-300">{onPremise ? "On-premise mode" : "Status unknown"}</p>
          <p className="truncate font-mono text-[10px] text-ink-700">
            {health?.mock_llm ? "mock inference" : health?.llm_reachable ? "model reachable" : "model unreachable"}
          </p>
        </div>
      </div>

      <nav className="flex-1 px-2">
        <button
          onClick={onOpenDocuments}
          className="flex w-full items-center gap-2.5 rounded-sm px-2.5 py-2 text-left text-sm text-ink-300 transition-colors hover:bg-graphite-700 hover:text-ink-100"
        >
          <FileStack size={16} strokeWidth={1.75} />
          <span className="flex-1">Documents</span>
          {documentCount > 0 && (
            <span className="rounded-full bg-graphite-600 px-1.5 py-0.5 font-mono text-[10px] text-ink-300">
              {documentCount}
            </span>
          )}
        </button>
      </nav>

      <div className="flex items-center gap-2 border-t border-graphite-600 px-4 py-3">
        <button
          onClick={() => user?.role === "admin" && onOpenAdmin?.()}
          disabled={user?.role !== "admin"}
          title={user?.role === "admin" ? "Open admin dashboard" : undefined}
          className={`flex min-w-0 flex-1 items-center gap-2 rounded-sm text-left transition-colors ${
            user?.role === "admin" ? "hover:bg-graphite-700" : "cursor-default"
          }`}
        >
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-graphite-600 font-mono text-[11px] text-ink-300">
            {user?.username?.[0]?.toUpperCase() || "?"}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs text-ink-100">{user?.username}</p>
            <p className="font-mono text-[10px] text-ink-500">{user?.role}</p>
          </div>
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            signOut();
          }}
          aria-label="Sign out"
          title="Sign out"
          className="shrink-0 rounded-sm p-1.5 text-ink-500 transition-colors hover:bg-graphite-700 hover:text-ink-100"
        >
          <LogOut size={15} strokeWidth={1.75} />
        </button>
      </div>
    </aside>
  );
}
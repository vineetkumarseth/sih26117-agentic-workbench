import React from "react";
import { Workflow, FileSearch, Eye, Database, GitMerge, SkipForward, ChevronsRight } from "lucide-react";

const AGENT_META = {
  supervisor: { label: "Supervisor", icon: Workflow },
  document_agent: { label: "Document agent", icon: FileSearch },
  vision_agent: { label: "Vision agent", icon: Eye },
  structured_agent: { label: "Structured-data agent", icon: Database },
  synthesizer: { label: "Synthesizer", icon: GitMerge },
};

function StepIcon({ agent, action }) {
  const meta = AGENT_META[agent];
  const Icon = action === "skip" ? SkipForward : meta?.icon || Workflow;
  return <Icon size={13} strokeWidth={1.75} />;
}

export default function AgentTracePanel({ trace, route, collapsed, onToggle }) {
  if (collapsed) {
    return (
      <button
        onClick={onToggle}
        aria-label="Expand agent trace"
        className="flex h-screen w-9 shrink-0 flex-col items-center border-l border-graphite-600 bg-graphite-800 pt-4 text-ink-500 transition-colors hover:text-ink-100"
      >
        <ChevronsRight size={15} strokeWidth={1.75} />
      </button>
    );
  }

  return (
    <aside className="flex h-screen w-72 shrink-0 flex-col border-l border-graphite-600 bg-graphite-800">
      <div className="flex items-center justify-between border-b border-graphite-600 px-4 py-3.5">
        <div>
          <p className="text-sm font-medium text-ink-100">Agent trace</p>
          <p className="font-mono text-[10px] text-ink-500">
            {route?.length ? route.join(" → ") : "no turn yet"}
          </p>
        </div>
        <button
          onClick={onToggle}
          aria-label="Collapse agent trace"
          className="rounded-sm p-1 text-ink-500 hover:bg-graphite-700 hover:text-ink-100"
        >
          <ChevronsRight size={15} strokeWidth={1.75} className="rotate-180" />
        </button>
      </div>

      <div className="scrollbar-thin flex-1 overflow-y-auto px-3 py-3">
        {(!trace || trace.length === 0) && (
          <p className="px-1 py-8 text-center text-xs text-ink-700">
            Send a message to see which agents handle it and why.
          </p>
        )}

        <ol className="space-y-2">
          {trace?.map((step, i) => {
            const isSkip = step.action === "skip";
            return (
              <li
                key={i}
                className="animate-step-in rounded-sm border border-graphite-600 bg-graphite-900 px-3 py-2"
                style={{ animationDelay: `${i * 60}ms`, animationFillMode: "backwards" }}
              >
                <div className="flex items-center gap-1.5">
                  <span className={isSkip ? "text-ink-700" : "text-amber-500"}>
                    <StepIcon agent={step.agent} action={step.action} />
                  </span>
                  <span className={`text-xs font-medium ${isSkip ? "text-ink-500" : "text-ink-100"}`}>
                    {AGENT_META[step.agent]?.label || step.agent}
                  </span>
                </div>
                <p className="mt-1 pl-[19px] font-mono text-[10.5px] leading-snug text-ink-500">{step.detail}</p>
                <p className="mt-1 pl-[19px] font-mono text-[9.5px] text-ink-700">
                  {new Date(step.timestamp).toLocaleTimeString()}
                </p>
              </li>
            );
          })}
        </ol>
      </div>
    </aside>
  );
}

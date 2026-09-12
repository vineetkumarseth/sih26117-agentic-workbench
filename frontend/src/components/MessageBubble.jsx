import React, { useState } from "react";
import { ImageIcon, ChevronDown } from "lucide-react";
import GuardrailAlert from "./GuardrailAlert.jsx";

const AGENT_LABEL = {
  document_agent: "Document",
  vision_agent: "Vision",
  structured_agent: "Records",
};

const SOURCE_META = {
  document: { badge: "bg-amber-500/20 text-amber-400" },
  structured: { badge: "bg-teal-500/20 text-teal-400" },
  vision: { badge: "bg-graphite-600 text-ink-200" },
};

// Splits "...pressure hit 181 psi [s2]..." (or, if the model drops the
// brackets, "...pressure hit 181 psi s2...") into plain text and small
// numbered citation badges -- footnote-style ("¹", "²"), not the raw
// internal id, since "d1" printed as text reads like debug output, not a
// citation. Numbers reflect each citation's position in this message's
// full citations list (in the order the agents produced them), colored
// by source type. A tag only renders as a badge if its id is actually in
// `citations` -- checked against real backend data, not just "looks like
// a tag" -- so stray text that happens to resemble one is never mis-styled.
function renderWithCitationTags(text, citations) {
  const validIds = new Set((citations || []).map((c) => c.id));
  if (validIds.size === 0) return text;

  const order = new Map((citations || []).map((c, i) => [c.id, i + 1]));
  const badgeClass = new Map((citations || []).map((c) => [c.id, SOURCE_META[c.source_type]?.badge || SOURCE_META.document.badge]));

  const pattern = /\[?\b([dsv]\d+)\]?\b/g;
  const parts = [];
  let lastIndex = 0;
  let match;
  let key = 0;

  while ((match = pattern.exec(text)) !== null) {
    const id = match[1];
    if (!validIds.has(id)) continue;
    parts.push(<React.Fragment key={key++}>{text.slice(lastIndex, match.index)}</React.Fragment>);
    parts.push(
      <span
        key={key++}
        className={`mx-0.5 inline-flex h-[15px] min-w-[15px] items-center justify-center rounded-full px-1 align-super font-mono text-[9px] font-medium leading-none ${badgeClass.get(id)}`}
      >
        {order.get(id)}
      </span>
    );
    lastIndex = match.index + match[0].length;
  }
  parts.push(<React.Fragment key={key++}>{text.slice(lastIndex)}</React.Fragment>);
  return parts;
}

function SourcesList({ citations }) {
  // Open by default (not click-to-reveal): for a demo in front of judges,
  // the source trail should be visible at a glance, proving answers are
  // grounded rather than invented, without anyone needing to know to click.
  const [open, setOpen] = useState(true);
  if (!citations?.length) return null;

  return (
    <div className="mt-1 w-full">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1 px-1 font-mono text-[10px] text-ink-500 transition-colors hover:text-ink-300"
      >
        <ChevronDown size={11} className={`transition-transform ${open ? "" : "-rotate-90"}`} />
        Grounded in {citations.length} source{citations.length > 1 ? "s" : ""}
      </button>
      {open && (
        <ul className="mt-1 space-y-1 border-l border-graphite-600 pl-2.5">
          {citations.map((c, i) => {
            const meta = SOURCE_META[c.source_type] || SOURCE_META.document;
            return (
              <li key={c.id} className="flex items-start gap-1.5 py-0.5">
                <span
                  className={`mt-0.5 flex h-[15px] w-[15px] shrink-0 items-center justify-center rounded-full font-mono text-[9px] font-medium leading-none ${meta.badge}`}
                >
                  {i + 1}
                </span>
                <div className="min-w-0">
                  <p className="font-mono text-[9.5px] text-ink-500">
                    <span className="text-amber-500">[{c.id}]</span> {c.label}
                  </p>
                  <p className="truncate text-[10.5px] text-ink-700">{c.snippet}</p>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export default function MessageBubble({ role, content, route, citations, blocked, blockReason, imagePreview }) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[72%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-1.5`}>
        {imagePreview && (
          <img
            src={imagePreview}
            alt="Attached"
            className="max-h-40 rounded-sm border border-graphite-600 object-cover"
          />
        )}

        {blocked ? (
          <GuardrailAlert reason={blockReason} />
        ) : (
          <div
            className={`rounded-md px-3.5 py-2.5 text-sm leading-relaxed ${
              isUser
                ? "bg-amber-500/15 text-ink-100"
                : "border border-graphite-600 bg-graphite-800 text-ink-100"
            }`}
          >
            {isUser ? content : renderWithCitationTags(content, citations)}
          </div>
        )}

        {!isUser && !blocked && route?.length > 0 && (
          <div className="flex flex-wrap gap-1 px-1">
            {route.map((agent) => (
              <span
                key={agent}
                className="rounded-full border border-graphite-600 px-2 py-0.5 font-mono text-[9.5px] text-ink-500"
              >
                {AGENT_LABEL[agent] || agent}
              </span>
            ))}
          </div>
        )}

        {!isUser && !blocked && <SourcesList citations={citations} />}
      </div>
    </div>
  );
}

export function ImageAttachedTag() {
  return (
    <span className="inline-flex items-center gap-1 text-ink-500">
      <ImageIcon size={11} /> image attached
    </span>
  );
}
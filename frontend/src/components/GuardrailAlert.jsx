import React from "react";
import { ShieldAlert } from "lucide-react";

const REASON_COPY = {
  prompt_injection_or_secret_request: "Blocked: looked like an attempt to override instructions or extract secrets.",
  off_topic: "Blocked: outside this workbench's scope (ingested plant documents only).",
  possible_credential_leak: "Response withheld: it contained something shaped like a live credential.",
  nemo_guardrails_refusal: "Blocked by the NeMo Guardrails policy engine.",
};

export default function GuardrailAlert({ reason }) {
  return (
    <div className="flex items-start gap-2 rounded-sm border border-alert-500/40 bg-alert-500/10 px-3 py-2 text-xs text-alert-400">
      <ShieldAlert size={14} className="mt-0.5 shrink-0" />
      <span>{REASON_COPY[reason] || "Blocked by the workbench's guardrails."}</span>
    </div>
  );
}

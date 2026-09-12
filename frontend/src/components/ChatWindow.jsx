import React, { useCallback, useRef, useState } from "react";
import { Send, Paperclip, Camera as CameraIcon, X, Loader2 } from "lucide-react";
import MessageBubble from "./MessageBubble.jsx";
import CameraCapture from "./CameraCapture.jsx";
import { sendChatMessage } from "../api/client.js";

function genSessionId() {
  return typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : `s-${Date.now()}`;
}

export default function ChatWindow({ onTraceUpdate }) {
  const [sessionId] = useState(genSessionId);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [pendingImage, setPendingImage] = useState(null); // { base64, preview }
  const [cameraOpen, setCameraOpen] = useState(false);
  const [sending, setSending] = useState(false);
  const fileInputRef = useRef(null);
  const scrollRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
    });
  }, []);

  function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result;
      const base64 = String(dataUrl).split(",")[1];
      setPendingImage({ base64, preview: dataUrl });
    };
    reader.readAsDataURL(file);
    e.target.value = "";
  }

  async function handleSend(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    const userMsg = { role: "user", content: text, imagePreview: pendingImage?.preview };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    const imageBase64 = pendingImage?.base64;
    setPendingImage(null);
    setSending(true);
    scrollToBottom();

    try {
      const result = await sendChatMessage({ message: text, sessionId, imageBase64 });
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.answer,
          route: result.route,
          citations: result.citations,
          blocked: result.blocked,
          blockReason: result.block_reason,
        },
      ]);
      onTraceUpdate(result.trace || [], result.route || []);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "The workbench couldn't reach the backend for that request. Check that the API is running.",
          route: [],
        },
      ]);
    } finally {
      setSending(false);
      scrollToBottom();
    }
  }

  return (
    <div className="flex h-screen flex-1 flex-col bg-graphite-900">
      <div ref={scrollRef} className="scrollbar-thin flex-1 overflow-y-auto px-6 py-6">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <p className="max-w-sm text-sm text-ink-500">
              Ask about an ingested plant document, attach a diagram for the vision agent, or ask about equipment
              readings and logs.
            </p>
          </div>
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-4">
            {messages.map((m, i) => (
              <MessageBubble key={i} {...m} />
            ))}
            {sending && (
              <div className="flex items-center gap-2 pl-1 text-xs text-ink-500">
                <Loader2 size={13} className="animate-spin" />
                Routing across agents…
              </div>
            )}
          </div>
        )}
      </div>

      <form onSubmit={handleSend} className="border-t border-graphite-600 bg-graphite-800 px-6 py-4">
        <div className="mx-auto max-w-3xl">
          {pendingImage && (
            <div className="mb-2 flex items-center gap-2 rounded-sm border border-graphite-600 bg-graphite-900 px-2.5 py-1.5">
              <img src={pendingImage.preview} alt="Pending attachment" className="h-8 w-8 rounded-sm object-cover" />
              <span className="flex-1 text-xs text-ink-500">Image ready to send</span>
              <button
                type="button"
                onClick={() => setPendingImage(null)}
                className="rounded-sm p-1 text-ink-500 hover:bg-graphite-700 hover:text-ink-100"
                aria-label="Remove attachment"
              >
                <X size={13} />
              </button>
            </div>
          )}
          <div className="flex items-end gap-2 rounded-md border border-graphite-600 bg-graphite-900 px-3 py-2 focus-within:border-amber-500">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="shrink-0 rounded-sm p-1.5 text-ink-500 hover:bg-graphite-700 hover:text-ink-100"
              aria-label="Attach image"
              title="Attach an image for the vision agent"
            >
              <Paperclip size={16} strokeWidth={1.75} />
            </button>
            <button
              type="button"
              onClick={() => setCameraOpen(true)}
              className="shrink-0 rounded-sm p-1.5 text-ink-500 hover:bg-graphite-700 hover:text-ink-100"
              aria-label="Take a photo"
              title="Take a live photo for the vision agent"
            >
              <CameraIcon size={16} strokeWidth={1.75} />
            </button>
            <input ref={fileInputRef} type="file" accept="image/png,image/jpeg" hidden onChange={handleFileChange} />
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  handleSend(e);
                }
              }}
              rows={1}
              placeholder="Ask about plant documents, readings, or an attached diagram…"
              className="max-h-32 flex-1 resize-none bg-transparent py-1 text-sm text-ink-100 placeholder:text-ink-700 focus:outline-none"
            />
            <button
              type="submit"
              disabled={!input.trim() || sending}
              className="shrink-0 rounded-sm bg-amber-500 p-1.5 text-graphite-950 transition-colors hover:bg-amber-400 disabled:opacity-40"
              aria-label="Send"
            >
              <Send size={15} strokeWidth={2} />
            </button>
          </div>
        </div>
      </form>
      <CameraCapture open={cameraOpen} onClose={() => setCameraOpen(false)} onCapture={setPendingImage} />
    </div>
  );
}
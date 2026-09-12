import React, { useCallback, useEffect, useState } from "react";
import { X, UploadCloud, FileText, Loader2, CheckCircle2 } from "lucide-react";
import { listDocuments, uploadDocument } from "../api/client.js";

export default function DocumentUpload({ open, onClose, onUploaded }) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const docs = await listDocuments();
      setDocuments(docs);
    } catch {
      // Silent -- the drawer still works for uploading even if listing fails.
    }
  }, []);

  useEffect(() => {
    if (open) refresh();
  }, [open, refresh]);

  async function handleFiles(fileList) {
    const file = fileList?.[0];
    if (!file) return;
    setError(null);
    setLoading(true);
    try {
      await uploadDocument(file);
      await refresh();
      onUploaded?.();
    } catch (err) {
      setError(err?.response?.data?.detail || "Upload failed — check the file type and size.");
    } finally {
      setLoading(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-20 flex justify-end bg-black/40" onClick={onClose}>
      <div
        className="flex h-screen w-96 flex-col border-l border-graphite-600 bg-graphite-800 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-graphite-600 px-5 py-4">
          <p className="text-sm font-medium text-ink-100">Ingested documents</p>
          <button onClick={onClose} className="rounded-sm p-1 text-ink-500 hover:bg-graphite-700 hover:text-ink-100">
            <X size={16} />
          </button>
        </div>

        <div className="px-5 py-4">
          <label
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              handleFiles(e.dataTransfer.files);
            }}
            className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border border-dashed px-4 py-8 text-center transition-colors ${
              dragOver ? "border-amber-500 bg-amber-500/5" : "border-graphite-600 hover:border-graphite-500"
            }`}
          >
            <input
              type="file"
              hidden
              accept=".pdf,.txt,.md,.png,.jpg,.jpeg"
              onChange={(e) => handleFiles(e.target.files)}
            />
            {loading ? (
              <Loader2 size={20} className="animate-spin text-amber-500" />
            ) : (
              <UploadCloud size={20} className="text-ink-500" />
            )}
            <p className="text-xs text-ink-300">Drop a file or click to upload</p>
            <p className="font-mono text-[10px] text-ink-700">PDF · TXT · MD · PNG · JPG — max 25 MB</p>
          </label>
          {error && <p className="mt-2 text-xs text-alert-400">{error}</p>}
        </div>

        <div className="scrollbar-thin flex-1 overflow-y-auto px-5 pb-5">
          {documents.length === 0 ? (
            <p className="py-6 text-center text-xs text-ink-700">No documents ingested yet.</p>
          ) : (
            <ul className="space-y-2">
              {documents.map((doc) => (
                <li
                  key={doc.id}
                  className="flex items-start gap-2.5 rounded-sm border border-graphite-600 bg-graphite-900 px-3 py-2.5"
                >
                  <FileText size={15} className="mt-0.5 shrink-0 text-ink-500" strokeWidth={1.75} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs text-ink-100">{doc.filename}</p>
                    <p className="font-mono text-[10px] text-ink-500">{doc.chunk_count} chunk(s) indexed</p>
                  </div>
                  <CheckCircle2 size={13} className="mt-0.5 shrink-0 text-teal-500" />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

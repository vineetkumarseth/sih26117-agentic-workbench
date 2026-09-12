import React, { useCallback, useEffect, useState } from "react";
import {
  X,
  LayoutDashboard,
  Users as UsersIcon,
  FileStack,
  ScrollText,
  Loader2,
  Trash2,
  ShieldAlert,
  ShieldCheck,
  Plus,
  UserPlus,
} from "lucide-react";
import {
  fetchAdminStats,
  fetchAdminUsers,
  fetchAdminDocuments,
  fetchAuditLog,
  updateAdminUser,
  createUser,
  deleteAdminDocument,
} from "../api/client.js";

const TABS = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "audit", label: "Audit log", icon: ScrollText },
  { id: "users", label: "Users", icon: UsersIcon },
  { id: "documents", label: "Documents", icon: FileStack },
];

export default function AdminPanel({ open, onClose, currentUser }) {
  const [tab, setTab] = useState("overview");

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-30 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="flex h-[85vh] w-[min(920px,92vw)] flex-col overflow-hidden rounded-md border border-graphite-600 bg-graphite-800 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-graphite-600 px-5 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-7 w-7 items-center justify-center rounded-sm bg-amber-500/15 text-amber-500">
              <ShieldCheck size={15} strokeWidth={1.75} />
            </div>
            <p className="text-sm font-medium text-ink-100">Admin dashboard</p>
          </div>
          <button onClick={onClose} className="rounded-sm p-1 text-ink-500 hover:bg-graphite-700 hover:text-ink-100">
            <X size={16} />
          </button>
        </div>

        <div className="flex border-b border-graphite-600 px-2">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex items-center gap-1.5 border-b-2 px-3.5 py-2.5 text-xs transition-colors ${
                tab === id
                  ? "border-amber-500 text-ink-100"
                  : "border-transparent text-ink-500 hover:text-ink-300"
              }`}
            >
              <Icon size={13.5} strokeWidth={1.75} />
              {label}
            </button>
          ))}
        </div>

        <div className="scrollbar-thin flex-1 overflow-y-auto px-5 py-4">
          {tab === "overview" && <OverviewTab />}
          {tab === "audit" && <AuditTab />}
          {tab === "users" && <UsersTab currentUser={currentUser} />}
          {tab === "documents" && <DocumentsTab />}
        </div>
      </div>
    </div>
  );
}

// --- shared bits -----------------------------------------------------------

function Card({ label, value, accent }) {
  return (
    <div className="rounded-sm border border-graphite-600 bg-graphite-900 px-4 py-3">
      <p className="font-mono text-[10px] uppercase tracking-wide text-ink-700">{label}</p>
      <p className={`mt-1 text-xl font-medium ${accent || "text-ink-100"}`}>{value}</p>
    </div>
  );
}

function LoadingRow() {
  return (
    <div className="flex items-center justify-center py-10 text-ink-500">
      <Loader2 size={18} className="animate-spin" />
    </div>
  );
}

function ErrorRow({ message }) {
  return <p className="py-6 text-center text-xs text-alert-400">{message}</p>;
}

// --- Overview ---------------------------------------------------------------

function OverviewTab() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchAdminStats()
      .then(setStats)
      .catch((err) => setError(err?.response?.data?.detail || "Failed to load stats."));
  }, []);

  if (error) return <ErrorRow message={error} />;
  if (!stats) return <LoadingRow />;

  const agentEntries = Object.entries(stats.agent_usage || {}).sort((a, b) => b[1] - a[1]);
  const maxAgentCount = Math.max(1, ...agentEntries.map(([, c]) => c));

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Card label="Queries" value={stats.total_queries} />
        <Card label="Blocked" value={stats.total_blocked} accent={stats.total_blocked > 0 ? "text-alert-400" : undefined} />
        <Card label="Documents" value={stats.total_documents} />
        <Card label="Indexed chunks" value={stats.total_chunks} />
        <Card label="Uploads" value={stats.total_uploads} />
        <Card label="Users" value={stats.total_users} />
        <Card label="Active users" value={stats.active_users} />
        <Card
          label="Inference mode"
          value={stats.mock_llm ? "Mock" : "Live"}
          accent={stats.mock_llm ? "text-alert-400" : "text-teal-500"}
        />
      </div>

      <div>
        <p className="mb-2 font-mono text-[10px] uppercase tracking-wide text-ink-700">Agent usage (by query)</p>
        {agentEntries.length === 0 ? (
          <p className="text-xs text-ink-700">No queries logged yet.</p>
        ) : (
          <div className="space-y-1.5">
            {agentEntries.map(([agent, count]) => (
              <div key={agent} className="flex items-center gap-2.5">
                <span className="w-32 shrink-0 truncate font-mono text-[11px] text-ink-300">{agent}</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-graphite-900">
                  <div
                    className="h-full rounded-full bg-amber-500/70"
                    style={{ width: `${(count / maxAgentCount) * 100}%` }}
                  />
                </div>
                <span className="w-6 shrink-0 text-right font-mono text-[11px] text-ink-500">{count}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div>
        <p className="mb-2 font-mono text-[10px] uppercase tracking-wide text-ink-700">On-premise configuration</p>
        <div className="grid grid-cols-1 gap-1.5 rounded-sm border border-graphite-600 bg-graphite-900 px-3.5 py-3 sm:grid-cols-2">
          <ConfigLine label="Text model" value={stats.ollama_text_model} />
          <ConfigLine label="Vision model" value={stats.ollama_vision_model} />
          <ConfigLine label="Embedding model" value={stats.embedding_model} />
          <ConfigLine label="Vector collection" value={stats.qdrant_collection} />
        </div>
      </div>
    </div>
  );
}

function ConfigLine({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-3 text-[11px]">
      <span className="text-ink-500">{label}</span>
      <span className="truncate font-mono text-ink-300">{value}</span>
    </div>
  );
}

// --- Audit log ---------------------------------------------------------------

const EVENT_STYLES = {
  login: "text-teal-500",
  query: "text-ink-300",
  upload: "text-amber-500",
  guardrail_block: "text-alert-400",
  error: "text-alert-400",
};

function AuditTab() {
  const [entries, setEntries] = useState(null);
  const [error, setError] = useState(null);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    fetchAuditLog()
      .then(setEntries)
      .catch((err) => setError(err?.response?.data?.detail || "Failed to load audit log."));
  }, []);

  if (error) return <ErrorRow message={error} />;
  if (!entries) return <LoadingRow />;

  const eventTypes = ["all", ...new Set(entries.map((e) => e.event_type))];
  const visible = filter === "all" ? entries : entries.filter((e) => e.event_type === filter);

  return (
    <div>
      <div className="mb-3 flex flex-wrap gap-1.5">
        {eventTypes.map((type) => (
          <button
            key={type}
            onClick={() => setFilter(type)}
            className={`rounded-full px-2.5 py-1 font-mono text-[10px] transition-colors ${
              filter === type
                ? "bg-amber-500/15 text-amber-500"
                : "bg-graphite-900 text-ink-500 hover:text-ink-300"
            }`}
          >
            {type} {type !== "all" && `(${entries.filter((e) => e.event_type === type).length})`}
          </button>
        ))}
      </div>

      <div className="overflow-hidden rounded-sm border border-graphite-600">
        <table className="w-full text-left text-[11px]">
          <thead className="bg-graphite-900 font-mono text-[10px] uppercase tracking-wide text-ink-700">
            <tr>
              <th className="px-3 py-2">Time</th>
              <th className="px-3 py-2">User</th>
              <th className="px-3 py-2">Event</th>
              <th className="px-3 py-2">Route</th>
              <th className="px-3 py-2">Detail</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((e) => (
              <tr key={e.id} className="border-t border-graphite-700">
                <td className="whitespace-nowrap px-3 py-2 font-mono text-ink-500">
                  {new Date(e.timestamp).toLocaleString()}
                </td>
                <td className="px-3 py-2 text-ink-300">{e.username || "—"}</td>
                <td className={`px-3 py-2 font-mono ${EVENT_STYLES[e.event_type] || "text-ink-300"}`}>
                  <span className="inline-flex items-center gap-1">
                    {e.event_type === "guardrail_block" && <ShieldAlert size={11} />}
                    {e.event_type}
                  </span>
                  {!e.allowed && <span className="ml-1.5 text-alert-400">(blocked)</span>}
                </td>
                <td className="px-3 py-2 font-mono text-ink-500">{e.route || "—"}</td>
                <td className="px-3 py-2 text-ink-500">{e.detail || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {visible.length === 0 && <p className="py-6 text-center text-xs text-ink-700">No entries.</p>}
      </div>
    </div>
  );
}

// --- Users ---------------------------------------------------------------

function UsersTab({ currentUser }) {
  const [users, setUsers] = useState(null);
  const [error, setError] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ username: "", password: "", role: "operator" });
  const [createError, setCreateError] = useState(null);
  const [creating, setCreating] = useState(false);

  const refresh = useCallback(() => {
    fetchAdminUsers()
      .then(setUsers)
      .catch((err) => setError(err?.response?.data?.detail || "Failed to load users."));
  }, []);

  useEffect(refresh, [refresh]);

  async function toggleActive(user) {
    try {
      await updateAdminUser(user.id, { is_active: !user.is_active });
      refresh();
    } catch (err) {
      setError(err?.response?.data?.detail || "Update failed.");
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    setCreateError(null);
    setCreating(true);
    try {
      await createUser(form);
      setForm({ username: "", password: "", role: "operator" });
      setShowCreate(false);
      refresh();
    } catch (err) {
      setCreateError(err?.response?.data?.detail || "Could not create user.");
    } finally {
      setCreating(false);
    }
  }

  if (error) return <ErrorRow message={error} />;
  if (!users) return <LoadingRow />;

  return (
    <div>
      <div className="mb-3 flex items-center justify-between">
        <p className="font-mono text-[10px] uppercase tracking-wide text-ink-700">{users.length} user(s)</p>
        <button
          onClick={() => setShowCreate((s) => !s)}
          className="flex items-center gap-1.5 rounded-sm bg-amber-500/15 px-2.5 py-1.5 text-[11px] text-amber-500 hover:bg-amber-500/25"
        >
          <UserPlus size={13} />
          New user
        </button>
      </div>

      {showCreate && (
        <form
          onSubmit={handleCreate}
          className="mb-3 flex flex-wrap items-end gap-2 rounded-sm border border-graphite-600 bg-graphite-900 p-3"
        >
          <div>
            <label className="mb-1 block font-mono text-[10px] text-ink-700">Username</label>
            <input
              required
              minLength={3}
              value={form.username}
              onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
              className="rounded-sm border border-graphite-600 bg-graphite-800 px-2 py-1 text-xs text-ink-100 outline-none focus:border-amber-500"
            />
          </div>
          <div>
            <label className="mb-1 block font-mono text-[10px] text-ink-700">Password</label>
            <input
              required
              minLength={8}
              type="password"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              className="rounded-sm border border-graphite-600 bg-graphite-800 px-2 py-1 text-xs text-ink-100 outline-none focus:border-amber-500"
            />
          </div>
          <div>
            <label className="mb-1 block font-mono text-[10px] text-ink-700">Role</label>
            <select
              value={form.role}
              onChange={(e) => setForm((f) => ({ ...f, role: e.target.value }))}
              className="rounded-sm border border-graphite-600 bg-graphite-800 px-2 py-1 text-xs text-ink-100 outline-none focus:border-amber-500"
            >
              <option value="operator">operator</option>
              <option value="admin">admin</option>
            </select>
          </div>
          <button
            type="submit"
            disabled={creating}
            className="flex items-center gap-1 rounded-sm bg-amber-500 px-3 py-1.5 text-xs font-medium text-graphite-900 disabled:opacity-50"
          >
            {creating ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
            Create
          </button>
          {createError && <p className="w-full text-[11px] text-alert-400">{createError}</p>}
        </form>
      )}

      <ul className="space-y-1.5">
        {users.map((u) => (
          <li
            key={u.id}
            className="flex items-center justify-between rounded-sm border border-graphite-600 bg-graphite-900 px-3.5 py-2.5"
          >
            <div className="flex items-center gap-2.5">
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-graphite-700 font-mono text-[10px] text-ink-300">
                {u.username[0]?.toUpperCase()}
              </div>
              <div>
                <p className="text-xs text-ink-100">
                  {u.username} {u.id === currentUser?.id && <span className="text-ink-700">(you)</span>}
                </p>
                <p className="font-mono text-[10px] text-ink-500">
                  {u.role} · joined {new Date(u.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
            <button
              onClick={() => toggleActive(u)}
              disabled={u.id === currentUser?.id && u.is_active}
              title={u.id === currentUser?.id ? "Can't deactivate your own account" : undefined}
              className={`rounded-full px-2.5 py-1 font-mono text-[10px] transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
                u.is_active
                  ? "bg-teal-500/15 text-teal-500 hover:bg-alert-500/15 hover:text-alert-400"
                  : "bg-alert-500/15 text-alert-400 hover:bg-teal-500/15 hover:text-teal-500"
              }`}
            >
              {u.is_active ? "active" : "disabled"}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

// --- Documents ---------------------------------------------------------------

function DocumentsTab() {
  const [docs, setDocs] = useState(null);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const refresh = useCallback(() => {
    fetchAdminDocuments()
      .then(setDocs)
      .catch((err) => setError(err?.response?.data?.detail || "Failed to load documents."));
  }, []);

  useEffect(refresh, [refresh]);

  async function handleDelete(doc) {
    if (!window.confirm(`Delete "${doc.filename}"? This removes it from the vector store too.`)) return;
    setDeletingId(doc.id);
    try {
      await deleteAdminDocument(doc.id);
      refresh();
    } catch (err) {
      setError(err?.response?.data?.detail || "Delete failed.");
    } finally {
      setDeletingId(null);
    }
  }

  if (error) return <ErrorRow message={error} />;
  if (!docs) return <LoadingRow />;

  return (
    <div>
      <p className="mb-3 font-mono text-[10px] uppercase tracking-wide text-ink-700">
        {docs.length} document(s) across all users
      </p>
      <ul className="space-y-1.5">
        {docs.map((d) => (
          <li
            key={d.id}
            className="flex items-center justify-between gap-3 rounded-sm border border-graphite-600 bg-graphite-900 px-3.5 py-2.5"
          >
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs text-ink-100">{d.filename}</p>
              <p className="font-mono text-[10px] text-ink-500">
                {d.owner_username || "unknown"} · {d.chunk_count} chunk(s) · {new Date(d.uploaded_at).toLocaleDateString()}
              </p>
            </div>
            <button
              onClick={() => handleDelete(d)}
              disabled={deletingId === d.id}
              className="rounded-sm p-1.5 text-ink-500 hover:bg-alert-500/15 hover:text-alert-400 disabled:opacity-40"
              title="Delete document"
            >
              {deletingId === d.id ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
            </button>
          </li>
        ))}
      </ul>
      {docs.length === 0 && <p className="py-6 text-center text-xs text-ink-700">No documents uploaded yet.</p>}
    </div>
  );
}

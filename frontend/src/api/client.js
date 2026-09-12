import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

// The JWT lives in memory (React state) for this session, not
// localStorage -- see AuthContext. This module just exposes a setter so
// the interceptor always attaches whatever token is currently active.
let currentToken = null;
export function setAuthToken(token) {
  currentToken = token;
}

export const api = axios.create({ baseURL: BASE_URL });

api.interceptors.request.use((config) => {
  if (currentToken) {
    config.headers.Authorization = `Bearer ${currentToken}`;
  }
  return config;
});

export async function login(username, password) {
  const form = new URLSearchParams();
  form.append("username", username);
  form.append("password", password);
  const { data } = await api.post("/api/auth/login", form, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data;
}

export async function fetchMe() {
  const { data } = await api.get("/api/auth/me");
  return data;
}

export async function sendChatMessage({ message, sessionId, imageBase64 }) {
  const { data } = await api.post("/api/chat", {
    message,
    session_id: sessionId,
    image_base64: imageBase64 || null,
  });
  return data;
}

export async function uploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  const { data } = await api.post("/api/documents/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function listDocuments() {
  const { data } = await api.get("/api/documents");
  return data;
}

export async function fetchHealth() {
  const { data } = await api.get("/api/health");
  return data;
}

export async function fetchAuditLog() {
  const { data } = await api.get("/api/audit");
  return data;
}

// --- Admin ---------------------------------------------------------------
export async function fetchAdminStats() {
  const { data } = await api.get("/api/admin/stats");
  return data;
}

export async function fetchAdminUsers() {
  const { data } = await api.get("/api/admin/users");
  return data;
}

export async function updateAdminUser(userId, patch) {
  const { data } = await api.patch(`/api/admin/users/${userId}`, patch);
  return data;
}

export async function createUser({ username, password, role }) {
  const { data } = await api.post("/api/auth/users", { username, password, role });
  return data;
}

export async function fetchAdminDocuments() {
  const { data } = await api.get("/api/admin/documents");
  return data;
}

export async function deleteAdminDocument(documentId) {
  await api.delete(`/api/admin/documents/${documentId}`);
}

import React, { useEffect, useState } from "react";
import Sidebar from "../components/Sidebar.jsx";
import ChatWindow from "../components/ChatWindow.jsx";
import AgentTracePanel from "../components/AgentTracePanel.jsx";
import DocumentUpload from "../components/DocumentUpload.jsx";
import AdminPanel from "../components/AdminPanel.jsx";
import { fetchHealth, listDocuments } from "../api/client.js";
import { useAuth } from "../api/AuthContext.jsx";

export default function Dashboard() {
  const { user } = useAuth();
  const [health, setHealth] = useState(null);
  const [trace, setTrace] = useState([]);
  const [route, setRoute] = useState([]);
  const [traceCollapsed, setTraceCollapsed] = useState(false);
  const [docsOpen, setDocsOpen] = useState(false);
  const [adminOpen, setAdminOpen] = useState(false);
  const [documentCount, setDocumentCount] = useState(0);

  useEffect(() => {
    fetchHealth().then(setHealth).catch(() => setHealth(null));
    refreshDocCount();
  }, []);

  function refreshDocCount() {
    listDocuments()
      .then((docs) => setDocumentCount(docs.length))
      .catch(() => {});
  }

  return (
    <div className="flex h-screen w-full overflow-hidden">
      <Sidebar
        health={health}
        onOpenDocuments={() => setDocsOpen(true)}
        onOpenAdmin={() => setAdminOpen(true)}
        documentCount={documentCount}
      />
      <ChatWindow
        onTraceUpdate={(newTrace, newRoute) => {
          setTrace(newTrace);
          setRoute(newRoute);
        }}
      />
      <AgentTracePanel
        trace={trace}
        route={route}
        collapsed={traceCollapsed}
        onToggle={() => setTraceCollapsed((c) => !c)}
      />
      <DocumentUpload open={docsOpen} onClose={() => setDocsOpen(false)} onUploaded={refreshDocCount} />
      <AdminPanel open={adminOpen} onClose={() => setAdminOpen(false)} currentUser={user} />
    </div>
  );
}

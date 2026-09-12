import React from "react";
import { AuthProvider, useAuth } from "./api/AuthContext.jsx";
import Login from "./components/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";

function Gate() {
  const { user } = useAuth();
  return user ? <Dashboard /> : <Login />;
}

export default function App() {
  return (
    <AuthProvider>
      <Gate />
    </AuthProvider>
  );
}

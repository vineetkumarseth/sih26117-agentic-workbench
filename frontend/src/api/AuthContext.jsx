import React, { createContext, useContext, useState, useCallback } from "react";
import { login as apiLogin, fetchMe, setAuthToken } from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | error

  const signIn = useCallback(async (username, password) => {
    setStatus("loading");
    try {
      const { access_token } = await apiLogin(username, password);
      setAuthToken(access_token);
      const me = await fetchMe();
      setUser(me);
      setStatus("idle");
      return true;
    } catch (err) {
      setAuthToken(null);
      setStatus("error");
      return false;
    }
  }, []);

  const signOut = useCallback(() => {
    setAuthToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, status, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

"use client";

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from "react";
import { api, User } from "@/lib/api";
import { useRouter, usePathname } from "next/navigation";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, role?: string) => Promise<void>;
  logout: () => void;
  isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  login: async () => {},
  register: async () => {},
  logout: () => {},
  isAdmin: false,
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  // Guard flag: only load user once per session
  const hasLoadedRef = useRef(false);

  const loadUser = useCallback(async () => {
    if (hasLoadedRef.current) return;
    hasLoadedRef.current = true;

    try {
      const u = await api.auth.me();
      setUser(u);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  useEffect(() => {
    if (!loading || !pathname) return;
    const isPublicRoute =
      pathname.startsWith("/login") || pathname.startsWith("/register");
    if (!isPublicRoute) {
      router.push("/login");
    }
  }, [loading, pathname, router]);

  const login = async (username: string, password: string) => {
    const data = await api.auth.login(username, password);
    setUser(data.user);
    router.push(data.user.role === "admin" ? "/admin/dashboard" : "/");
  };

  const register = async (username: string, password: string, role = "user") => {
    await api.auth.register(username, password, role);
    router.push("/login");
  };

  const logout = () => {
    api.auth.logout();
    setUser(null);
    setLoading(false);
    hasLoadedRef.current = false;
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, isAdmin: user?.role === "admin" }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
